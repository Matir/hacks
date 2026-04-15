import os
import functools
from typing import Any, Dict, List, Optional, Callable

from pydantic import PrivateAttr
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.tools import FunctionTool
from google.adk.artifacts import BaseArtifactService

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
from trashdig.tools import get_next_hypothesis, update_hypothesis_status, exit_loop, save_findings, save_hypotheses


_COORDINATOR_INSTRUCTION = """
You are TrashDig's Coordinator — an AI orchestrator for a multi-phase vulnerability scanner.

## Sub-agents

- **stack_scout**: Identifies the technology stack, maps high-value source files, and generates initial security hypotheses.
- **web_route_mapper**: Maps all HTTP routes and endpoint handlers. Invoke only when stack_scout reports this is a web application.
- **hunter_loop**: An autonomous loop that processes all pending security hypotheses using the hunter agent.
- **skeptic**: Adversarial reviewer that attempts to debunk findings by identifying false positives.
- **validator**: Generates and executes PoC scripts in a sandbox container to confirm exploitability.

## Workflow

1. RECON — Run stack_scout on the project root. If is_web_app, also run web_route_mapper.
2. HUNT — Run hunter_loop. This will automatically process all high-value files and discovered hypotheses.
3. VERIFY — For each finding: run skeptic first. Only if skeptic confirms validity, run validator.

When asked to coordinate a full scan, follow this pipeline in order.
"""

_HUNTER_ORCHESTRATOR_INSTRUCTION = """
You are the Hunter Orchestrator. Your job is to process ONE pending security hypothesis from the database.

1. Call `get_next_hypothesis` to find the next target.
2. If it returns "None", call `exit_loop` to finish the hunting phase.
3. If you get a hypothesis:
   - Extract the 'target' (file path).
   - Use the `hunter` agent to perform a deep-dive analysis of that target.
   - The hunter will return a JSON response with 'findings' and 'hypotheses'.
   - Call `save_findings` with the 'findings' list.
   - Call `save_hypotheses` with the 'hypotheses' list.
   - Once done, call `update_hypothesis_status` with 'completed'.
"""


