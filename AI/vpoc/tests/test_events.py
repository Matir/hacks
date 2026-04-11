import asyncio
import threading
import pytest
from core.events import (
    CommandEvent,
    Event,
    EventBus,
    HintEvent,
    TOPIC_HINT,
    TOPIC_COMMAND,
    TOPIC_FINDING_UPDATED,
    TOPIC_AGENT_STATUS,
    TOPIC_LOG_LINE,
    TOPIC_BUDGET_ALERT,
)


@pytest.mark.anyio
async def test_event_bus_fan_out():
    bus = EventBus()
    sub1 = await bus.subscribe()
    sub2 = await bus.subscribe()

    test_event = Event(topic="test.topic", payload={"key": "value"})
    await bus.publish(test_event)

    res1 = await bus.get_event(sub1)
    res2 = await bus.get_event(sub2)

    assert res1.event_id == test_event.event_id
    assert res1.payload["key"] == "value"
    assert res2.event_id == test_event.event_id


@pytest.mark.anyio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    sub1 = await bus.subscribe()

    await bus.unsubscribe(sub1)

    with pytest.raises(ValueError):
        await bus.get_event(sub1)


@pytest.mark.anyio
async def test_event_bus_concurrent_subscribers():
    bus = EventBus()
    subscribers = [await bus.subscribe() for _ in range(10)]

    test_event = Event(topic="test.topic", payload={"data": 123})
    await bus.publish(test_event)

    for sub_id in subscribers:
        res = await bus.get_event(sub_id)
        assert res.payload["data"] == 123


@pytest.mark.anyio
async def test_event_bus_different_topics():
    bus = EventBus()
    sub1 = await bus.subscribe()

    e1 = Event(topic="topic.a", payload={"a": 1})
    e2 = Event(topic="topic.b", payload={"b": 2})

    await bus.publish(e1)
    await bus.publish(e2)

    res1 = await bus.get_event(sub1)
    res2 = await bus.get_event(sub1)

    assert res1.topic == "topic.a"
    assert res2.topic == "topic.b"


@pytest.mark.anyio
async def test_publish_threadsafe_delivers_event():
    """Verifies that publish_threadsafe correctly delivers events from a background thread."""
    bus = EventBus()
    sub = await bus.subscribe()
    loop = asyncio.get_event_loop()

    event = Event(topic=TOPIC_LOG_LINE, payload={"msg": "hello from thread"})

    def _publish_from_thread() -> None:
        bus.publish_threadsafe(event, loop)

    thread = threading.Thread(target=_publish_from_thread)
    thread.start()
    thread.join()

    # Give the event loop a tick to process the scheduled coroutine.
    await asyncio.sleep(0)

    received = await bus.get_event(sub)
    assert received.event_id == event.event_id
    assert received.payload["msg"] == "hello from thread"


def test_topic_constants_defined():
    """Verifies all expected topic constants are present and non-empty strings."""
    for constant in [
        TOPIC_HINT,
        TOPIC_COMMAND,
        TOPIC_FINDING_UPDATED,
        TOPIC_AGENT_STATUS,
        TOPIC_LOG_LINE,
        TOPIC_BUDGET_ALERT,
    ]:
        assert isinstance(constant, str)
        assert len(constant) > 0


def test_hint_event_create():
    """Verifies HintEvent.create produces a correctly structured event."""
    event = HintEvent.create(project_id="proj-1", text="focus on auth")
    assert event.topic == TOPIC_HINT
    assert event.payload["project_id"] == "proj-1"
    assert event.payload["text"] == "focus on auth"
    assert event.event_id  # non-empty


def test_command_event_create():
    """Verifies CommandEvent.create produces a correctly structured event."""
    event = CommandEvent.create(
        project_id="proj-1", command="SKIP_FINDING", args={"finding_id": 42}
    )
    assert event.topic == TOPIC_COMMAND
    assert event.payload["command"] == "SKIP_FINDING"
    assert event.payload["args"]["finding_id"] == 42


def test_command_event_create_default_args():
    """Verifies CommandEvent.create defaults args to an empty dict."""
    event = CommandEvent.create(project_id="proj-1", command="PAUSE")
    assert event.payload["args"] == {}
