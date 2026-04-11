import typing
from google.adk import Agent
from pydantic import Field


class VPOCAgent(Agent):
    """Base class for all VPOC agents, extending ADK Agent with VPOC-specific state."""

    # Add any project-wide state here if needed
    project_id: typing.Optional[str] = Field(
        default=None, description="The current project ID"
    )

    # TODO: Add shared budget/token tracking integration here
