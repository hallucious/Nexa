from src.contracts.execution_event_contract import ExecutionEvent
from src.engine.execution_timeline import ExecutionTimelineBuilder


def test_basic_timeline_build():

    events = [
        ExecutionEvent("execution_started", "run1", None, 0, {}),
        ExecutionEvent("node_started", "run1", "A", 10, {}),
        ExecutionEvent("node_completed", "run1", "A", 20, {}),
        ExecutionEvent("execution_completed", "run1", None, 30, {}),
    ]

    builder = ExecutionTimelineBuilder()
    bundle = builder.build(events)

    timeline = bundle.timeline
    profile = bundle.profile

    assert timeline.duration_ms == 30
    assert len(timeline.node_spans) == 1
    assert timeline.node_spans[0].duration_ms == 10

    assert profile.total_nodes == 1
    assert profile.succeeded_nodes == 1
    assert profile.failed_nodes == 0