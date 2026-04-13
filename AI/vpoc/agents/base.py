import typing
import logging
import litellm
from pydantic import Field

from core.models import ProjectConfig
from core.storage import StorageManager
from core.events import EventBus
from core.budget import BudgetManager

logger = logging.getLogger(__name__)


class VPOCMixin:
    """Mixin providing VPOC-specific state for ADK agent subclasses."""

    project_id: typing.Optional[str] = Field(
        default=None, description="The current project ID."
    )
    project_config: typing.Optional["ProjectConfig"] = Field(
        default=None, description="Per-project configuration."
    )
    storage_manager: typing.Optional["StorageManager"] = Field(
        default=None, description="Per-project storage manager."
    )
    event_bus: typing.Optional["EventBus"] = Field(
        default=None, description="In-process event bus for UI fanout."
    )
    budget_manager: typing.Optional["BudgetManager"] = Field(
        default=None, description="Global budget manager for token enforcement."
    )
    model_name: str = Field(
        default="gemini/gemini-1.5-flash", description="LiteLlm model string."
    )

    async def call_llm(self, prompt: str, system_instruction: typing.Optional[str] = None) -> str:
        """
        Executes an LLM call via LiteLlm with budget enforcement.
        
        :param prompt: User prompt text.
        :param system_instruction: Optional system instruction.
        :return: Completion text.
        """
        if not self.budget_manager or not self.project_id:
            logger.warning("BudgetManager or project_id missing, skipping budget check.")
        else:
            # Simple estimation: 1 token per 4 chars
            estimated_tokens = (len(prompt) + len(system_instruction or "")) // 4
            await self.budget_manager.check_budget(self.project_id, estimated_tokens)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await litellm.acompletion(
                model=self.model_name,
                messages=messages,
            )
            
            content = response.choices[0].message.content
            
            # Record usage
            if self.budget_manager and self.project_id:
                usage = response.usage
                self.budget_manager.record_usage(
                    project_id=self.project_id,
                    agent_name=getattr(self, "name", "unknown"),
                    model=self.model_name,
                    tokens_in=usage.prompt_tokens,
                    tokens_out=usage.completion_tokens,
                )
                
            return content
        except Exception as e:
            logger.exception("LiteLlm call failed: %s", e)
            raise
