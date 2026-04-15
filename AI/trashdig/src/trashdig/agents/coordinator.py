import os
from typing import Any, Dict, List, Optional, Callable

from pydantic import PrivateAttr
from google.adk.agents import LlmAgent
from google.adk.sessions.sqlite_session_service import SqliteSessionService

from trashdig.agents.callbacks import TrashDigCallback
from trashdig.agents.recon import create_stack_scout_agent, create_web_route_mapper_agent
from trashdig.agents.hunter import create_hunter_agent
from trashdig.agents.validator import create_validator_agent
from trashdig.agents.skeptic import create_skeptic_agent
from trashdig.agents.types import Hypothesis, TaskType
from trashdig.config import Config
from trashdig.services.database import ProjectDatabase
from trashdig.services.cost import CostTracker
from trashdig.services.permissions import PermissionManager
from trashdig.findings import Finding
from trashdig.engine.engine import Engine


_COORDINATOR_INSTRUCTION = """
You are TrashDig's Coordinator — an AI orchestrator for a multi-phase vulnerability scanner.

## Sub-agents

- **stack_scout**: Identifies the technology stack, maps high-value source files, and generates initial security hypotheses from the project structure.
- **web_route_mapper**: Maps all HTTP routes and endpoint handlers. Invoke only when stack_scout reports this is a web application.
- **hunter**: Deep-dive static analysis of individual source files to identify potential vulnerabilities. Returns findings and follow-up hypotheses.
- **skeptic**: Adversarial reviewer that attempts to debunk findings by identifying false positives, missed sanitizers, and framework protections.
- **validator**: Generates and executes PoC scripts in a sandbox container to confirm exploitability of findings that survive the skeptic.

## Workflow

1. RECON — Run stack_scout on the project root. If is_web_app, also run web_route_mapper.
2. HUNT — Run hunter on each high-value file and each hypothesis target. Collect new hypotheses and loop.
3. VERIFY — For each finding: run skeptic first. Only if skeptic confirms validity, run validator.

When asked to coordinate a full scan, follow this pipeline in order.
When asked for a specific phase (reconnaissance, hunting, or verification), execute only that phase.
"""


