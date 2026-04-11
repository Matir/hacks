import typing
from pydantic import Field

if typing.TYPE_CHECKING:
    from core.storage import StorageManager
    from core.events import EventBus


class VPOCMixin:
    """Mixin providing VPOC-specific state for ADK agent subclasses.

    Apply alongside the appropriate ADK agent base class, e.g.::

        class OrchestratorAgent(VPOCMixin, LlmAgent): ...
        class SourceReviewAgent(VPOCMixin, BaseAgent): ...

    Pydantic (used by ADK agents) collects field annotations from the full
    MRO, so these fields are available on all concrete agent classes.
    """

    project_id: typing.Optional[str] = Field(
        default=None, description="The current project ID."
    )
    storage_manager: typing.Optional["StorageManager"] = Field(
        default=None, description="Per-project storage manager."
    )
    event_bus: typing.Optional["EventBus"] = Field(
        default=None, description="In-process event bus for UI fanout."
    )
