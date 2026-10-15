"""Validate rotary reports and suppress historic/duplicate reports."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Rotation:
    resource_id: str
    owner_id: str
    updated: datetime
    action: str
    direction: str
    steps: int
    duration: int

    @property
    def signed_steps(self) -> int:
        return self.steps if self.direction == "clock_wise" else -self.steps

    def event_data(self) -> dict[str, Any]:
        data = asdict(self)
        data["updated"] = self.updated.isoformat()
        return data


def parse_rotation(resource: dict[str, Any]) -> Rotation | None:
    """Ignore absent and malformed reports without breaking other controllers."""
    try:
        report = resource["relative_rotary"]["rotary_report"]
        rotation = report["rotation"]
        updated = datetime.fromisoformat(report["updated"].replace("Z", "+00:00"))
        steps, duration = rotation["steps"], rotation["duration"]
        if (
            updated.tzinfo is None
            or report["action"] not in ("start", "repeat")
            or rotation["direction"] not in ("clock_wise", "counter_clock_wise")
            or type(steps) is not int
            or not 0 < steps <= 100_000
            or type(duration) is not int
            or duration < 0
        ):
            return None
        return Rotation(
            resource["id"],
            resource["owner"]["rid"],
            updated,
            report["action"],
            rotation["direction"],
            steps,
            duration,
        )
    except KeyError, TypeError, ValueError, AttributeError:
        return None


class ReportTracker:
    """Keep a high-water mark for every resource, including resources with no report."""

    def __init__(self) -> None:
        self.seen: dict[str, datetime | None] = {}

    def baseline(self, resources: list[dict[str, Any]]) -> None:
        for resource in resources:
            if isinstance(resource.get("id"), str):
                report = parse_rotation(resource)
                self.seen[resource["id"]] = report.updated if report else None

    def consume(self, resources: list[dict[str, Any]]) -> list[Rotation]:
        result: list[Rotation] = []
        for resource in resources:
            resource_id = resource.get("id")
            if not isinstance(resource_id, str):
                continue
            report = parse_rotation(resource)
            if resource_id not in self.seen:
                # Newly discovered devices must not replay their historic last action.
                self.seen[resource_id] = report.updated if report else None
            elif report and (
                self.seen[resource_id] is None or report.updated > self.seen[resource_id]
            ):
                self.seen[resource_id] = report.updated
                result.append(report)
        return result
