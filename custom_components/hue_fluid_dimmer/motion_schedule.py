"""Contiguous, local-time motion periods; a running cycle keeps its chosen period."""

from copy import deepcopy


def periods_for(binding):
    if binding.get("motion_periods") is not None:
        return deepcopy(binding["motion_periods"])
    return [
        {
            "id": "all_day",
            "start": "00:00",
            "do_not_disturb": False,
            "override_targets": False,
            "targets": [],
            "timeout": max(
                60,
                min(
                    3600,
                    round(
                        binding.get("motion_timeout", 300)
                        / (30 if binding.get("motion_timeout", 300) <= 600 else 60)
                    )
                    * (30 if binding.get("motion_timeout", 300) <= 600 else 60),
                ),
            ),
            "startup": deepcopy(binding.get("motion_start", {})),
        }
    ]


def validate_periods(periods, validate_start):
    if not isinstance(periods, list) or not periods:
        raise ValueError("At least one period is required")
    result, starts, ids = [], set(), set()
    for period in periods:
        if not isinstance(period, dict):
            raise ValueError("Invalid period")
        start = period.get("start")
        if not isinstance(start, str) or len(start) != 5 or start[2] != ":":
            raise ValueError("Invalid start time")
        try:
            hour, minute = map(int, start.split(":"))
        except ValueError:
            raise ValueError("Invalid start time") from None
        if not 0 <= hour < 24 or not 0 <= minute < 60 or start != f"{hour:02}:{minute:02}":
            raise ValueError("Invalid start time")
        if start in starts:
            raise ValueError("Periods must have different start times")
        starts.add(start)
        timeout = period.get("timeout", 300)
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or not 60 <= timeout <= 3600
            or timeout % (30 if timeout <= 600 else 60)
        ):
            raise ValueError("Invalid timeout")
        startup, error = validate_start({"motion_start": period.get("startup", {})})
        if error:
            raise ValueError("Invalid startup settings")
        targets = period.get("targets", [])
        override = period.get("override_targets", False)
        quiet = period.get("do_not_disturb", False)
        if (
            not isinstance(override, bool)
            or not isinstance(quiet, bool)
            or not isinstance(targets, list)
            or any(not isinstance(e, str) or not e.startswith("light.") for e in targets)
            or (override and not quiet and not targets)
        ):
            raise ValueError("Invalid period targets")
        identity = period.get("id", start)
        if not isinstance(identity, str) or identity in ids:
            raise ValueError("Invalid period identifier")
        ids.add(identity)
        result.append(
            {
                "id": identity,
                "start": start,
                "timeout": int(timeout),
                "startup": startup["motion_start"],
                "do_not_disturb": quiet,
                "override_targets": override,
                "targets": list(dict.fromkeys(targets)),
            }
        )
    return sorted(result, key=lambda item: item["start"])


def effective_binding(binding, now):
    periods = periods_for(binding)
    ordered = sorted(periods, key=lambda p: p["start"])
    current = now.strftime("%H:%M")
    chosen = next((p for p in reversed(ordered) if p["start"] <= current), ordered[-1])
    if chosen.get("do_not_disturb"):
        return None
    result = deepcopy(binding)
    result["motion_start"] = deepcopy(chosen.get("startup", {}))
    result["motion_timeout"] = chosen.get("timeout", 300)
    if chosen.get("override_targets"):
        result["motion_targets"] = list(chosen["targets"])
    result["motion_period_id"] = chosen["id"]
    return result
