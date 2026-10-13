from custom_components.hue_rotary_fast.models import ReportTracker, parse_rotation


def test_baseline_duplicates_out_of_order_and_two_controllers(resource):
    tracker = ReportTracker()
    tracker.baseline([resource(), resource(resource_id="dial-b", report=False)])
    assert tracker.consume([resource()]) == []
    reports = tracker.consume([resource(2), resource(1, resource_id="dial-b")])
    assert [r.resource_id for r in reports] == ["dial-a", "dial-b"]
    assert tracker.consume([resource(1), resource(2)]) == []
    assert tracker.consume([resource(3, resource_id="new")]) == []
    assert len(tracker.consume([resource(4, resource_id="new")])) == 1


def test_recovery_does_not_replay_an_outage(resource):
    tracker = ReportTracker()
    tracker.baseline([resource()])
    tracker.baseline([resource(10)])
    assert tracker.consume([resource(10)]) == []
    assert len(tracker.consume([resource(11)])) == 1


def test_direction_and_validation(resource):
    assert parse_rotation(resource(direction="counter_clock_wise", steps=330)).signed_steps == -330
    for item in [
        resource(report=False),
        {},
        resource(steps=True),
        resource(steps=-1),
        resource(direction="other"),
    ]:
        assert parse_rotation(item) is None
