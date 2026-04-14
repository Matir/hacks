from typing import Dict, Any, List, Optional, Callable
from trashdig.agents.archaeologist import create_archaeologist_agent
from trashdig.agents.hunter import create_hunter_agent
from trashdig.agents.validator import create_validator_agent
from trashdig.agents.types import Task, TaskType, TaskStatus, Hypothesis
from trashdig.config import Config
from trashdig.database import ProjectDatabase
from trashdig.findings import Finding

class Coordinator:
    """Coordinatates the hypothesis-driven workflow between agents."""

    def __init__(self, config: Config, project_path: str = "."):
        """Initializes the Coordinator with the given configuration.

        Args:
            config: The project configuration object.
            project_path: Root directory of the project being scanned.
                Used as the key for all database records.
        """
        self.config = config
        self.project_path = project_path
        self.archaeologist = create_archaeologist_agent(config.agents.get("archaeologist"))
        self.hunter = create_hunter_agent(config.agents.get("hunter"))
        self.validator = create_validator_agent(config.agents.get("validator"))

        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.scan_results: Dict[str, Any] = {}
        self.tech_stack: str = ""
        self.findings: List[Finding] = []

        # Persistent knowledge store
        db_path = getattr(config, "db_path", ".trashdig/trashdig.db")
        self.db = ProjectDatabase(db_path)

        # Callback for TUI updates
        self.on_task_event: Optional[Callable[[str], None]] = None

    def log(self, message: str) -> None:
        """Logs a message through the event callback.

        Args:
            message: The message to log.
        """
        if self.on_task_event:
            self.on_task_event(message)

    def spawn_task(self, task: Task) -> None:
        """Adds a new task to the queue.

        Args:
            task: The task to add to the queue.
        """
        self.log(f"Spawned Task: [cyan]{task.type.name}[/cyan] -> [dim]{task.target}[/dim]")
        self.task_queue.append(task)

    async def run_loop(self) -> None:
        """Main Observe-Hypothesize-Verify loop.
        
        This loop processes the task queue until it is empty, delegating tasks
        to the appropriate agents based on the task type.
        """
        while self.task_queue:
            task = self.task_queue.pop(0)
            task.status = TaskStatus.RUNNING
            self.log(f"Executing: [bold blue]{task.type.name}[/bold blue] ([dim]{task.target}[/dim])")
            
            try:
                if task.type == TaskType.SCAN:
                    await self._handle_scan(task)
                elif task.type == TaskType.HUNT:
                    await self._handle_hunt(task)
                elif task.type == TaskType.VERIFY:
                    await self._handle_verify(task)
                
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.append(task)
            except Exception as e:
                task.status = TaskStatus.FAILED
                self.log(f"[red]Task Failed: {str(e)}[/red]")

    async def _handle_scan(self, task: Task) -> None:
        """Runs the Archaeologist scan.

        Args:
            task: The scan task to handle.
        """
        results = await self.archaeologist.scan_project(task.target)

        # Handle new format {"mapping": ..., "hypotheses": ...}
        mapping: Dict[str, Any] = results.get("mapping", results)
        hypotheses: List[Dict[str, Any]] = results.get("hypotheses", [])

        self.scan_results = mapping
        if "tech_stack" in results:
            self.tech_stack = results["tech_stack"]

        # Persist the project profile
        self.db.save_project_profile(self.project_path, self.tech_stack, mapping)

        # Spawn HUNT tasks from hypotheses
        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
                parent_id=task.id
            )
            self.db.save_hypothesis(self.project_path, hypo_task)
            self.spawn_task(hypo_task)

        # Automatically spawn HUNT tasks for high-value targets if requested
        if task.context.get("auto_hunt"):
            for path, data in mapping.items():
                if isinstance(data, dict) and data.get("is_high_value"):
                    self.spawn_task(Task(TaskType.HUNT, path, parent_id=task.id))

    async def _handle_hunt(self, task: Task) -> None:
        """Runs the Hunter on a single target.

        Args:
            task: The hunt task to handle.
        """
        # Mark the hypothesis as running if it came from the DB
        if isinstance(task, Hypothesis):
            self.db.update_hypothesis_status(task.id, "running")

        results = await self.hunter.hunt_vulnerabilities([task.target], project_root=".")

        # Process findings
        findings = results.get("findings", [])
        for finding in findings:
            self.findings.append(finding)
            self.db.save_finding(self.project_path, finding)
            self.log(f"Found potential issue: [bold yellow]{finding.title}[/bold yellow]")
            # Automatically spawn verification task
            self.spawn_task(Task(TaskType.VERIFY, finding.title, context={"finding": finding}, parent_id=task.id))

        # Mark hypothesis complete/failed based on whether findings were found
        if isinstance(task, Hypothesis):
            status = "completed" if findings else "failed"
            self.db.update_hypothesis_status(task.id, status, result={"finding_count": len(findings)})

        # Process new hypotheses (Recursive Loop)
        hypotheses = results.get("hypotheses", [])
        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
                parent_id=task.id
            )
            self.db.save_hypothesis(self.project_path, hypo_task)
            self.spawn_task(hypo_task)

    async def _handle_verify(self, task: Task) -> None:
        """Runs the Validator on a finding.

        Args:
            task: The verification task to handle.
        """
        finding: Optional[Finding] = task.context.get("finding")
        if not finding:
            return

        result = await self.validator.verify_finding(finding, self.tech_stack, log_fn=self.log)
        if result.get("status"):
            finding.verification_status = result["status"]
            self.log(f"Verification Result: [bold {'green' if result['status'] == 'Verified' else 'red'}]{result['status']}[/bold]")
        if result.get("poc_code"):
            finding.poc = result["poc_code"]
        finding.save()

        # Sync the updated status back to the database
        self.db.update_finding_status(
            self.project_path,
            finding.title,
            finding.file_path,
            finding.verification_status,
            finding.poc,
        )

    # TUI-facing methods — call agents directly without touching the task queue,
    # so each phase stays isolated and the user controls when to advance.
    async def run_archaeologist(self, path: str = ".") -> Dict[str, Any]:
        """Run the Archaeologist scan and return the project mapping.

        Calls the Archaeologist agent directly, without enqueuing follow-on HUNT
        tasks.  Hypotheses are persisted to the database so the user can review
        the project map and decide which targets to hunt.

        Args:
            path: The project path to scan.

        Returns:
            The scan results mapping (file path → {summary, is_high_value}).
        """
        results = await self.archaeologist.scan_project(path, log_fn=self.log)

        mapping: Dict[str, Any] = results.get("mapping", results)
        hypotheses: List[Dict[str, Any]] = results.get("hypotheses", [])

        self.scan_results = mapping
        if "tech_stack" in results:
            self.tech_stack = results["tech_stack"]

        self.db.save_project_profile(self.project_path, self.tech_stack, mapping)

        # Persist hypotheses for later use, but do not queue HUNT tasks —
        # the user decides which targets to hunt via the TUI.
        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
            )
            self.db.save_hypothesis(self.project_path, hypo_task)
            self.log(f"Hypothesis: [dim]{hypo_task.target}[/dim] — {hypo_task.description}")

        return mapping

    async def run_hunter(self, targets: List[str], path: str = ".") -> List[Finding]:
        """Run the Hunter on a list of targets and return new findings.

        Calls the Hunter agent directly for each target without enqueuing
        follow-on VERIFY tasks.  New findings are appended to
        ``self.findings``; recursive hypotheses are persisted but not queued.

        Args:
            targets: List of file paths to hunt in.
            path: Project root path.

        Returns:
            The list of findings discovered in this run.
        """
        new_findings: List[Finding] = []
        for target in targets:
            self.log(f"Hunting: [cyan]{target}[/cyan]")
            results = await self.hunter.hunt_vulnerabilities([target], project_root=path, log_fn=self.log)

            for finding in results.get("findings", []):
                self.findings.append(finding)
                new_findings.append(finding)
                self.db.save_finding(self.project_path, finding)
                self.log(f"Found potential issue: [bold yellow]{finding.title}[/bold yellow]")

            # Persist recursive hypotheses without auto-queueing them.
            for hypo in results.get("hypotheses", []):
                hypo_task = Hypothesis(
                    type=TaskType.HUNT,
                    target=hypo.get("target", ""),
                    description=hypo.get("description", ""),
                    confidence=hypo.get("confidence", 0.5),
                )
                self.db.save_hypothesis(self.project_path, hypo_task)
                self.log(f"Hypothesis: [dim]{hypo_task.target}[/dim] — {hypo_task.description}")

        return new_findings

    async def verify_finding(self, finding: Finding) -> Dict[str, Any]:
        """Verify a single finding and update its status in place.

        Calls the Validator agent directly without using the task queue.

        Args:
            finding: The finding object to verify.

        Returns:
            A dictionary with 'status' and 'poc_code'.
        """
        result = await self.validator.verify_finding(finding, self.tech_stack, log_fn=self.log)
        if result.get("status"):
            finding.verification_status = result["status"]
            self.log(
                f"Verification Result: "
                f"[bold {'green' if result['status'] == 'Verified' else 'red'}]"
                f"{result['status']}[/bold]"
            )
        if result.get("poc_code"):
            finding.poc = result["poc_code"]
        finding.save()
        self.db.update_finding_status(
            self.project_path,
            finding.title,
            finding.file_path,
            finding.verification_status,
            finding.poc,
        )
        return {"status": finding.verification_status, "poc_code": finding.poc}

