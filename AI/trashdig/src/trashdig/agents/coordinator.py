from typing import Dict, Any, List, Optional, Callable
from trashdig.agents.archaeologist import create_archaeologist_agent
from trashdig.agents.hunter import create_hunter_agent
from trashdig.agents.validator import create_validator_agent
from trashdig.agents.types import Task, TaskType, TaskStatus, Hypothesis
from trashdig.config import Config
from trashdig.findings import Finding

class Coordinator:
    """Coordinatates the hypothesis-driven workflow between agents."""

    def __init__(self, config: Config):
        self.config = config
        self.archaeologist = create_archaeologist_agent(config.agents.get("archaeologist"))
        self.hunter = create_hunter_agent(config.agents.get("hunter"))
        self.validator = create_validator_agent(config.agents.get("validator"))
        
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.scan_results: Dict[str, Any] = {}
        self.tech_stack: str = ""
        self.findings: List[Finding] = []
        
        # Callback for TUI updates
        self.on_task_event: Optional[Callable[[str], None]] = None

    def log(self, message: str):
        """Logs a message through the event callback."""
        if self.on_task_event:
            self.on_task_event(message)

    def spawn_task(self, task: Task):
        """Adds a new task to the queue."""
        self.log(f"Spawned Task: [cyan]{task.type.name}[/cyan] -> [dim]{task.target}[/dim]")
        self.task_queue.append(task)

    async def run_loop(self):
        """Main Observe-Hypothesize-Verify loop."""
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

    async def _handle_scan(self, task: Task):
        """Runs the Archaeologist scan."""
        results = await self.archaeologist.scan_project(task.target)
        
        # Handle new format {"mapping": ..., "hypotheses": ...}
        mapping = results.get("mapping", results)
        hypotheses = results.get("hypotheses", [])
        
        self.scan_results = mapping
        if "tech_stack" in results:
            self.tech_stack = results["tech_stack"]
        
        # Spawn HUNT tasks from hypotheses
        for hypo in hypotheses:
            self.spawn_task(Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target"),
                description=hypo.get("description"),
                confidence=hypo.get("confidence", 0.5),
                parent_id=task.id
            ))

        # Automatically spawn HUNT tasks for high-value targets if requested
        if task.context.get("auto_hunt"):
            for path, data in mapping.items():
                if isinstance(data, dict) and data.get("is_high_value"):
                    self.spawn_task(Task(TaskType.HUNT, path, parent_id=task.id))

    async def _handle_hunt(self, task: Task):
        """Runs the Hunter on a single target."""
        # HunterAgent.hunt_vulnerabilities currently takes a list, 
        # but in Phase 2 we want it to handle single file and return hypotheses.
        findings = await self.hunter.hunt_vulnerabilities([task.target], project_root=".")
        for finding in findings:
            self.findings.append(finding)
            self.log(f"Found potential issue: [bold yellow]{finding.title}[/bold yellow]")
            # Automatically spawn verification task
            self.spawn_task(Task(TaskType.VERIFY, finding.title, context={"finding": finding}, parent_id=task.id))

    async def _handle_verify(self, task: Task):
        """Runs the Validator on a finding."""
        finding = task.context.get("finding")
        if not finding:
            return
            
        result = await self.validator.verify_finding(finding, self.tech_stack)
        if result.get("status"):
            finding.verification_status = result["status"]
            self.log(f"Verification Result: [bold {'green' if result['status'] == 'Verified' else 'red'}]{result['status']}[/bold]")
        if result.get("poc_code"):
            finding.poc = result["poc_code"]
        finding.save()

    # Backward compatibility for existing TUI methods
    async def run_archaeologist(self, path: str = ".") -> Dict[str, Any]:
        task = Task(TaskType.SCAN, path)
        self.spawn_task(task)
        await self.run_loop()
        return self.scan_results

    async def run_hunter(self, targets: List[str], path: str = ".") -> List[Finding]:
        for target in targets:
            self.spawn_task(Task(TaskType.HUNT, target, context={"project_root": path}))
        await self.run_loop()
        return self.findings

    async def verify_finding(self, finding: Finding) -> Dict[str, Any]:
        task = Task(TaskType.VERIFY, finding.title, context={"finding": finding})
        self.spawn_task(task)
        await self.run_loop()
        # Mocking return for existing API
        return {"status": finding.verification_status, "poc_code": finding.poc}
