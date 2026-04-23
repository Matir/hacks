import functools
import logging
import os
from collections.abc import Callable
from typing import Any

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent
from google.adk.artifacts import BaseArtifactService
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.adk.tools import AgentTool, FunctionTool
from pydantic import PrivateAttr

from trashdig.agents.code_investigator import create_code_investigator_agent
from trashdig.agents.hunter import create_hunter_agent
from trashdig.agents.recon import (
    create_stack_scout_agent,
    create_web_route_mapper_agent,
)
from trashdig.agents.skeptic import create_skeptic_agent
from trashdig.agents.summarizer import create_summarizer_agent
from trashdig.agents.utils.callbacks import TrashDigCallback
from trashdig.agents.utils.helpers import load_prompt, read_file_content, run_agent
from trashdig.agents.utils.json_utils import parse_json_response
from trashdig.agents.utils.types import EngineState, Hypothesis, TaskType
from trashdig.agents.validator import create_validator_agent
from trashdig.config import Config
from trashdig.findings import Finding
from trashdig.services.cost import CostTracker
from trashdig.services.database import ProjectDatabase, get_database
from trashdig.services.permissions import PermissionManager
from trashdig.services.session import get_session_service
from trashdig.tools import (
    exit_loop,
    get_next_hypothesis,
    save_findings,
    save_hypotheses,
    update_hypothesis_status,
)
from trashdig.tools.mcp_toolsets import build_mcp_toolsets

logger = logging.getLogger(__name__)


