import asyncio

import pytest

from custom_components.hue_fluid_dimmer.control import Dimmer

BINDING = {"enabled": True, "lights": ["light.test"], "sensitivity": 1.5, "transition": 1}


async def wait_worker(dimmer):
    tasks = [target.task for target in dimmer.targets.values() if target.task]
    await asyncio.gather(*tasks)


async def test_rapid_rotation_coalesces_without_rounding_drift():
    sent = []
    dimmer = Dimmer(
        lambda _: 10, lambda lights, value, ramp: record(sent, value, ramp), command_interval=0
    )
    for _ in range(22):
        dimmer.rotate({**BINDING, "sensitivity": 1}, 15)
    await wait_worker(dimmer)
    assert sent == [(32.0, 1)]


async def record(sent, value, ramp):
    sent.append((value, ramp))


async def test_slow_light_response_preserves_new_steps_and_reverse_direction():
    sent = []
    started, release = asyncio.Event(), asyncio.Event()

    async def send(lights, value, ramp):
        sent.append(value)
        if len(sent) == 1:
            started.set()
            await release.wait()

    dimmer = Dimmer(lambda _: 20, send, command_interval=0)
    dimmer.rotate(BINDING, 150)
    await started.wait()
    dimmer.rotate(BINDING, 150)
    dimmer.rotate(BINDING, -75)
    release.set()
    await wait_worker(dimmer)
    assert sent == [35, 42.5]


async def test_shared_target_idle_sync_and_clamping():
    current, now, sent = [90], [10], []
    dimmer = Dimmer(
        lambda _: current[0],
        lambda lights, v, t: record(sent, v, t),
        clock=lambda: now[0],
        command_interval=0,
    )
    dimmer.rotate(BINDING, 1500)
    await wait_worker(dimmer)
    current[0] = 5  # Delayed/externally changed state must not reset an active gesture.
    dimmer.rotate(BINDING, -150)
    await wait_worker(dimmer)
    assert sent[-1][0] == 85
    now[0] = 15
    dimmer.rotate(BINDING, -150)
    await wait_worker(dimmer)
    assert sent[-1][0] == 0


async def test_unavailable_and_disabled_do_not_send():
    sent = []
    dimmer = Dimmer(lambda _: None, lambda lights, v, t: record(sent, v, t), command_interval=0)
    dimmer.rotate(BINDING, 100)
    dimmer.rotate({**BINDING, "enabled": False}, 100)
    assert sent == []
    assert all(target.task is None for target in dimmer.targets.values())


async def test_failure_resync_and_cancel():
    sent = []

    async def failed(lights, v, t):
        raise RuntimeError("test failure")

    dimmer = Dimmer(lambda _: 20, failed, command_interval=0)
    dimmer.rotate(BINDING, 15)
    await wait_worker(dimmer)
    assert dimmer.targets[("light.test",)].brightness is None
    dimmer.send = lambda lights, v, t: record(sent, v, t)
    dimmer.rotate(BINDING, 15)
    await wait_worker(dimmer)
    assert sent[-1][0] == 21.5
    await dimmer.cancel_targets(("light.test",))
    assert dimmer.targets[("light.test",)].brightness is None
    await dimmer.close()


async def test_button_ramp_steps_from_last_target_and_stops_immediately():
    sent = []
    now = [0.0]
    dimmer = Dimmer(
        lambda _: 40,
        lambda lights, value, ramp: record(sent, value, ramp),
        clock=lambda: now[0],
        command_interval=0,
    )
    dimmer.button_step(("light.test",), "up", 0.65, step=5)
    await wait_worker(dimmer)
    now[0] = 0.65
    dimmer.button_step(("light.test",), "up", 0.34, step=5)
    await wait_worker(dimmer)
    assert sent == [(45, 0.65), (50, 0.34)]
    now[0] = 0.82
    await dimmer.stop_button_ramp(("light.test",))
    assert sent[-1] == (pytest.approx(47.5), 0)
    assert dimmer.targets[("light.test",)].brightness == pytest.approx(47.5)


async def test_button_ramp_release_freezes_current_transition_level():
    sent = []
    now = [10.0]
    dimmer = Dimmer(
        lambda _: 40,
        lambda lights, value, ramp: record(sent, value, ramp),
        clock=lambda: now[0],
        command_interval=0,
    )
    dimmer.button_step(("light.test",), "up", 1.0, step=5)
    await wait_worker(dimmer)

    now[0] = 10.5
    await dimmer.stop_button_ramp(("light.test",))

    assert sent == [(45, 1.0), (42.5, 0)]
    assert dimmer.targets[("light.test",)].brightness == 42.5


async def test_adaptive_custom_follows_cadence_and_discards_old_goal_on_reverse():
    now, sent = [10.0], []
    dimmer = Dimmer(
        lambda _: 40,
        lambda lights, v, t: record(sent, v, t),
        clock=lambda: now[0],
        command_interval=0,
    )
    binding = {**BINDING, "dial_profile": "custom", "adaptive_transition": True}
    dimmer.rotate(binding, 150)
    await wait_worker(dimmer)
    assert sent[-1] == (55, 0.4)
    now[0] += 0.2
    dimmer.rotate(binding, -15)
    await wait_worker(dimmer)
    assert sent[-1][0] == pytest.approx(46)
    assert sent[-1][1] == pytest.approx(0.2)


async def test_named_presets_always_use_adaptive_transition():
    sent = []
    dimmer = Dimmer(lambda _: 10, lambda lights, v, t: record(sent, v, t), command_interval=0)
    dimmer.rotate({**BINDING, "dial_profile": "balanced", "adaptive_transition": False}, 15)
    await wait_worker(dimmer)
    assert sent == [(11.5, 0.4)]
