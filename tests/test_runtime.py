"""Exercise real polling/event routing with synthetic bridge data."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.core import Event

from custom_components.hue_fluid_dimmer.api import BridgeError
from custom_components.hue_fluid_dimmer.const import CONF_MODE, EVENT_ROTATION
from custom_components.hue_fluid_dimmer.runtime import Runtime


def make_runtime(monkeypatch, options):
    monkeypatch.setattr(
        "custom_components.hue_fluid_dimmer.runtime.aiohttp_client.async_get_clientsession",
        lambda *a, **kw: None,
    )
    fired = []
    hass = SimpleNamespace(
        bus=SimpleNamespace(async_fire=lambda name, data: fired.append((name, data)))
    )
    entry = SimpleNamespace(
        options=options,
        data={},
        subentries={
            rid: SimpleNamespace(subentry_type="tap_dial", unique_id=rid, data=binding)
            for rid, binding in options.get("controllers", {}).items()
        },
        async_create_background_task=lambda h, coro, name, **kw: asyncio.create_task(coro),
    )
    runtime = Runtime(hass, entry)
    runtime.device = lambda owner: SimpleNamespace(id=owner, name_by_user=None, name=owner)
    return runtime, fired


async def test_active_polling_sleeps_and_native_events_only_wake(monkeypatch, resource):
    runtime, fired = make_runtime(monkeypatch, {"poll_interval": 0.01, "active_window": 0.04})
    runtime.resources = [resource()]
    runtime.tracker.baseline(runtime.resources)
    calls = []

    async def fetch():
        calls.append(1)
        return [resource(1)]

    runtime.client.rotary_resources = fetch
    runtime.task = asyncio.create_task(runtime.poll())
    await asyncio.sleep(0.02)
    assert not calls
    runtime.on_hue_event(Event("hue_event", {"unique_id": "dial-a", "steps": 9999}))
    await asyncio.sleep(0.09)
    count = len(calls)
    await asyncio.sleep(0.04)
    assert len(calls) == count
    assert len(fired) == 1 and fired[0][0] == EVENT_ROTATION
    assert fired[0][1]["steps"] == 15  # REST, not delayed native steps.
    await runtime.close()
    assert runtime.task.done()


async def test_hundred_resources_use_one_batch_request(monkeypatch, resource):
    runtime, fired = make_runtime(monkeypatch, {CONF_MODE: "continuous", "poll_interval": 0.02})
    baseline = [resource(resource_id=f"dial-{i}") for i in range(100)]
    runtime.resources = baseline
    runtime.tracker.baseline(baseline)
    fetch = Mock(side_effect=lambda: None)

    async def batch():
        fetch()
        return [resource(1, resource_id=f"dial-{i}") for i in range(100)]

    runtime.client.rotary_resources = batch
    runtime.task = asyncio.create_task(runtime.poll())
    await asyncio.sleep(0.03)
    await runtime.close()
    assert fetch.call_count == 2
    assert len(fired) == 100


async def test_failed_read_backs_off_and_recovery_baselines(monkeypatch, resource):
    runtime, fired = make_runtime(monkeypatch, {CONF_MODE: "continuous", "poll_interval": 0.01})
    runtime.tracker.baseline([resource()])
    failed = asyncio.Event()
    calls = []

    async def fetch():
        calls.append(1)
        failed.set()
        raise BridgeError("test outage")

    runtime.client.rotary_resources = fetch
    runtime.task = asyncio.create_task(runtime.poll())
    await failed.wait()
    await asyncio.sleep(0.03)
    assert len(calls) == 1 and runtime.error_count == 1
    assert not runtime.available and not fired
    await runtime.close()


async def test_button_bus_does_not_duplicate_sse_actions(monkeypatch, resource):
    binding = {"enabled": True, "lights": ["light.test"], "button_1": "scene.test"}
    runtime, _ = make_runtime(monkeypatch, {"controllers": {"dial-a": binding}})
    runtime.resources = [resource()]
    calls = []

    async def button(*args):
        calls.append(args)

    runtime.button = button
    for device, event_type in [
        ("other", "short_release"),
        ("owner-a", "initial_press"),
        ("owner-a", "short_release"),
    ]:
        runtime.on_hue_event(
            Event(
                "hue_event",
                {"unique_id": "button-a", "device_id": device, "type": event_type, "subtype": 1},
            )
        )
    await asyncio.sleep(0)
    assert len(calls) == 0
    await runtime.close()


async def test_light_list_button_sends_one_service_call(monkeypatch):
    runtime, _ = make_runtime(monkeypatch, {})
    call = AsyncMock()
    runtime.hass.services = SimpleNamespace(async_call=call)
    binding = {"lights": ["light.group"], "button_1": ["light.group", "light.single"]}
    await runtime.button("dial-a", binding, 1)
    call.assert_awaited_once_with(
        "light", "toggle", {"entity_id": ["light.group", "light.single"]}, blocking=True
    )
    await runtime.close()


async def test_timestamped_sse_routes_matching_buttons_only(monkeypatch, resource):
    binding = {"enabled": True, "button_2": {"short": ["light.group"]}}
    runtime, _ = make_runtime(monkeypatch, {"controllers": {"dial-a": binding}})
    runtime.resources = [resource()]
    runtime.button_map = {"button-a": ("dial-a", 2)}
    calls = []

    async def button(*args):
        calls.append(args)

    runtime.button = button
    runtime.consume_buttons(
        [
            {
                "type": "update",
                "data": [
                    {
                        "id": "other",
                        "type": "button",
                        "button": {
                            "button_report": {
                                "event": "initial_press",
                                "updated": "2026-10-13T21:50:35.454Z",
                            }
                        },
                    },
                    {
                        "id": "button-a",
                        "type": "button",
                        "button": {
                            "button_report": {
                                "event": "initial_press",
                                "updated": "2026-10-13T21:50:35.454Z",
                            }
                        },
                    },
                    {
                        "id": "button-a",
                        "type": "button",
                        "button": {
                            "button_report": {
                                "event": "short_release",
                                "updated": "2026-10-13T21:50:35.532Z",
                            }
                        },
                    },
                ],
            }
        ]
    )
    await asyncio.sleep(0)
    assert len(calls) == 1 and calls[0][2:] == (2, "short")
    await runtime.close()


async def test_sse_reconnect_cancels_gesture_and_backoffs(monkeypatch, resource):
    binding = {"enabled": True, "button_2": {"short": ["light.a"], "double": ["light.b"]}}
    runtime, _ = make_runtime(monkeypatch, {"controllers": {"dial-a": binding}})
    runtime.resources = [resource()]
    runtime.client.button_resources = AsyncMock(
        return_value=[
            {
                "id": "button-a",
                "owner": {"rid": "owner-a"},
                "metadata": {"control_id": 2},
                "button": {
                    "button_report": {
                        "event": "short_release",
                        "updated": "2026-10-13T21:50:35.532Z",
                    }
                },
            }
        ]
    )
    runtime.gestures.feed("dial-a", 2, "initial_press", 1)
    runtime.gestures.feed("dial-a", 2, "short_release", 1.08)

    async def broken_stream():
        if False:
            yield []
        raise BridgeError("test disconnect", retry_after=60)

    runtime.client.button_events = broken_stream
    sleeps = []

    async def sleep(delay):
        sleeps.append(delay)
        runtime.closed = True

    monkeypatch.setattr("custom_components.hue_fluid_dimmer.runtime.asyncio.sleep", sleep)
    await runtime.listen_buttons()
    assert sleeps == [60] and not runtime.gestures.pending
    assert runtime.button_map == {"button-a": ("dial-a", 2)}
    assert runtime.button_baselined
    assert runtime.button_snapshots[("dial-a", 2)][1] == "short_release"
    await runtime.close()
