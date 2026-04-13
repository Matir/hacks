import datetime
import typing

from core.events import TOPIC_BUDGET_ALERT, Event, EventBus
from core.global_storage import GlobalStorageManager
from core.models import BudgetConfig


class BudgetExhaustedError(Exception):
    """Raised when the daily token budget for a project has been reached."""
    pass


class BudgetManager:
    """Enforces daily token caps across all projects.

    Loads usage totals from GlobalStorageManager and checks before
    each LLM invocation. Midnight UTC reset is implicit in
    get_daily_token_usage() logic.
    """

    def __init__(
        self,
        global_storage: GlobalStorageManager,
        event_bus: typing.Optional[EventBus] = None,
    ) -> None:
        self.global_storage = global_storage
        self.event_bus = event_bus

    async def check_budget(self, project_id: str, estimated_tokens: int = 0) -> bool:
        """
        Checks if the daily budget allows for another LLM call.

        :param project_id: The project being checked.
        :param estimated_tokens: Optional token count to check against.
        :return: True if budget is available.
        :raises BudgetExhaustedError: If the cap is already reached.
        """
        config: typing.Optional[BudgetConfig] = self.global_storage.get_budget_limit(project_id)
        if config is None:
            # If no limit set, assume unlimited or use a very high default?
            # Per AGENTS.md, daily_budget_limit in config.toml is the initial default.
            return True

        current_usage = self.global_storage.get_daily_token_usage(project_id)
        if current_usage + estimated_tokens >= config.daily_limit:
            if self.event_bus:
                await self.event_bus.publish(
                    Event(
                        topic=TOPIC_BUDGET_ALERT,
                        payload={
                            "project_id": project_id,
                            "usage": current_usage,
                            "limit": config.daily_limit,
                            "message": "Daily budget exhausted. All projects paused.",
                        },
                    )
                )
            raise BudgetExhaustedError(
                f"Project {project_id} has exhausted its daily budget of {config.daily_limit} tokens."
            )

        # Warning at 80%
        if (current_usage / config.daily_limit) >= 0.8:
            if self.event_bus:
                await self.event_bus.publish(
                    Event(
                        topic=TOPIC_BUDGET_ALERT,
                        payload={
                            "project_id": project_id,
                            "usage": current_usage,
                            "limit": config.daily_limit,
                            "message": "Daily budget approaching 80% limit.",
                        },
                    )
                )

        return True

    def record_usage(
        self,
        project_id: str,
        agent_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        """
        Persists token usage to the global database.
        
        :param project_id: The project that used the tokens.
        :param agent_name: The agent that made the call.
        :param model: The LiteLlm model string.
        :param tokens_in: Prompt tokens.
        :param tokens_out: Completion tokens.
        """
        self.global_storage.track_token_usage(
            project_id=project_id,
            agent_name=agent_name,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
