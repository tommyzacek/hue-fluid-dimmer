"""Small async REST adapter. No imports from Hue's private runtime objects."""

from collections.abc import Callable
from typing import Any

import aiohttp


class BridgeError(Exception):
    """Bridge unavailable, rejected authentication, or invalid response."""

    def __init__(self, message: str, retry_after: float = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


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