class Coordinator(LlmAgent):
    """Coordinates the hypothesis-driven vulnerability scanning workflow."""

    # ------------------------------------------------------------------
    # Settable TUI callbacks
    # ------------------------------------------------------------------
    on_task_event: Optional[Any] = None
    on_stats_event: Optional[Any] = None

    # ------------------------------------------------------------------
    # All mutable state
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
        artifact_service: Optional[BaseArtifactService] = None,
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

        db_path = getattr(config, "db_path", ".trashdig/trashdig.db")
        
        # Create the HunterOrchestrator and wrap it in a LoopAgent
        hunter_orchestrator = LlmAgent(
            name="hunter_orchestrator",
            model=config.get_agent_config("hunter").model,
            instruction=_HUNTER_ORCHESTRATOR_INSTRUCTION,
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
            instruction=_COORDINATOR_INSTRUCTION,
            description="Orchestrates the multi-phase vulnerability scanning pipeline.",
            sub_agents=[stack_scout, web_route_mapper, hunter_loop, skeptic, validator],
        )

        # --- PrivateAttr initialisation ---
        db = ProjectDatabase(db_path)
        scan_session_id = db.get_or_create_scan_session(project_path if project_path else ".")
        session_service = SqliteSessionService(db_path=db_path)
        
        cost_tracker = CostTracker()
        engine = Engine(
            session_service=session_service,
            artifact_service=artifact_service,
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
        for _agent in (*self.sub_agents, self, hunter_orchestrator):
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
        return []

    @property
    def completed_tasks(self) -> list:
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
    def hunter_loop(self):
        return self._agent_by_name("hunter_loop")

    @property
    def hunter(self):
        # The actual hunter is now nested inside hunter_loop -> hunter_orchestrator
        orchestrator = next((a for a in self.hunter_loop.sub_agents if a.name == "hunter_orchestrator"), None)
        if orchestrator:
            return next((a for a in orchestrator.sub_agents if a.name == "hunter"), None)
        return None

    @property
    def skeptic(self):
        return self._agent_by_name("skeptic")

    @property
    def validator(self):
        return self._agent_by_name("validator")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_stats(
        self,
        input_tokens: int,
        output_tokens: int,
        new_msg: bool = False,
        model_name: Optional[str] = None,
    ) -> None:
        if self.on_stats_event:
            self.on_stats_event()

    def _agent_by_name(self, name: str) -> Any:
        return next((a for a in self.sub_agents if a.name == name), None)

    def _on_llm_error(self) -> None:
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
        self._db.log_conversation(
            self._project_path, agent_name, prompt, response,
            tool_calls, input_tokens, output_tokens,
        )

    def log(self, message: str) -> None:
        if self.on_task_event:
            self.on_task_event(message)

    # ------------------------------------------------------------------
    # Full automated pipeline
    # ------------------------------------------------------------------

    async def run_full_scan(self, path: str = ".") -> None:
        """Run the full SCAN → HUNT → VERIFY pipeline with hypothesis loop."""
        # Phase 1: Recon
        await self.run_recon(path)

        # Phase 2: Hypothesis-driven hunting loop using ADK LoopAgent
        self.log("[bold]Coordinator:[/bold] starting autonomous hunting loop...")
        async for _ in self.hunter_loop.run_async(self._engine.ctx):
            pass

        # Reload findings from DB as the loop agent populated it
        db_findings = self._db.get_findings(self._project_path)
        self._findings = []
        for f in db_findings:
            # Filter out internal DB keys (id, project_path)
            filtered = {k: v for k, v in f.items() if k in Finding.__dataclass_fields__}
            self._findings.append(Finding(**filtered))

        # Phase 3: Verify all accumulated findings
        for finding in list(self._findings):
            await self.verify_finding(finding)

    async def _hunt_batch(
        self, targets: List[str], path: str = "."
    ) -> tuple:
        """Kept for backward compatibility, but run_full_scan now uses hunter_loop."""
        new_findings: List[Finding] = []
        all_hypotheses: List[Dict[str, Any]] = []

        for target in targets:
            self.log(f"[bold]Coordinator:[/bold] hunting [cyan]{target}[/cyan]")
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
            all_hypotheses.extend(results.get("hypotheses", []))

        return new_findings, all_hypotheses

    # ------------------------------------------------------------------
    # TUI-facing methods
    # ------------------------------------------------------------------

    async def run_recon(self, path: str = ".") -> Dict[str, Any]:
        """Performs initial stack discovery and project mapping."""
        import json
        self.log(f"[bold]Coordinator:[/bold] starting reconnaissance on [cyan]{path}[/cyan]")
        
        # 1. Run StackScout
        prompt = (
            f"Analyze the project at {os.path.abspath(path)}.\n"
            "Identify the full tech stack, determine if it is a web application, "
            "map high-value files, and generate security hypotheses."
        )
        
        result = await self._engine.run(self.stack_scout, prompt)
        try:
            cleaned = result.text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:].rstrip("`").strip()
            data = json.loads(cleaned)
        except Exception as e:
            self.log(f"[bold red]Error:[/bold red] Failed to parse StackScout output: {e}")
            data = {}

        mapping: Dict[str, Any] = data.get("mapping", {})
        hypotheses: List[Dict[str, Any]] = data.get("hypotheses", [])
        self._tech_stack = data.get("tech_stack", "")
        self._scan_results = mapping

        is_web_app = data.get("is_web_app", False)

        if is_web_app:
            self.log("[bold]Coordinator:[/bold] web application detected, mapping attack surface…")
            route_prompt = "Identify all web routes, methods, handlers, and parameters in the project."
            route_result = await self._engine.run(self.web_route_mapper, route_prompt)
            try:
                r_cleaned = route_result.text.strip()
                if r_cleaned.startswith("```json"):
                    r_cleaned = r_cleaned[7:].rstrip("`").strip()
                route_data = json.loads(r_cleaned)
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

    async def run_hunter(self, targets: List[str], path: str = ".") -> List[Finding]:
        import json
        from trashdig.agents.utils import read_file_content
        new_findings: List[Finding] = []
        for i, target in enumerate(targets, 1):
            self.log(f"[bold]Hunter:[/bold] analysing [cyan]{target}[/cyan] ([dim]{i}/{len(targets)}[/dim])")
            content = read_file_content(os.path.join(path, target))

            prompt = (
                f"Analyze the following file for potential security vulnerabilities:\n\n"
                f"File: {target}\n"
                f"Content:\n{content}\n\n"
                f"Identify and document each finding or follow-up hypothesis in a JSON response with two keys:\n"
                f"1. 'findings': A list of vulnerability objects:\n"
                f"   - title, description, severity, vulnerable_code, impact, exploitation_path, remediation, cwe_id\n"
                f"2. 'hypotheses': A list of follow-up tasks if you need to trace data flow into other files:\n"
                f"   - target: (The file path or symbol to investigate next)\n"
                f"   - description: (Why you need to look there)\n"
                f"   - confidence: (0.0 to 1.0)\n"
            )

            result = await self._engine.run(self.hunter, prompt)
            try:
                cleaned = result.text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:].rstrip("`").strip()
                data = json.loads(cleaned)
                
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
                    finding.save(os.path.join(path, "findings"))
                    self._findings.append(finding)
                    new_findings.append(finding)
                    self._db.save_finding(self._project_path, finding)
                    
                    sev_color = {"critical": "red", "high": "red", "medium": "yellow", "low": "green"}.get((finding.severity or "").lower(), "white")
                    self.log(f"  [bold {sev_color}]■[/bold {sev_color}] [bold]{finding.title}[/bold] — {finding.description[:80]}…")

                # Handle hypotheses
                for h in data.get("hypotheses", []):
                    hypo_task = Hypothesis(
                        type=TaskType.HUNT,
                        target=h.get("target", ""),
                        description=h.get("description", ""),
                        confidence=h.get("confidence", 0.5),
                    )
                    self._db.save_hypothesis(self._project_path, hypo_task)
                    self.log(f"  [dim]Hypothesis: {hypo_task.target}[/dim]")

            except Exception as e:
                self.log(f"[bold red]Error:[/bold red] Failed to parse Hunter output for {target}: {e}")

        self.log(f"Finished: [bold green]HUNT[/bold green] — {len(new_findings)} findings found")
        return new_findings

    async def verify_finding(self, finding: Finding) -> Dict[str, Any]:
        import json
        from trashdig.agents.utils import read_file_content
        
        # 1. Run Skeptic
        self.log(f"[bold]Skeptic:[/bold] reviewing [bold yellow]{finding.title}[/bold yellow]")
        file_content = read_file_content(finding.file_path)
        
        skeptic_prompt = (
            f"Please review this potential finding and try to debunk it:\n\n"
            f"Title: {finding.title}\n"
            f"Description: {finding.description}\n"
            f"Vulnerable Code:\n{finding.vulnerable_code}\n\n"
            f"File Path: {finding.file_path}\n"
            f"File Content:\n{file_content}\n\n"
            f"Your Goal:\n"
            f"Find any reason why this is a False Positive. Check reachability, "
            f"framework protections, or logical errors in the original report."
        )
        
        skeptic_result = await self._engine.run(self.skeptic, skeptic_prompt)
        try:
            s_text = skeptic_result.text.strip()
            if s_text.startswith("```json"):
                s_text = s_text[7:].rstrip("`").strip()
            s_data = json.loads(s_text)
            is_valid = s_data.get("is_valid", True)
        except Exception as e:
            self.log(f"[dim]Skeptic parsing failed: {e}. Defaulting to valid.[/dim]")
            is_valid = True

        if not is_valid:
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
        self.log(f"[bold]Validator:[/bold] verifying [bold yellow]{finding.title}[/bold yellow]")
        validator_prompt = (
            f"Please verify this potential finding by generating and executing a Proof-of-Concept (PoC):\n\n"
            f"Title: {finding.title}\n"
            f"Description: {finding.description}\n"
            f"Vulnerable Code:\n{finding.vulnerable_code}\n\n"
            f"Project Tech Stack: {self._tech_stack}\n"
            f"File Path: {finding.file_path}\n"
            f"File Content:\n{file_content}\n\n"
            f"Instructions:\n"
            f"1. Generate a PoC (Python script, custom command, etc.) that demonstrates the vulnerability.\n"
            f"2. Execute the PoC using `container_bash_tool` to see if it successfully exploits the vulnerability in a sandbox.\n"
            f"3. Analyze the tool output.\n"
            f"4. Provide a JSON response with: 'status' (Verified/False Positive), "
            f"'poc_code' (the script/command used), and 'reasoning' (results of the PoC execution)."
        )
        
        val_result = await self._engine.run(self.validator, validator_prompt)
        try:
            v_text = val_result.text.strip()
            if v_text.startswith("```json"):
                v_text = v_text[7:].rstrip("`").strip()
            v_data = json.loads(v_text)
            status = v_data.get("status", "Unverified")
            poc_code = v_data.get("poc_code", "")
        except Exception as e:
            self.log(f"[dim]Validator parsing failed: {e}.[/dim]")
            status = "Unverified"
            poc_code = ""

        finding.verification_status = status
        finding.poc = poc_code
        finding.save(os.path.join(self._project_path, "findings"))
        self._db.update_finding_status(
            self._project_path,
            finding.title,
            finding.file_path,
            finding.verification_status,
            finding.poc,
        )

        status_color = "green" if status == "Verified" else "red" if status == "False Positive" else "yellow"
        self.log(f"Finished: [bold green]VERIFY[/bold green] ([dim]{finding.title}[/dim]) — [{status_color}]{status}[/{status_color}]")
        return {"status": status, "poc_code": poc_code}
