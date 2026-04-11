import asyncio
import pytest
from core.events import EventBus, Event


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
