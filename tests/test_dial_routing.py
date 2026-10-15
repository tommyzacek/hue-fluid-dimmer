"""Verify temporary wheel targets and both idle deadlines without hardware."""

from unittest.mock import Mock

from custom_components.hue_reconfigo.dial_routing import DialRouting


async def test_unused_takeover_expires_after_five_seconds(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(
        "asyncio.get_running_loop", lambda: Mock(call_later=Mock(return_value=Mock()))
    )
    routing = DialRouting(lambda: clock[0])
    routing.borrow("kitchen", ("number.pwm",))
    clock[0] = 5
    assert routing.motion("kitchen") is None
    assert not routing.leases


async def test_every_motion_renews_five_second_return_and_is_controller_local(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(
        "asyncio.get_running_loop", lambda: Mock(call_later=Mock(return_value=Mock()))
    )
    routing = DialRouting(lambda: clock[0])
    routing.borrow("kitchen", ("number.pwm",))
    clock[0] = 4
    assert routing.motion("kitchen") == ("number.pwm",)
    assert routing.motion("bedroom") is None
    clock[0] = 6
    assert routing.motion("kitchen") == ("number.pwm",)
    assert routing.leases["kitchen"].deadline == 11
    clock[0] = 11
    assert routing.motion("kitchen") is None
    routing.close()


async def test_old_timeout_cannot_expire_a_new_takeover(monkeypatch):
    monkeypatch.setattr(
        "asyncio.get_running_loop", lambda: Mock(call_later=Mock(return_value=Mock()))
    )
    routing = DialRouting(lambda: 0)
    routing.borrow("kitchen", ("fan.one",))
    old = routing.leases["kitchen"]
    routing.borrow("kitchen", ("fan.two",))
    routing.expire("kitchen", old)
    assert routing.motion("kitchen") == ("fan.two",)
    routing.close()
