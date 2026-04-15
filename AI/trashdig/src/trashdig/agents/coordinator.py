import os
import uuid
from typing import Dict, Any, List, Optional, Callable, Set
import asyncio
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from trashdig.agents.callbacks import TrashDigCallback
from trashdig.agents.recon import create_stack_scout_agent, create_web_route_mapper_agent
from trashdig.agents.hunter import create_hunter_agent
from trashdig.agents.validator import create_validator_agent
from trashdig.agents.skeptic import create_skeptic_agent
from trashdig.agents.types import Task, TaskType, TaskStatus, Hypothesis
from trashdig.config import Config
from trashdig.services.database import ProjectDatabase
from trashdig.services.cost import CostTracker
from trashdig.services.permissions import PermissionManager
from trashdig.findings import Finding
from trashdig.engine.engine import Engine


class Coordinator:
    """Coordinatates the hypothesis-driven workflow between agents."""

    def __init__(
        self,
        config: Config,
        project_path: str = ".",
        on_confirm: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        """Initializes the Coordinator with the given configuration.

        Args:
            config: The project configuration object.
            project_path: Root directory of the project being scanned.
                Used as the key for all database records.
            on_confirm: Optional callback for tool call confirmation.
        """
        self.config = config
        self.project_path = project_path
        self.permission_manager = PermissionManager(config, on_confirm=on_confirm)

        self.stack_scout = create_stack_scout_agent(
            config.get_agent_config("stack_scout") or config.get_agent_config("archaeologist"),
            permission_manager=self.permission_manager,
        )
        self.web_route_mapper = create_web_route_mapper_agent(
            config.get_agent_config("web_route_mapper"),
            permission_manager=self.permission_manager,
        )
        self.hunter = create_hunter_agent(
            config.get_agent_config("hunter"),
            permission_manager=self.permission_manager,
        )
        self.skeptic = create_skeptic_agent(
            config.get_agent_config("skeptic"),
            permission_manager=self.permission_manager,
        )
        self.validator = create_validator_agent(
            config.get_agent_config("validator"),
            permission_manager=self.permission_manager,
        )

        self.cost_tracker = CostTracker()
        self.semaphore = asyncio.Semaphore(config.max_parallel_tasks)
        self.active_tasks: Set[asyncio.Task] = set()

        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.scan_results: Dict[str, Any] = {}
        self.attack_surface: List[Dict[str, Any]] = []
        self.tech_stack: str = ""
        self.findings: List[Finding] = []

        # LLM usage counters (cumulative)
        self.total_messages: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.llm_errors: int = 0

        # Internal trackers for live streaming updates
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._current_msg_input: int = 0
        self._current_msg_output: int = 0

        # Persistent knowledge store — must be initialised before Engine so
        # we can retrieve/create the scan session ID.
        db_path = getattr(config, "db_path", ".trashdig/trashdig.db")
        self.db = ProjectDatabase(db_path)

        # Stable scan session ID shared across all agent calls in this
        # invocation.  All ADK session data (event history) is written to
        # the same SQLite file via SqliteSessionService so sessions survive
        # process restarts.
        self.scan_session_id: str = self.db.get_or_create_scan_session(
            project_path if project_path else "."
        )
        session_service = SqliteSessionService(db_path=db_path)
        self.engine = Engine(
            session_service=session_service,
            session_id_prefix=self.scan_session_id,
        )

        # Wire ADK-native callbacks to all agents so tool calls, token stats,
        # costs, and DB logging happen automatically without manual threading.
        cb = TrashDigCallback(self)
        for _agent in (
            self.stack_scout, self.web_route_mapper,
            self.hunter, self.skeptic, self.validator,
        ):
            _agent.before_tool_callback = cb.on_before_tool
            _agent.after_model_callback = cb.on_after_model
            _agent.on_model_error_callback = cb.on_model_error

        # Callback for TUI updates
        self.on_task_event: Optional[Callable[[str], None]] = None
        self.on_stats_event: Optional[Callable[[], None]] = None

    def _on_stats(
        self,
        input_tokens: int,
        output_tokens: int,
        new_msg: bool = False,
        model_name: Optional[str] = None,
    ) -> None:
        """Accumulate LLM usage stats from a single run_prompt call.

        Args:
            input_tokens: Latest token count for the current request.
            output_tokens: Latest token count for the current request.
            new_msg: Whether this is the final update for a message.
            model_name: The name of the model used for this request.
        """
        if new_msg:
            self.total_messages += 1
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens
            self._current_msg_input = 0
            self._current_msg_output = 0

            if model_name:
                self.cost_tracker.record_usage(model_name, input_tokens, output_tokens)
        else:
            self._current_msg_input = input_tokens
            self._current_msg_output = output_tokens

        # Exported cumulative totals for the UI
        self.input_tokens = self._total_input_tokens + self._current_msg_input
        self.output_tokens = self._total_output_tokens + self._current_msg_output

        if self.on_stats_event:
            self.on_stats_event()

    def _agent_by_name(self, name: str) -> Any:
        """Return the agent instance for *name*, or None if not found.

        Used by TrashDigCallback to look up the model name for cost tracking.

        Args:
            name: The agent name (e.g. ``"hunter"``).

        Returns:
            The matching agent instance, or ``None``.
        """
        agents = {
            self.stack_scout.name: self.stack_scout,
            self.web_route_mapper.name: self.web_route_mapper,
            self.hunter.name: self.hunter,
            self.skeptic.name: self.skeptic,
            self.validator.name: self.validator,
        }
        return agents.get(name)

    def _on_llm_error(self) -> None:
        """Increment the LLM error counter."""
        self.llm_errors += 1
        if self.on_stats_event:
            self.on_stats_event()

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
        self.log(
            f"Spawned Task: [cyan]{task.type.name}[/cyan] -> [dim]{task.target}[/dim]"
        )
        self.task_queue.append(task)

    async def run_loop(self) -> None:
        """Main Observe-Hypothesize-Verify loop.

        This loop processes the task queue until it is empty, delegating tasks
        to the appropriate agents based on the task type.
        """
        while self.task_queue or self.active_tasks:
            # While we have room and tasks, spawn workers
            while self.task_queue and len(self.active_tasks) < self.config.max_parallel_tasks:
                task = self.task_queue.pop(0)
                worker = asyncio.create_task(self._execute_task_with_semaphore(task))
                self.active_tasks.add(worker)
                worker.add_done_callback(self.active_tasks.discard)

            if self.active_tasks:
                # Wait for at least one task to finish before checking the queue again
                await asyncio.wait(self.active_tasks, return_when=asyncio.FIRST_COMPLETED)
            elif self.task_queue:
                # This should not happen given the inner while loop, but for safety:
                continue
            else:
                break

    async def _execute_task_with_semaphore(self, task: Task) -> None:
        """Worker wrapper that acquires the semaphore and executes a task.

        Args:
            task: The task to execute.
        """
        async with self.semaphore:
            task.status = TaskStatus.RUNNING
            self.log(
                f"Executing: [bold blue]{task.type.name}[/bold blue] ([dim]{task.target}[/dim])"
            )

            try:
                if task.type == TaskType.SCAN:
                    await self._handle_scan(task)
                elif task.type == TaskType.HUNT:
                    await self._handle_hunt(task)
                elif task.type == TaskType.VERIFY:
                    await self._handle_verify(task)

                task.status = TaskStatus.COMPLETED
                self.completed_tasks.append(task)
                self.log(
                    f"Finished: [bold green]{task.type.name}[/bold green] ([dim]{task.target}[/dim])"
                )
            except Exception as e:
                task.status = TaskStatus.FAILED
                self.log(f"[red]Task Failed: {str(e)}[/red]")

    async def _handle_scan(self, task: Task) -> None:
        """Runs the Recon (StackScout and WebRouteMapper) scan.

        Args:
            task: The scan task to handle.
        """
        results = await self.stack_scout.scan(
            task.target,
            engine=self.engine,
        )

        mapping: Dict[str, Any] = results.get("mapping", {})
        hypotheses: List[Dict[str, Any]] = results.get("hypotheses", [])
        self.tech_stack = results.get("tech_stack", "")
        self.scan_results = mapping

        # If it's a web app, also run WebRouteMapper
        if results.get("is_web_app"):
            route_results = await self.web_route_mapper.map_routes(
                task.target,
                engine=self.engine,
            )
            self.attack_surface = route_results.get("attack_surface", [])

        # Persist the project profile
        full_profile = {"mapping": self.scan_results, "attack_surface": self.attack_surface}
        self.db.save_project_profile(self.project_path, self.tech_stack, full_profile)

        # Spawn HUNT tasks from hypotheses
        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
                parent_id=task.id,
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

        results = await self.hunter.hunt_vulnerabilities(
            [task.target],
            project_root=".",
            engine=self.engine,
        )

        # Process findings
        findings = results.get("findings", [])
        for finding in findings:
            self.findings.append(finding)
            self.db.save_finding(self.project_path, finding)
            self.log(
                f"Found potential issue: [bold yellow]{finding.title}[/bold yellow]"
            )
            # Automatically spawn verification task
            self.spawn_task(
                Task(
                    TaskType.VERIFY,
                    finding.title,
                    context={"finding": finding},
                    parent_id=task.id,
                )
            )

        # Mark hypothesis complete/failed based on whether findings were found
        if isinstance(task, Hypothesis):
            status = "completed" if findings else "failed"
            self.db.update_hypothesis_status(
                task.id, status, result={"finding_count": len(findings)}
            )

        # Process new hypotheses (Recursive Loop)
        hypotheses = results.get("hypotheses", [])
        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
                parent_id=task.id,
            )
            self.db.save_hypothesis(self.project_path, hypo_task)
            self.spawn_task(hypo_task)

    async def _handle_verify(self, task: Task) -> None:
        """Runs the Skeptic and Validator on a finding.

        Args:
            task: The verification task to handle.
        """
        finding: Optional[Finding] = task.context.get("finding")
        if not finding:
            return

        # 1. Run Skeptic
        skeptic_result = await self.skeptic.debunk_finding(
            finding,
            self.project_path,
            engine=self.engine,
            log_fn=self.log,
        )

        if not skeptic_result.get("is_valid", True):
            finding.verification_status = "Debunked"
            finding.save(os.path.join(self.project_path, "findings"))
            self.db.update_finding_status(
                self.project_path,
                finding.title,
                finding.file_path,
                finding.verification_status,
                "",
            )
            self.log(
                f"Skeptic Result: [bold red]Debunked[/bold red]"
            )
            return

        # 2. Run Validator
        result = await self.validator.verify_finding(
            finding,
            self.tech_stack,
            engine=self.engine,
            log_fn=self.log,
        )
        if result.get("status"):
            finding.verification_status = result["status"]
            self.log(
                f"Verification Result: [bold {'green' if result['status'] == 'Verified' else 'red'}]{result['status']}[/bold]"
            )
        if result.get("poc_code"):
            finding.poc = result["poc_code"]
        finding.save(os.path.join(self.project_path, "findings"))

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
    async def run_recon(self, path: str = ".") -> Dict[str, Any]:
        """Run the Recon (StackScout and WebRouteMapper) scan.

        Calls the StackScout agent directly, and if a web application is 
        detected, also calls WebRouteMapper.  Hypotheses are persisted.

        Args:
            path: The project path to scan.

        Returns:
            The file mapping.
        """
        results = await self.stack_scout.scan(
            path,
            engine=self.engine,
            log_fn=self.log,
        )

        mapping: Dict[str, Any] = results.get("mapping", {})
        hypotheses: List[Dict[str, Any]] = results.get("hypotheses", [])
        self.tech_stack = results.get("tech_stack", "")
        self.scan_results = mapping

        # If it's a web app, also run WebRouteMapper
        if results.get("is_web_app"):
            route_results = await self.web_route_mapper.map_routes(
                path,
                engine=self.engine,
                log_fn=self.log,
            )
            self.attack_surface = route_results.get("attack_surface", [])

        full_profile = {"mapping": self.scan_results, "attack_surface": self.attack_surface}
        self.db.save_project_profile(self.project_path, self.tech_stack, full_profile)

        # Persist hypotheses
        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
            )
            self.db.save_hypothesis(self.project_path, hypo_task)
            self.log(
                f"Hypothesis: [dim]{hypo_task.target}[/dim] — {hypo_task.description}"
            )

        self.log(
            f"Finished: [bold green]RECON[/bold green] ([dim]{path}[/dim]) — {len(mapping)} files mapped"
        )
        return self.scan_results

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
            results = await self.hunter.hunt_vulnerabilities(
                [target],
                project_root=path,
                engine=self.engine,
                log_fn=self.log,
            )

            for finding in results.get("findings", []):
                self.findings.append(finding)
                new_findings.append(finding)
                self.db.save_finding(self.project_path, finding)
                self.log(
                    f"Found potential issue: [bold yellow]{finding.title}[/bold yellow]"
                )

            for hypo in results.get("hypotheses", []):
                hypo_task = Hypothesis(
                    type=TaskType.HUNT,
                    target=hypo.get("target", ""),
                    description=hypo.get("description", ""),
                    confidence=hypo.get("confidence", 0.5),
                )
                self.db.save_hypothesis(self.project_path, hypo_task)
                self.log(
                    f"Hypothesis: [dim]{hypo_task.target}[/dim] — {hypo_task.description}"
                )

            self.log(
                f"Finished: [bold green]HUNT[/bold green] ([dim]{target}[/dim]) — {len(results.get('findings', []))} findings found"
            )

        return new_findings

    async def verify_finding(self, finding: Finding) -> Dict[str, Any]:
        """Verify a single finding and update its status in place.

        Calls the Skeptic and Validator agents directly without using the task queue.

        Args:
            finding: The finding object to verify.

        Returns:
            A dictionary with 'status' and 'poc_code'.
        """
        # 1. Run Skeptic
        skeptic_result = await self.skeptic.debunk_finding(
            finding,
            self.project_path,
            engine=self.engine,
            log_fn=self.log,
        )

        if not skeptic_result.get("is_valid", True):
            finding.verification_status = "Debunked"
            finding.save(os.path.join(self.project_path, "findings"))
            self.db.update_finding_status(
                self.project_path,
                finding.title,
                finding.file_path,
                finding.verification_status,
                "",
            )
            self.log(
                f"Skeptic Result: [bold red]Debunked[/bold red]"
            )
            return {"status": "Debunked", "poc_code": ""}

        # 2. Run Validator
        result = await self.validator.verify_finding(
            finding,
            self.tech_stack,
            engine=self.engine,
            log_fn=self.log,
        )
        if result.get("status"):
            finding.verification_status = result["status"]
            self.log(
                f"Verification Result: "
                f"[bold {'green' if result['status'] == 'Verified' else 'red'}]"
                f"{result['status']}[/bold]"
            )
        if result.get("poc_code"):
            finding.poc = result["poc_code"]
        finding.save(os.path.join(self.project_path, "findings"))
        self.db.update_finding_status(
            self.project_path,
            finding.title,
            finding.file_path,
            finding.verification_status,
            finding.poc,
        )

        self.log(
            f"Finished: [bold green]VERIFY[/bold green] ([dim]{finding.title}[/dim]) — {finding.verification_status}"
        )
        return {"status": finding.verification_status, "poc_code": finding.poc}
