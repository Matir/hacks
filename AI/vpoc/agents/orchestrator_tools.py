import logging
import typing
from core.models import FindingStatus, ReconResult, Finding
from core.storage import StorageManager
from core.budget import BudgetManager

logger = logging.getLogger(__name__)


def get_project_summary(storage: StorageManager, project_id: str) -> typing.Dict[str, typing.Any]:
    """
    Returns a high-level summary of the project's current state.
    Includes counts of findings by status and overall progress.
    """
    summary = {
        "project_id": project_id,
        "finding_counts": {},
        "total_findings": 0,
    }
    
    for status in FindingStatus:
        findings = storage.get_findings_by_status(status)
        count = len(findings)
        summary["finding_counts"][status.value] = count
        summary["total_findings"] += count
        
    return summary


def get_recon_results_summary(storage: StorageManager, project_id: str) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Returns a list of entry points and high-value targets identified during Recon.
    """
    results = storage.get_recon_results(project_id)
    return [
        {
            "file_path": r.file_path,
            "result_type": r.result_type,
            "description": r.description,
            "priority": r.priority,
        }
        for r in results
    ]


def get_findings_to_review(storage: StorageManager, project_id: str, limit: int = 10) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Returns a list of POTENTIAL findings that need LLM pre-screening or prioritization.
    """
    findings = storage.get_findings_by_status(FindingStatus.POTENTIAL)
    # Sort by line number or other metric for now; in future might use tool severity
    return [
        {
            "id": f.id,
            "vuln_type": f.vuln_type,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "severity": f.severity,
            "discovery_tool": f.discovery_tool,
            "evidence_snippet": f.evidence[:200] + "..." if len(f.evidence) > 200 else f.evidence,
        }
        for f in findings[:limit]
    ]


def promote_finding(
    storage: StorageManager,
    agent_manager: AgentManager,
    finding_id: int,
    status: str,
    rationale: str,
    priority_score: typing.Optional[float] = None
) -> str:
    """
    Promotes a finding to SCREENED or REJECTED status with an LLM-provided rationale.
    
    If promoted to SCREENED, the finding is automatically enqueued for PoC/Validation.
    
    :param finding_id: The ID of the finding to update.
    :param status: The new status (must be SCREENED or REJECTED).
    :param rationale: A brief explanation for the decision.
    :param priority_score: Optional score to override default prioritization.
    """
    try:
        new_status = FindingStatus(status.upper())
        if new_status not in (FindingStatus.SCREENED, FindingStatus.REJECTED):
            return f"Error: Status must be SCREENED or REJECTED, not {status}."
        
        # Update rationale and status
        with Session(storage.engine) as session:
            f = session.get(Finding, finding_id)
            if not f:
                return f"Error: Finding {finding_id} not found."
            
            f.status = new_status
            f.llm_rationale = rationale
            if priority_score is not None:
                f.priority_score = priority_score
            
            session.add(f)
            session.commit()
            session.refresh(f)
            
            # Auto-enqueue if SCREENED
            if new_status == FindingStatus.SCREENED:
                # We need to ensure agent_manager is available.
                # In this architecture, it should be passed from the agent.
                import asyncio
                # Use a background task if we don't want to block the tool call
                asyncio.create_task(agent_manager.enqueue_finding(f))
                return f"Successfully promoted finding {finding_id} to SCREENED and enqueued for validation."
                    
        return f"Successfully updated finding {finding_id} to {status}."
    except Exception as e:
        logger.exception("Failed to promote finding %d: %s", finding_id, e)
        return f"Error: {str(e)}"


def get_budget_status(budget_manager: BudgetManager, project_id: str) -> typing.Dict[str, typing.Any]:
    """
    Returns the current token usage vs the daily limit for the project.
    """
    config = budget_manager.global_storage.get_budget_limit(project_id)
    usage = budget_manager.global_storage.get_daily_token_usage(project_id)
    
    return {
        "project_id": project_id,
        "usage": usage,
        "limit": config.daily_limit if config else "No limit set",
        "remaining": (config.daily_limit - usage) if config else "Unlimited",
    }