class Coordinator(LlmAgent):
    """Coordinates the hypothesis-driven vulnerability scanning workflow."""

    # ------------------------------------------------------------------
    # Settable TUI callbacks
    # ------------------------------------------------------------------
    on_task_event: Any | None = None
    on_stats_event: Any | None = None

    # ------------------------------------------------------------------
    # All mutable state
    # ------------------------------------------------------------------
    _config: Config = PrivateAttr()
    _db: ProjectDatabase = PrivateAttr()
    _session_service: BaseSessionService = PrivateAttr()
    _artifact_service: BaseArtifactService | None = PrivateAttr()
    _cost_tracker: CostTracker = PrivateAttr()
    _scan_session_id: str = PrivateAttr()
    _project_path: str = PrivateAttr()
    _permission_manager: PermissionManager = PrivateAttr()
    _state: EngineState = PrivateAttr(default=EngineState.IDLE)

    _findings: list[Finding] = PrivateAttr()
    _scan_results: dict[str, Any] = PrivateAttr()
    _attack_surface: list[dict[str, Any]] = PrivateAttr()
    _tech_stack: str = PrivateAttr()

    _summarizer: Any = PrivateAttr()
    _llm_errors: int = PrivateAttr()

    def __init__(
        self,
        config: Config,
        project_path: str | None = None,
        on_confirm: Callable[[str, dict[str, Any]], bool] | None = None,
        artifact_service: BaseArtifactService | None = None,
    ):
        """Initialises the Coordinator with the given configuration."""
        if project_path is None:
            project_path = config.workspace_root

        # Ensure it's a string even if mocked in tests
        project_path_str = str(project_path)

        perm = PermissionManager(config, on_confirm=on_confirm)

        code_investigator = create_code_investigator_agent(
            config.get_agent_config("code_investigator"),
            permission_manager=perm,
        )
        investigator_tool = AgentTool(code_investigator)

        stack_scout = create_stack_scout_agent(
            config.get_agent_config("stack_scout"),
            permission_manager=perm,
            extra_tools=build_mcp_toolsets(config, "stack_scout"),
        )
        web_route_mapper = create_web_route_mapper_agent(
            config.get_agent_config("web_route_mapper"),
            permission_manager=perm,
            extra_tools=build_mcp_toolsets(config, "web_route_mapper"),
        )
        hunter = create_hunter_agent(
            config.get_agent_config("hunter"),
            permission_manager=perm,
            extra_tools=[investigator_tool] + build_mcp_toolsets(config, "hunter"),
        )

        skeptic = create_skeptic_agent(
            config.get_agent_config("skeptic"),
            permission_manager=perm,
            extra_tools=[investigator_tool] + build_mcp_toolsets(config, "skeptic"),
        )

        validator = create_validator_agent(
            config.get_agent_config("validator"),
            permission_manager=perm,
            extra_tools=build_mcp_toolsets(config, "validator"),
        )

        summarizer = create_summarizer_agent(
            config.get_agent_config("summarizer") or config.get_agent_config("hunter")
        )

        db_path = getattr(config, "db_path", ".trashdig/trashdig.db")
        if not isinstance(db_path, str):
            db_path = ".trashdig/trashdig.db"

        # Create the HunterOrchestrator and wrap it in a LoopAgent
        hunter_orchestrator = LlmAgent(
            name="hunter_orchestrator",
            model=config.get_agent_config("hunter").model,
            instruction=load_prompt("hunter_orchestrator.md"),
            tools=[
                FunctionTool(functools.partial(get_next_hypothesis, project_path=project_path, db_path=db_path)),
                FunctionTool(functools.partial(update_hypothesis_status, db_path=db_path)),
                FunctionTool(functools.partial(save_findings, project_path=project_path, db_path=db_path)),
                FunctionTool(functools.partial(save_hypotheses, project_path=project_path, db_path=db_path)),
                FunctionTool(exit_loop),
            ],
            sub_agents=[hunter],
        )
        hunter_loop = LoopAgent(
            name="hunter_loop",
            sub_agents=[hunter_orchestrator],
            description="Autonomous loop for processing security hypotheses.",
        )

        coordinator_cfg = config.get_agent_config("coordinator")

        super().__init__(
            name="coordinator",
            model=coordinator_cfg.model,
            instruction=load_prompt("coordinator.md"),
            description="Orchestrates the multi-phase vulnerability scanning pipeline.",
            sub_agents=[stack_scout, web_route_mapper, hunter_loop, skeptic, validator],
        )

        # --- PrivateAttr initialisation ---
        db = get_database(db_path)
        scan_session_id = db.get_or_create_scan_session(project_path_str)
        session_service = get_session_service()

        cost_tracker = CostTracker()

        object.__setattr__(self, "_config", config)
        object.__setattr__(self, "_db", db)
        object.__setattr__(self, "_session_service", session_service)
        object.__setattr__(self, "_artifact_service", artifact_service)
        object.__setattr__(self, "_cost_tracker", cost_tracker)
        object.__setattr__(self, "_scan_session_id", scan_session_id)
        object.__setattr__(self, "_project_path", project_path_str)
        object.__setattr__(self, "_permission_manager", perm)
        object.__setattr__(self, "_findings", [])
        object.__setattr__(self, "_scan_results", {})
        object.__setattr__(self, "_attack_surface", [])
        object.__setattr__(self, "_tech_stack", "")
        object.__setattr__(self, "_summarizer", summarizer)
        object.__setattr__(self, "_llm_errors", 0)
        object.__setattr__(self, "_state", EngineState.IDLE)

        # Wire ADK-native callbacks using the singleton manager
        cb = TrashDigCallback.get_instance(self)
        for _agent in (*self.sub_agents, self, hunter_orchestrator):
            cb.attach_to(_agent)

    # ------------------------------------------------------------------
    # TUI compatibility properties (read-only)
    # ------------------------------------------------------------------

    @property
    def config(self) -> Config:
        """Returns the TrashDig configuration."""
        return self._config

    @property
    def project_path(self) -> str:
        """Returns the absolute path to the project root."""
        return self._project_path

    @property
    def db(self) -> ProjectDatabase:
        """Returns the project database instance."""
        return self._db

    @property
    def scan_session_id(self) -> str:
        """Returns the unique ID for the current scan session."""
        return self._scan_session_id

    @property
    def session_id(self) -> str:
        """Alias for scan_session_id."""
        return self._scan_session_id

    @property
    def findings(self) -> list[Finding]:
        """Returns the list of discovered findings."""
        return self._findings

    @findings.setter
    def findings(self, value: list[Finding]) -> None:
        object.__setattr__(self, "_findings", value)

    @property
    def scan_results(self) -> dict[str, Any]:
        """Returns the project mapping results."""
        return self._scan_results

    @scan_results.setter
    def scan_results(self, value: dict[str, Any]) -> None:
        object.__setattr__(self, "_scan_results", value)

    @property
    def attack_surface(self) -> list[dict[str, Any]]:
        """Returns the list of discovered web endpoints."""
        return self._attack_surface

    @property
    def tech_stack(self) -> str:
        """Returns the identified technology stack string."""
        return self._tech_stack

    @property
    def total_cost(self) -> float:
        """Returns the total USD cost of the scan session."""
        return self._cost_tracker.total_cost

    @property
    def input_tokens(self) -> int:
        """Returns the total input tokens used."""
        return self._cost_tracker.total_input_tokens

    @property
    def output_tokens(self) -> int:
        """Returns the total output tokens used."""
        return self._cost_tracker.total_output_tokens

    @property
    def total_messages(self) -> int:
        """Returns the total number of LLM messages."""
        return self._cost_tracker.total_messages

    @property
    def task_queue(self) -> list[Any]:
        """Returns the current task queue (stub for TUI compatibility)."""
        return []

    @property
    def completed_tasks(self) -> list[Any]:
        """Returns the completed tasks (stub for TUI compatibility)."""
        return []

    @property
    def hunter(self) -> BaseAgent:
        """Returns the Hunter agent instance."""
        # Find it in sub_agents or sub_agents of sub_agents
        for sa in self.sub_agents:
            if sa.name == "hunter_loop":
                return sa.sub_agents[0].sub_agents[0]  # hunter_loop -> orchestrator -> hunter
        raise RuntimeError("Hunter agent not found in Coordinator sub-agents.")

    @property
    def stack_scout(self) -> BaseAgent:
        """Returns the StackScout agent instance."""
        for sa in self.sub_agents:
            if sa.name == "stack_scout":
                return sa
        raise RuntimeError("StackScout agent not found in Coordinator sub-agents.")

    @property
    def web_route_mapper(self) -> BaseAgent:
        """Returns the WebRouteMapper agent instance."""
        for sa in self.sub_agents:
            if sa.name == "web_route_mapper":
                return sa
        raise RuntimeError("WebRouteMapper agent not found in Coordinator sub-agents.")

    @property
    def hunter_loop(self) -> BaseAgent:
        """Returns the Hunter LoopAgent instance."""
        for sa in self.sub_agents:
            if sa.name == "hunter_loop":
                return sa
        raise RuntimeError("Hunter loop agent not found in Coordinator sub-agents.")

    @property
    def skeptic(self) -> BaseAgent:
        """Returns the Skeptic agent instance."""
        for sa in self.sub_agents:
            if sa.name == "skeptic":
                return sa
        raise RuntimeError("Skeptic agent not found in Coordinator sub-agents.")

    @property
    def validator(self) -> BaseAgent:
        """Returns the Validator agent instance."""
        for sa in self.sub_agents:
            if sa.name == "validator":
                return sa
        raise RuntimeError("Validator agent not found in Coordinator sub-agents.")

    @property
    def state(self) -> EngineState:
        """Returns the current engine state."""
        return self._state

    @property
    def llm_errors(self) -> int:
        """Returns the number of LLM errors encountered."""
        return self._llm_errors

    # ------------------------------------------------------------------
    # Internal state mutation (via Callbacks)
    # ------------------------------------------------------------------

    def _on_stats(self, in_tokens: int, out_tokens: int, new_msg: bool = False, model_name: str = "unknown") -> None:
        """Called by callbacks to update TUI stats."""
        if self.on_stats_event:
            self.on_stats_event()

    def _on_llm_error(self) -> None:
        """Called by callbacks to increment error count."""
        object.__setattr__(self, "_llm_errors", self._llm_errors + 1)
        if self.on_stats_event:
            self.on_stats_event()

    def _log_conversation(  # noqa: PLR0913
        self,
        agent_name: str,
        prompt: str,
        response: str,
        tool_calls: list[dict[str, Any]],
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._db.log_conversation(
            self._project_path, agent_name, prompt, response,
            tool_calls, input_tokens, output_tokens,
        )

    def log(self, message: str) -> None:
        """Emits a log event to the TUI or console.

        Args:
            message: The text to log (supports Rich markup).
        """
        if self.on_task_event:
            self.on_task_event(message)

    def _save_project_profile(self, tech_stack: str, profile: dict[str, Any]) -> str:
        """Internal helper to save the project profile and update local state."""
        object.__setattr__(self, "_tech_stack", tech_stack)
        object.__setattr__(self, "_scan_results", profile.get("mapping", {}))
        object.__setattr__(self, "_attack_surface", profile.get("attack_surface", []))
        self._db.save_project_profile(self._project_path, tech_stack, profile)
        return f"Project profile for {tech_stack} saved successfully."

    def _save_finding(self, raw: dict[str, Any]) -> str:
        """Internal helper to save a single finding."""
        finding = Finding(
            title=raw.get("title", "Untitled"),
            description=raw.get("description", "N/A"),
            severity=raw.get("severity", "N/A"),
            vulnerable_code=raw.get("vulnerable_code", "N/A"),
            file_path=raw.get("file_path", "N/A"),
            impact=raw.get("impact", "N/A"),
            exploitation_path=raw.get("exploitation_path", "N/A"),
            remediation=raw.get("remediation", "N/A"),
            cwe_id=raw.get("cwe_id"),
        )
        finding.save()
        self._findings.append(finding)
        self._db.save_finding(self._project_path, finding)
        return f"Finding '{finding.title}' saved successfully."

    # ------------------------------------------------------------------
    # Full automated pipeline
    # ------------------------------------------------------------------

    async def run_full_scan(self, path: str = ".") -> None:
        """Run the full SCAN → HUNT → VERIFY pipeline with hypothesis loop."""
        TrashDigCallback.get_instance().reset_turn_counts()
        # Phase 1: Recon
        await self.run_recon(path)

        # Phase 2: Hypothesis-driven hunting loop using ADK LoopAgent
        self.log("[bold]Coordinator:[/bold] starting autonomous hunting loop...")

        runner = Runner(
            agent=self.hunter_loop,
            app_name="hunter_loop",
            session_service=self._session_service,
            artifact_service=self._artifact_service,
            auto_create_session=True,
        )

        async for _ in runner.run_async(
            user_id="default_user",
            session_id=f"{self._scan_session_id}:hunt_loop",
        ):
            pass

        # Reload findings from DB as the loop agent populated it
        db_findings = self._db.get_findings(self._project_path)
        self._findings = []
        for f in db_findings:
            filtered = {k: v for k, v in f.items() if k in Finding.__dataclass_fields__}
            self._findings.append(Finding(**filtered))

        # Phase 3: Verify all accumulated findings
        for finding in list(self._findings):
            await self.verify_finding(finding)

    async def _hunt_batch(
        self, targets: list[str], path: str = "."
    ) -> tuple:
        """Kept for backward compatibility."""
        new_findings: list[Finding] = []
        all_hypotheses: list[dict[str, Any]] = []

        for target in targets:
            self.log(f"[bold]Coordinator:[/bold] hunting [cyan]{target}[/cyan]")

            prompt = load_prompt("hunter_batch.md").format(target=target)

            text = await run_agent(
                self.hunter,
                prompt,
                session_id=f"{self._scan_session_id}:hunt:{target}",
                session_service=self._session_service,
                artifact_service=self._artifact_service,
                summarizer=self._summarizer
            )
            try:
                data = parse_json_response(text)

                # Handle findings
                raw_findings = data.get("findings", [])
                for raw in raw_findings:
                    finding = Finding(
                        title=raw.get("title", "Untitled"),
                        description=raw.get("description", "No description provided"),
                        severity=raw.get("severity", "Medium"),
                        vulnerable_code=raw.get("vulnerable_code", ""),
                        file_path=target,
                        impact=raw.get("impact", "Unknown impact"),
                        exploitation_path=raw.get("exploitation_path", "Not documented"),
                        remediation=raw.get("remediation", "No remediation provided"),
                        cwe_id=raw.get("cwe_id"),
                        poc=raw.get("poc")
                    )
                    self._findings.append(finding)
                    new_findings.append(finding)
                    self._db.save_finding(self._project_path, finding)

                all_hypotheses.extend(data.get("hypotheses", []))
            except Exception:
                logger.exception("Failed to parse Hunter response for %s", target)

        return new_findings, all_hypotheses

    # ------------------------------------------------------------------
    # TUI-facing methods
    # ------------------------------------------------------------------

    async def run_recon(self, path: str = ".") -> dict[str, Any]:
        """Performs initial stack discovery and project mapping."""
        TrashDigCallback.get_instance().reset_turn_counts()
        self.log(f"[bold]Coordinator:[/bold] starting reconnaissance on [cyan]{path}[/cyan]")

        abs_path = os.path.abspath(path)  # noqa: ASYNC240
        prompt = load_prompt("recon.md").format(abs_path=abs_path)

        text = await run_agent(
            self.stack_scout,
            prompt,
            session_id=f"{self._scan_session_id}:recon:stack_scout",
            session_service=self._session_service,
            artifact_service=self._artifact_service,
            summarizer=self._summarizer
        )

        try:
            data = parse_json_response(text)
        except Exception as e:
            self.log(f"[bold red]Error:[/bold red] Failed to parse StackScout output: {e}")
            data = {}

        mapping: dict[str, Any] = data.get("mapping", {})
        hypotheses: list[dict[str, Any]] = data.get("hypotheses", [])
        self._tech_stack = data.get("tech_stack", "")
        self._scan_results = mapping

        is_web_app = data.get("is_web_app", False)

        if is_web_app:
            self.log("[bold]Coordinator:[/bold] web application detected, mapping attack surface…")
            route_prompt = load_prompt("web_route_mapper_route.md")
            r_text = await run_agent(
                self.web_route_mapper,
                route_prompt,
                session_id=f"{self._scan_session_id}:recon:routes",
                session_service=self._session_service,
                artifact_service=self._artifact_service,
                summarizer=self._summarizer
            )
            try:
                route_data = parse_json_response(r_text)
                self._attack_surface = route_data.get("attack_surface", [])
            except Exception as e:
                self.log(f"[bold red]Error:[/bold red] Failed to parse WebRouteMapper output: {e}")

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

    async def run_hunter(self, targets: list[str], path: str = ".") -> list[Finding]:
        """Runs the Hunter agent on a specific list of targets.

        Args:
            targets: List of relative file paths to analyze.
            path: Base path to the project.

        Returns:
            A list of new Finding objects discovered.
        """
        TrashDigCallback.get_instance().reset_turn_counts()
        new_findings: list[Finding] = []
        for i, target in enumerate(targets, 1):
            self.log(f"[bold]Hunter:[/bold] analysing [cyan]{target}[/cyan] ([dim]{i}/{len(targets)}[/dim])")
            content = read_file_content(os.path.join(path, target))

            prompt = load_prompt("hunter_single.md").format(target=target, content=content)

            text = await run_agent(
                self.hunter,
                prompt,
                session_id=f"{self._scan_session_id}:hunt:{target}",
                session_service=self._session_service,
                artifact_service=self._artifact_service,
                summarizer=self._summarizer
            )
            try:
                data = parse_json_response(text)

                # Handle findings
                raw_findings = data.get("findings", [])
                if not isinstance(raw_findings, list):
                    raw_findings = [raw_findings]

                for raw in raw_findings:
                    finding = Finding(
                        title=raw.get("title", "Untitled"),
                        description=raw.get("description", "N/A"),
                        severity=raw.get("severity", "N/A"),
                        vulnerable_code=raw.get("vulnerable_code", "N/A"),
                        file_path=target,
                        impact=raw.get("impact", "N/A"),
                        exploitation_path=raw.get("exploitation_path", "N/A"),
                        remediation=raw.get("remediation", "N/A"),
                        cwe_id=raw.get("cwe_id"),
                    )
                    self._findings.append(finding)
                    new_findings.append(finding)
                    self._db.save_finding(self._project_path, finding)

                # Handle hypotheses
                new_hypotheses = data.get("hypotheses", [])
                for hypo in new_hypotheses:
                    hypo_task = Hypothesis(
                        type=TaskType.HUNT,
                        target=hypo.get("target", ""),
                        description=hypo.get("description", ""),
                        confidence=hypo.get("confidence", 0.5),
                        parent_id=f"hunt:{target}"
                    )
                    self._db.save_hypothesis(self._project_path, hypo_task)

            except Exception as e:
                self.log(f"[bold red]Error:[/bold red] Failed to parse Hunter output for {target}: {e}")

        return new_findings

    async def verify_finding(self, finding: Finding) -> dict[str, Any]:
        """Verify a finding using Skeptic and Validator agents."""
        self.log(f"[bold]Coordinator:[/bold] verifying [cyan]{finding.title}[/cyan]")

        # Phase 3.1: Skeptic
        skeptic_prompt = load_prompt("skeptic_verify.md").format(
            title=finding.title,
            description=finding.description,
            vulnerable_code=finding.vulnerable_code,
            file_path=finding.file_path,
            file_content=read_file_content(os.path.join(self._project_path, finding.file_path))
        )

        s_text = await run_agent(
            self.skeptic,
            skeptic_prompt,
            session_id=f"{self._scan_session_id}:verify:skeptic:{finding.title}",
            session_service=self._session_service,
            artifact_service=self._artifact_service,
            summarizer=self._summarizer
        )

        try:
            s_data = parse_json_response(s_text)
            is_valid = s_data.get("is_valid", True)
            finding.verification_status = "Verified" if is_valid else "False Positive"
            finding.remediation = s_data.get("remediation", finding.remediation)
        except Exception as e:
            self.log(f"[bold red]Error:[/bold red] Failed to parse Skeptic output: {e}")
            is_valid = True  # Conservative default

        if is_valid:
            # Phase 3.2: Validator
            validator_prompt = load_prompt("validator_verify.md").format(
                title=finding.title,
                file_path=finding.file_path,
                tech_stack=self._tech_stack
            )

            v_text = await run_agent(
                self.validator,
                validator_prompt,
                session_id=f"{self._scan_session_id}:verify:validator:{finding.title}",
                session_service=self._session_service,
                artifact_service=self._artifact_service,
                summarizer=self._summarizer
            )

            try:
                v_data = parse_json_response(v_text)
                status = v_data.get("status", "Unverified")
                finding.verification_status = status
                finding.poc = v_data.get("poc") or v_data.get("poc_code")
            except Exception as e:
                self.log(f"[bold red]Error:[/bold red] Failed to parse Validator output: {e}")

        self._db.save_finding(self._project_path, finding)
        self.log(f"Verification complete: [bold]{finding.verification_status}[/bold]")
        return {"status": finding.verification_status, "poc_code": finding.poc}

    def _agent_by_name(self, name: str) -> BaseAgent:
        """Finds a sub-agent by name."""
        if name == "coordinator":
            return self
        if name == "hunter_orchestrator":
            return self.hunter_loop.sub_agents[0]
        for sa in self.sub_agents:
            if sa.name == name:
                return sa
        # Special case for LoopAgent nested agents
        if name == "hunter":
            return self.hunter
        raise ValueError(f"Unknown agent name: {name}")