class Coordinator(LlmAgent):
    """Coordinates the hypothesis-driven vulnerability scanning workflow.

    ``Coordinator`` is an ADK ``LlmAgent`` whose ``sub_agents`` are the five
    specialist worker agents (StackScout, WebRouteMapper, Hunter, Skeptic,
    Validator).  All mutable scan state is stored in ``PrivateAttr`` fields so
    that Pydantic's ``extra='forbid'`` (inherited from ``BaseAgent``) does not
    reject them.

    The two TUI-callback attributes (``on_task_event``, ``on_stats_event``) are
    declared as proper Pydantic model fields so they can be set from outside
    the class via normal attribute assignment.
    """

    # ------------------------------------------------------------------
    # Settable TUI callbacks — declared as Pydantic fields so that
    # coordinator.on_task_event = fn works through Pydantic's __setattr__.
    # ------------------------------------------------------------------
    on_task_event: Optional[Any] = None   # Callable[[str], None]
    on_stats_event: Optional[Any] = None  # Callable[[], None]

    # ------------------------------------------------------------------
    # All mutable state — PrivateAttr keeps them out of the Pydantic schema.
    # ------------------------------------------------------------------
    _db: ProjectDatabase = PrivateAttr()
    _engine: Engine = PrivateAttr()
    _cost_tracker: CostTracker = PrivateAttr()
    _scan_session_id: str = PrivateAttr()
    _project_path: str = PrivateAttr()
    _permission_manager: PermissionManager = PrivateAttr()

    _findings: List[Finding] = PrivateAttr()
    _scan_results: Dict[str, Any] = PrivateAttr()
    _attack_surface: List[Dict[str, Any]] = PrivateAttr()
    _tech_stack: str = PrivateAttr()

    _llm_errors: int = PrivateAttr()

    def __init__(
        self,
        config: Config,
        project_path: str = ".",
        on_confirm: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        """Initialises the Coordinator with the given configuration."""
        perm = PermissionManager(config, on_confirm=on_confirm)

        stack_scout = create_stack_scout_agent(
            config.get_agent_config("stack_scout") or config.get_agent_config("archaeologist"),
            permission_manager=perm,
        )
        web_route_mapper = create_web_route_mapper_agent(
            config.get_agent_config("web_route_mapper"),
            permission_manager=perm,
        )
        hunter = create_hunter_agent(
            config.get_agent_config("hunter"),
            permission_manager=perm,
        )
        skeptic = create_skeptic_agent(
            config.get_agent_config("skeptic"),
            permission_manager=perm,
        )
        validator = create_validator_agent(
            config.get_agent_config("validator"),
            permission_manager=perm,
        )

        coordinator_cfg = config.get_agent_config("coordinator")

        super().__init__(
            name="coordinator",
            model=coordinator_cfg.model,
            instruction=_COORDINATOR_INSTRUCTION,
            description="Orchestrates the multi-phase vulnerability scanning pipeline.",
            sub_agents=[stack_scout, web_route_mapper, hunter, skeptic, validator],
        )

        # --- PrivateAttr initialisation ---
        db_path = getattr(config, "db_path", ".trashdig/trashdig.db")
        db = ProjectDatabase(db_path)
        scan_session_id = db.get_or_create_scan_session(project_path if project_path else ".")
        session_service = SqliteSessionService(db_path=db_path)
        
        cost_tracker = CostTracker()
        engine = Engine(
            session_service=session_service,
            session_id_prefix=scan_session_id,
            cost_tracker=cost_tracker,
        )

        self._db = db
        self._engine = engine
        self._cost_tracker = cost_tracker
        self._scan_session_id = scan_session_id
        self._project_path = project_path or "."
        self._permission_manager = perm
        self._findings = []
        self._scan_results = {}
        self._attack_surface = []
        self._tech_stack = ""
        self._llm_errors = 0

        # Wire ADK-native callbacks using the singleton manager
        cb = TrashDigCallback.get_instance(self)
        for _agent in (*self.sub_agents, self):
            cb.attach_to(_agent)

    # ------------------------------------------------------------------
    # TUI compatibility properties (read-only)
    # ------------------------------------------------------------------

    @property
    def project_path(self) -> str:
        return self._project_path

    @property
    def db(self) -> ProjectDatabase:
        return self._db

    @property
    def scan_session_id(self) -> str:
        return self._scan_session_id

    @property
    def findings(self) -> List[Finding]:
        return self._findings

    @property
    def scan_results(self) -> Dict[str, Any]:
        return self._scan_results

    @property
    def attack_surface(self) -> List[Dict[str, Any]]:
        return self._attack_surface

    @property
    def tech_stack(self) -> str:
        return self._tech_stack

    @property
    def task_queue(self) -> list:
        """Always empty — task-queue machinery replaced by run_full_scan()."""
        return []

    @property
    def completed_tasks(self) -> list:
        """Always empty — task-queue machinery replaced by run_full_scan()."""
        return []

    @property
    def total_messages(self) -> int:
        return self._engine.total_messages

    @property
    def input_tokens(self) -> int:
        return self._cost_tracker.total_input_tokens

    @property
    def output_tokens(self) -> int:
        return self._cost_tracker.total_output_tokens

    @property
    def total_cost(self) -> float:
        return self._cost_tracker.total_cost

    @property
    def llm_errors(self) -> int:
        return self._llm_errors

    # Convenience accessors for individual sub-agents
    @property
    def stack_scout(self):
        return self._agent_by_name("stack_scout")

    @property
    def web_route_mapper(self):
        return self._agent_by_name("web_route_mapper")

    @property
    def hunter(self):
        return self._agent_by_name("hunter")

    @property
    def skeptic(self):
        return self._agent_by_name("skeptic")

    @property
    def validator(self):
        return self._agent_by_name("validator")

    # ------------------------------------------------------------------
    # Internal helpers (called by TrashDigCallback and internal pipeline)
    # ------------------------------------------------------------------

    def _on_stats(
        self,
        input_tokens: int,
        output_tokens: int,
        new_msg: bool = False,
        model_name: Optional[str] = None,
    ) -> None:
        """Inform the TUI that stats have changed.

        The actual accounting is now handled by Engine and CostTracker.
        This method remains as a signaling hook for the TUI.
        """
        if self.on_stats_event:
            self.on_stats_event()

    def _agent_by_name(self, name: str) -> Any:
        """Return the sub-agent with *name*, or None if not found.

        Uses the ADK-native ``sub_agents`` list, so no explicit attribute
        references are needed.

        Args:
            name: The agent name (e.g. ``"hunter"``).

        Returns:
            The matching agent instance, or ``None``.
        """
        return next((a for a in self.sub_agents if a.name == name), None)

    def _on_llm_error(self) -> None:
        """Increment the LLM error counter."""
        self._llm_errors += 1
        if self.on_stats_event:
            self.on_stats_event()

    def _on_conversation(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        tool_calls: List[Dict[str, Any]],
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Delegate conversation logging to the database.

        Kept for backward compatibility with tests and direct callers.
        In production, ``TrashDigCallback.on_after_model`` handles this.
        """
        self._db.log_conversation(
            self._project_path, agent_name, prompt, response,
            tool_calls, input_tokens, output_tokens,
        )

    def log(self, message: str) -> None:
        """Emit a progress message through the TUI event callback.

        Args:
            message: The message to log (Rich markup supported).
        """
        if self.on_task_event:
            self.on_task_event(message)

    # ------------------------------------------------------------------
    # Full automated pipeline (replaces the old run_loop / task-queue)
    # ------------------------------------------------------------------

    async def run_full_scan(self, path: str = ".") -> None:
        """Run the full SCAN → HUNT → VERIFY pipeline with hypothesis loop.

        Replaces the old ``run_loop()`` / asyncio task-queue machinery with a
        clean sequential pipeline.  Use this for fully-automated scanning; use
        the individual TUI-facing methods for interactive step-by-step scanning.

        Args:
            path: The project root directory to scan.
        """
        # Phase 1: Recon
        mapping = await self.run_recon(path)

        # Phase 2: Hypothesis-driven hunting loop
        targets: set = {
            p for p, d in mapping.items()
            if isinstance(d, dict) and d.get("is_high_value")
        }
        hunted: set = set()

        while targets - hunted:
            batch = list(targets - hunted)
            _, new_hypotheses = await self._hunt_batch(batch, path)
            hunted.update(batch)
            for hypo in new_hypotheses:
                target = hypo.get("target", "")
                if target and target not in hunted:
                    targets.add(target)

        # Phase 3: Verify all accumulated findings
        for finding in list(self._findings):
            await self.verify_finding(finding)

    async def _hunt_batch(
        self, targets: List[str], path: str = "."
    ) -> tuple:
        """Run hunter on *targets*, return (new_findings, new_hypotheses).

        Args:
            targets: List of file paths to hunt in.
            path: Project root directory.

        Returns:
            A tuple of (new_findings: List[Finding], new_hypotheses: List[dict]).
        """
        new_findings: List[Finding] = []
        all_hypotheses: List[Dict[str, Any]] = []

        for target in targets:
            self.log(f"[bold]Coordinator:[/bold] hunting [cyan]{target}[/cyan]")
            results = await self._agent_by_name("hunter").hunt_vulnerabilities(
                [target],
                project_root=path,
                engine=self._engine,
                log_fn=self.log,
            )
            for finding in results.get("findings", []):
                self._findings.append(finding)
                new_findings.append(finding)
                self._db.save_finding(self._project_path, finding)
                self.log(
                    f"Found potential issue: [bold yellow]{finding.title}[/bold yellow]"
                )
            all_hypotheses.extend(results.get("hypotheses", []))

        return new_findings, all_hypotheses

    # ------------------------------------------------------------------
    # TUI-facing methods — call agents directly without the task queue,
    # so each phase stays isolated and the user controls when to advance.
    # ------------------------------------------------------------------

    async def run_recon(self, path: str = ".") -> Dict[str, Any]:
        """Run the Recon (StackScout and WebRouteMapper) scan.

        Calls the StackScout agent directly, and if a web application is
        detected, also calls WebRouteMapper.  Hypotheses are persisted.

        Args:
            path: The project path to scan.

        Returns:
            The file mapping dict.
        """
        results = await self.stack_scout.scan(
            path,
            engine=self._engine,
            log_fn=self.log,
        )

        mapping: Dict[str, Any] = results.get("mapping", {})
        hypotheses: List[Dict[str, Any]] = results.get("hypotheses", [])
        self._tech_stack = results.get("tech_stack", "")
        self._scan_results = mapping

        if results.get("is_web_app"):
            route_results = await self.web_route_mapper.map_routes(
                path,
                engine=self._engine,
                log_fn=self.log,
            )
            self._attack_surface = route_results.get("attack_surface", [])

        full_profile = {"mapping": self._scan_results, "attack_surface": self._attack_surface}
        self._db.save_project_profile(self._project_path, self._tech_stack, full_profile)

        for hypo in hypotheses:
            hypo_task = Hypothesis(
                type=TaskType.HUNT,
                target=hypo.get("target", ""),
                description=hypo.get("description", ""),
                confidence=hypo.get("confidence", 0.5),
            )
            self._db.save_hypothesis(self._project_path, hypo_task)
            self.log(
                f"Hypothesis: [dim]{hypo_task.target}[/dim] — {hypo_task.description}"
            )

        self.log(
            f"Finished: [bold green]RECON[/bold green] ([dim]{path}[/dim]) — "
            f"{len(mapping)} files mapped"
        )
        return self._scan_results

    async def run_hunter(self, targets: List[str], path: str = ".") -> List[Finding]:
        """Run the Hunter on a list of targets and return new findings.

        Calls the Hunter agent directly for each target.  New findings are
        appended to ``self.findings``; recursive hypotheses are persisted
        but not auto-queued (use ``run_full_scan()`` for that).

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
                engine=self._engine,
                log_fn=self.log,
            )

            for finding in results.get("findings", []):
                self._findings.append(finding)
                new_findings.append(finding)
                self._db.save_finding(self._project_path, finding)
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
                self._db.save_hypothesis(self._project_path, hypo_task)
                self.log(
                    f"Hypothesis: [dim]{hypo_task.target}[/dim] — {hypo_task.description}"
                )

            self.log(
                f"Finished: [bold green]HUNT[/bold green] ([dim]{target}[/dim]) — "
                f"{len(results.get('findings', []))} findings found"
            )

        return new_findings

    async def verify_finding(self, finding: Finding) -> Dict[str, Any]:
        """Verify a single finding and update its status in place.

        Calls the Skeptic and Validator agents directly without using any
        task queue.

        Args:
            finding: The finding object to verify.

        Returns:
            A dictionary with ``'status'`` and ``'poc_code'``.
        """
        # 1. Run Skeptic
        skeptic_result = await self.skeptic.debunk_finding(
            finding,
            self._project_path,
            engine=self._engine,
            log_fn=self.log,
        )

        if not skeptic_result.get("is_valid", True):
            finding.verification_status = "Debunked"
            finding.save(os.path.join(self._project_path, "findings"))
            self._db.update_finding_status(
                self._project_path,
                finding.title,
                finding.file_path,
                finding.verification_status,
                "",
            )
            self.log("Skeptic Result: [bold red]Debunked[/bold red]")
            return {"status": "Debunked", "poc_code": ""}

        # 2. Run Validator
        result = await self.validator.verify_finding(
            finding,
            self._tech_stack,
            engine=self._engine,
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
        finding.save(os.path.join(self._project_path, "findings"))
        self._db.update_finding_status(
            self._project_path,
            finding.title,
            finding.file_path,
            finding.verification_status,
            finding.poc,
        )

        self.log(
            f"Finished: [bold green]VERIFY[/bold green] ([dim]{finding.title}[/dim]) — "
            f"{finding.verification_status}"
        )
        return {"status": finding.verification_status, "poc_code": finding.poc}
