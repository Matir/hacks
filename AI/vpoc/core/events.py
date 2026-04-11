import asyncio
import time
import typing
import uuid
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Topic constants
# ---------------------------------------------------------------------------

TOPIC_HINT: str = "orchestrator.hint"
TOPIC_COMMAND: str = "orchestrator.command"
TOPIC_FINDING_UPDATED: str = "finding.updated"
TOPIC_AGENT_STATUS: str = "agent.status"
TOPIC_LOG_LINE: str = "log.line"
TOPIC_BUDGET_ALERT: str = "budget.alert"


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------

class Event(BaseModel):
    """Base schema for all events published on the EventBus."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    payload: typing.Dict[str, typing.Any]
    timestamp: float = Field(default_factory=time.time)


class HintEvent(Event):
    """Published when a user submits a free-form hint via TUI or web.

    Payload schema: ``{"project_id": str, "text": str}``
    """

    topic: str = Field(default=TOPIC_HINT)

    @classmethod
    def create(cls, project_id: str, text: str) -> "HintEvent":
        """Creates a HintEvent with the standard payload schema.

        :param project_id: The project the hint applies to.
        :param text: Free-form hint text from the user.
        """
        return cls(
            topic=TOPIC_HINT,
            payload={"project_id": project_id, "text": text},
        )


class CommandEvent(Event):
    """Published when a user triggers a quick-action button via TUI or web.

    Payload schema: ``{"project_id": str, "command": str, "args": dict}``

    Valid commands: ``PAUSE``, ``RESUME``, ``SKIP_FINDING``,
    ``PRIORITIZE_RCE``, ``MARK_FALSE_POSITIVE``.
    """

    topic: str = Field(default=TOPIC_COMMAND)

    @classmethod
    def create(
        cls,
        project_id: str,
        command: str,
        args: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> "CommandEvent":
        """Creates a CommandEvent with the standard payload schema.

        :param project_id: The project the command targets.
        :param command: The command name (e.g. ``PAUSE``).
        :param args: Optional command-specific arguments.
        """
        return cls(
            topic=TOPIC_COMMAND,
            payload={"project_id": project_id, "command": command, "args": args or {}},
        )


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

class EventBus:
    """An asynchronous, in-process event bus with fan-out support.

    Each subscriber receives its own ``asyncio.Queue`` so slow consumers
    do not block fast ones.  The bus is intended exclusively for UI fanout
    (TUI, Web); agents communicate through ADK runner/session machinery.
    """

    def __init__(self) -> None:
        self._subscribers: typing.Dict[str, asyncio.Queue[Event]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def subscribe(self) -> str:
        """Creates a new subscription and returns a unique subscription ID."""
        sub_id: str = str(uuid.uuid4())
        queue: asyncio.Queue[Event] = asyncio.Queue()
        async with self._lock:
            self._subscribers[sub_id] = queue
        return sub_id

    async def unsubscribe(self, sub_id: str) -> None:
        """Removes a subscription by ID."""
        async with self._lock:
            if sub_id in self._subscribers:
                del self._subscribers[sub_id]

    async def publish(self, event: Event) -> None:
        """Publishes an event to all current subscribers."""
        async with self._lock:
            for queue in self._subscribers.values():
                queue.put_nowait(event)

    async def get_event(self, sub_id: str) -> Event:
        """Retrieves the next event for a subscription, blocking until one arrives.

        :raises ValueError: If the subscription ID does not exist.
        """
        queue: typing.Optional[asyncio.Queue[Event]] = self._subscribers.get(sub_id)
        if queue is None:
            raise ValueError(f"Subscription {sub_id} not found.")
        return await queue.get()

    def publish_threadsafe(
        self, event: Event, loop: asyncio.AbstractEventLoop
    ) -> None:
        """Publishes an event from a non-async thread.

        Schedules ``publish`` as a coroutine on the given event loop so that
        the asyncio lock is held correctly and subscriber dict access is
        confined to the event loop thread.
        """
        asyncio.run_coroutine_threadsafe(self.publish(event), loop)
