import asyncio
import uuid
import typing
from pydantic import BaseModel, Field


class Event(BaseModel):
    """Base schema for all events in the system."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    payload: typing.Dict[str, typing.Any]
    timestamp: float = Field(
        default_factory=typing.cast(typing.Callable[[], float], lambda: 0.0)
    )  # Placeholder for actual time

    def __init__(self, **data: typing.Any):
        import time

        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = time.time()


class EventBus:
    """An asynchronous, in-process event bus with fan-out support."""

    def __init__(self) -> None:
        self._subscribers: typing.Dict[str, asyncio.Queue[Event]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def subscribe(self) -> str:
        """
        Creates a new subscription and returns a unique subscription ID.
        The subscriber receives their own Queue.
        """
        sub_id: str = str(uuid.uuid4())
        queue: asyncio.Queue[Event] = asyncio.Queue()
        async with self._lock:
            self._subscribers[sub_id] = queue
        return sub_id

    async def unsubscribe(self, sub_id: str) -> None:
        """Removes a subscription."""
        async with self._lock:
            if sub_id in self._subscribers:
                del self._subscribers[sub_id]

    async def publish(self, event: Event) -> None:
        """Publishes an event to all current subscribers."""
        async with self._lock:
            # We iterate over items and put into queues.
            # If a queue is full (not possible here with default maxsize=0),
            # it could block. Using put_nowait for safety in broadcast.
            for sub_id, queue in self._subscribers.items():
                queue.put_nowait(event)

    async def get_event(self, sub_id: str) -> Event:
        """Retrieves the next event for a specific subscription."""
        # Note: This will block if the queue is empty.
        queue: typing.Optional[asyncio.Queue[Event]] = self._subscribers.get(sub_id)
        if queue is None:
            raise ValueError(f"Subscription {sub_id} not found.")
        return await queue.get()

    def publish_threadsafe(self, event: Event, loop: asyncio.AbstractEventLoop) -> None:
        """Publishes an event from a non-async thread."""
        def _publish() -> None:
            for queue in self._subscribers.values():
                queue.put_nowait(event)

        loop.call_soon_threadsafe(_publish)
