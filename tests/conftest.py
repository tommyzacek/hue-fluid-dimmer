"""Synthetic reports; no household credentials or identifiers."""

import copy

import pytest


@pytest.fixture
def resource():
    def make(
        second=0,
        *,
        resource_id="dial-a",
        owner_id="owner-a",
        steps=15,
        direction="clock_wise",
        report=True,
    ):
        item = {
            "id": resource_id,
            "type": "relative_rotary",
            "owner": {"rid": owner_id, "rtype": "device"},
            "relative_rotary": {},
        }
        if report:
            item["relative_rotary"]["rotary_report"] = {
                "updated": f"2026-01-01T00:00:{second:02d}Z",
                "action": "start" if second == 0 else "repeat",
                "rotation": {"direction": direction, "steps": steps, "duration": 100},
            }
        return copy.deepcopy(item)

    return make
