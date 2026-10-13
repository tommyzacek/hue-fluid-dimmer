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
