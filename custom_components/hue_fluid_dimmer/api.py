"""Small async REST adapter. No imports from Hue's private runtime objects."""

import json
from collections.abc import Callable
from typing import Any

import aiohttp


class BridgeError(Exception):
    """Bridge unavailable, rejected authentication, or invalid response."""

    def __init__(self, message: str, retry_after: float = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def retry_delay(response) -> float:
    try:
        return max(0, float(response.headers.get("Retry-After", 0)))
    except TypeError, ValueError:
        return 0


class BridgeClient:
    """Reuse HA's session; fetch all dials with one request per bridge."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        credentials: Callable[[], tuple[str, str]],
    ) -> None:
        self.session = session
        self.credentials = credentials

    async def rotary_resources(self) -> list[dict[str, Any]]:
        host, key = self.credentials()
        try:
            async with self.session.get(
                f"https://{host}/clip/v2/resource/relative_rotary",
                headers={"hue-application-key": key},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status != 200:
                    try:
                        retry_after = max(0, float(response.headers.get("Retry-After", 0)))
                    except ValueError:
                        retry_after = 0
                    raise BridgeError(f"Hue HTTP status {response.status}", retry_after)
                payload = await response.json()
                if (
                    not isinstance(payload, dict)
                    or payload.get("errors")
                    or not isinstance(payload.get("data"), list)
                    or any(not isinstance(item, dict) for item in payload["data"])
                ):
                    raise BridgeError("Invalid Hue resource response")
                return payload["data"]
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            # Do not log request headers, URLs or credentials.
            raise BridgeError("Cannot read Hue rotary resources") from err

    async def device_resources(self) -> list[dict[str, Any]]:
        host, key = self.credentials()
        try:
            async with self.session.get(
                f"https://{host}/clip/v2/resource/device",
                headers={"hue-application-key": key},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status != 200:
                    raise BridgeError(f"Hue HTTP status {response.status}", retry_delay(response))
                payload = await response.json()
                if (
                    not isinstance(payload, dict)
                    or payload.get("errors")
                    or not isinstance(payload.get("data"), list)
                    or any(not isinstance(item, dict) for item in payload["data"])
                ):
                    raise BridgeError("Invalid Hue device response")
                return payload["data"]
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeError("Cannot read Hue devices") from err

    async def button_resources(self) -> list[dict[str, Any]]:
        host, key = self.credentials()
        try:
            async with self.session.get(
                f"https://{host}/clip/v2/resource/button",
                headers={"hue-application-key": key},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status != 200:
                    raise BridgeError(f"Hue HTTP status {response.status}", retry_delay(response))
                payload = await response.json()
                if (
                    not isinstance(payload, dict)
                    or payload.get("errors")
                    or not isinstance(payload.get("data"), list)
                    or any(not isinstance(item, dict) for item in payload["data"])
                ):
                    raise BridgeError("Invalid Hue button response")
                return payload["data"]
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeError("Cannot read Hue buttons") from err

    async def brightness_transition(
        self,
        resource_type: str,
        resource_id: str,
        brightness: float,
        duration_ms: int,
    ) -> None:
        """Ask the Hue Bridge to run a native brightness transition."""
        if resource_type not in ("light", "grouped_light"):
            raise BridgeError("Unsupported Hue dimming resource")
        host, key = self.credentials()
        on = brightness > 0
        body = {
            "on": {"on": on},
            "dimming": {"brightness": max(0.0, min(100.0, brightness))},
            "dynamics": {"duration": max(0, duration_ms)},
        }
        await self._put_resource(host, key, resource_type, resource_id, body)

    async def read_brightness(self, resource_type: str, resource_id: str) -> float:
        """Read the current bridge brightness, avoiding HA's transition target state."""
        if resource_type not in ("light", "grouped_light"):
            raise BridgeError("Unsupported Hue dimming resource")
        host, key = self.credentials()
        try:
            async with self.session.get(
                f"https://{host}/clip/v2/resource/{resource_type}/{resource_id}",
                headers={"hue-application-key": key},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                payload = await response.json()
                if (
                    response.status != 200
                    or not isinstance(payload, dict)
                    or payload.get("errors")
                    or not isinstance(payload.get("data"), list)
                    or not payload["data"]
                ):
                    raise BridgeError(f"Hue HTTP status {response.status}")
                resource = payload["data"][0]
                if not isinstance(resource, dict):
                    raise BridgeError("Invalid Hue brightness response")
                if not resource.get("on", {}).get("on", False):
                    return 0.0
                brightness = resource.get("dimming", {}).get("brightness")
                if not isinstance(brightness, (int, float)):
                    raise BridgeError("Hue resource has no brightness")
                return max(0.0, min(100.0, float(brightness)))
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeError("Cannot read Hue brightness") from err

    async def brightness_delta(
        self,
        resource_type: str,
        resource_id: str,
        delta: float,
        duration_ms: int,
    ) -> None:
        """Move by a small relative brightness amount over a smooth transition."""
        if resource_type not in ("light", "grouped_light"):
            raise BridgeError("Unsupported Hue dimming resource")
        if not delta:
            return
        host, key = self.credentials()
        body = {
            "dimming_delta": {
                "action": "up" if delta > 0 else "down",
                "brightness_delta": abs(delta),
            },
            "dynamics": {"duration": max(0, duration_ms)},
        }
        if delta > 0:
            body["on"] = {"on": True}
        await self._put_resource(host, key, resource_type, resource_id, body)

    async def stop_dimming(self, resource_type: str, resource_id: str) -> None:
        """Stop an active Hue dimming transition at its current bridge level."""
        if resource_type not in ("light", "grouped_light"):
            raise BridgeError("Unsupported Hue dimming resource")
        host, key = self.credentials()
        await self._put_resource(
            host,
            key,
            resource_type,
            resource_id,
            {"dimming_delta": {"action": "stop"}},
        )

    async def _put_resource(
        self,
        host: str,
        key: str,
        resource_type: str,
        resource_id: str,
        body: dict[str, Any],
    ) -> None:
        try:
            async with self.session.put(
                f"https://{host}/clip/v2/resource/{resource_type}/{resource_id}",
                headers={"hue-application-key": key},
                json=body,
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                payload = await response.json()
                if response.status != 200 or not isinstance(payload, dict) or payload.get("errors"):
                    raise BridgeError(f"Hue HTTP status {response.status}")
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeError("Cannot send Hue dimming command") from err

    async def button_events(self):
        """One read-only SSE connection per bridge; never replay on reconnect."""
        host, key = self.credentials()
        try:
            async with self.session.get(
                f"https://{host}/eventstream/clip/v2",
                headers={"hue-application-key": key, "Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=3, sock_read=90),
            ) as response:
                if response.status != 200:
                    raise BridgeError(
                        f"Hue event HTTP status {response.status}", retry_delay(response)
                    )
                data = []
                async for raw in response.content:
                    line = raw.decode("utf-8").rstrip("\r\n")
                    if line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        payload = json.loads("\n".join(data))
                        data.clear()
                        if not isinstance(payload, list):
                            raise BridgeError("Invalid Hue event response")
                        yield payload
                raise BridgeError("Hue event stream closed")
        except (aiohttp.ClientError, TimeoutError, ValueError, UnicodeError) as err:
            raise BridgeError("Cannot read Hue button events") from err
