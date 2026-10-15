"""Explicit, save-time sensor configuration; never enable native behavior rules."""

import aiohttp

from .api import BridgeError


async def request(client, kind, resource=None, body=None):
    host, key = client.credentials()
    url = f"https://{host}/clip/v2/resource/{kind}" + (f"/{resource}" if resource else "")
    method = client.session.get if body is None else client.session.put
    kwargs = {"headers": {"hue-application-key": key}, "timeout": aiohttp.ClientTimeout(total=5)}
    if body is not None:
        kwargs["json"] = body
    try:
        async with method(url, **kwargs) as response:
            if response.status not in ((200,) if body is None else (200, 207)):
                raise BridgeError(f"Hue configuration HTTP status {response.status}")
            payload = await response.json()
            if (
                not isinstance(payload, dict)
                or payload.get("errors")
                or not isinstance(payload.get("data"), list)
            ):
                raise BridgeError("Hue rejected motion configuration")
            return payload["data"]
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise BridgeError("Cannot access Hue motion configuration") from err


async def sensor_settings(client, device):
    resource = next((s["rid"] for s in device.get("services", []) if s["rtype"] == "motion"), None)
    if not resource:
        raise BridgeError("Motion resource is unavailable")
    data = await request(client, "motion", resource)
    if len(data) != 1:
        raise BridgeError("Motion resource is unavailable")
    sensitivity = data[0].get("sensitivity", {})
    maximum = sensitivity.get("sensitivity_max")
    current = sensitivity.get("sensitivity")
    if not isinstance(maximum, int) or maximum <= 0 or not isinstance(current, int):
        return resource, None, None
    return resource, current, maximum


async def save_settings(client, owner, device, binding):
    if not binding.get("enabled", False):
        return
    resource, current, maximum = await sensor_settings(client, device)
    plan = []
    level = binding.get("motion_sensitivity")
    if level is not None and maximum is not None:
        current_level = round(current * 2 / maximum)
        if level != current_level:
            value = round(maximum * level / 2)
            plan.append(
                (
                    "motion",
                    resource,
                    {"sensitivity": {"sensitivity": value}},
                    {"sensitivity": {"sensitivity": current}},
                )
            )
    applied = []
    try:
        for kind, rid, new, old in plan:
            applied.append((kind, rid, old))
            await request(client, kind, rid, new)
    except BridgeError:
        for kind, rid, old in reversed(applied):
            try:
                await request(client, kind, rid, old)
            except BridgeError:
                raise BridgeError(
                    "Motion configuration failed; rollback could not be confirmed"
                ) from None
        raise
