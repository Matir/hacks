from typing import Any

from google.adk.agents import LlmAgent
from pydantic import ConfigDict

from trashdig.agents.utils.helpers import google_provider_extras, load_prompt
from trashdig.config import AgentConfig


class SummarizerAgent(LlmAgent):
    """Specialized agent for summarizing agent conversation history."""

    model_config = ConfigDict(extra="allow")


def create_summarizer_agent(config: AgentConfig | None = None, **kwargs: Any) -> SummarizerAgent:
    """Creates a Summarizer agent.

    Args:
        config: Optional agent configuration.
        **kwargs: Additional arguments for the LlmAgent constructor.

    Returns:
        A configured SummarizerAgent instance.
    """
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("summarizer.md")
    kwargs.update(google_provider_extras(config.provider))

    return SummarizerAgent(
        name="summarizer",
        model=config.model,
        instruction=instruction,
        description="Summarizes long conversation histories to save context.",
        **kwargs,
    )
