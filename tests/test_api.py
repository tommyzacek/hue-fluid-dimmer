from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hue_fluid_dimmer.api import BridgeClient, BridgeError


def client(payload, status=200, headers=None):
    session = MagicMock()
    response = MagicMock(status=status, headers=headers or {})
    response.json = AsyncMock(return_value=payload)
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=False)
    return BridgeClient(session, lambda: ("bridge.invalid", "test-only-key"))


async def test_one_authenticated_batch_request(resource):
    api = client({"data": [resource(), resource(resource_id="dial-b")], "errors": []})
    assert len(await api.rotary_resources()) == 2
    api.session.get.assert_called_once()
    args, kwargs = api.session.get.call_args
    assert args[0].endswith("/resource/relative_rotary")
    assert kwargs["headers"] == {"hue-application-key": "test-only-key"}
    assert kwargs["timeout"].total == 3


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"data": "wrong"},
        {"data": [None]},
        {"data": [], "errors": [{"description": "denied"}]},
    ],
)
async def test_invalid_or_error_response(payload):
    with pytest.raises(BridgeError):
        await client(payload).rotary_resources()


async def test_rate_limit_respects_retry_after():
    with pytest.raises(BridgeError) as caught:
        await client({}, status=429, headers={"Retry-After": "60"}).rotary_resources()
    assert caught.value.retry_after == 60


async def test_button_resources_are_one_authenticated_discovery_read():
    api = client({"data": [{"id": "button-a"}], "errors": []})
    assert await api.button_resources() == [{"id": "button-a"}]
    args, kwargs = api.session.get.call_args
    assert args[0].endswith("/resource/button")
    assert kwargs["headers"]["hue-application-key"] == "test-only-key"


@pytest.mark.parametrize("payload", [None, {"data": [None]}, {"data": [], "errors": [{}]}])
async def test_invalid_button_discovery_is_recoverable(payload):
    with pytest.raises(BridgeError):
        await client(payload).button_resources()


async def test_sse_frame_boundaries_keep_individual_reports():
    api = client({})
    response = await api.session.get.return_value.__aenter__()

    async def lines():
        yield b": heartbeat\n"
        yield b"\n"
        yield b'data: [{"type":"update",\n'
        yield b'data: "data":[{"id":"a"},{"id":"b"}]}]\n'
        yield b"\n"

    response.content.__aiter__.side_effect = lines
    stream = api.button_events()
    assert await anext(stream) == [{"type": "update", "data": [{"id": "a"}, {"id": "b"}]}]
    await stream.aclose()
    args, kwargs = api.session.get.call_args
    assert args[0].endswith("/eventstream/clip/v2")
    assert kwargs["headers"]["Accept"] == "text/event-stream"
    assert "Last-Event-ID" not in kwargs["headers"]
    assert kwargs["timeout"].total is None


async def test_sse_eof_causes_reconnect_instead_of_busy_loop():
    api = client({})
    response = await api.session.get.return_value.__aenter__()

    async def lines():
        if False:
            yield b""

    response.content.__aiter__.side_effect = lines
    with pytest.raises(BridgeError, match="closed"):
        await anext(api.button_events())
