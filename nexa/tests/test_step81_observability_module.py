from src.utils.observability import make_event

def test_make_event_has_required_fields():
    e = make_event(run_id="r1", circuit_id="c1", node_id="n1", stage="core", event="node.enter")
    assert "ts_utc" in e
    assert e["run_id"] == "r1"
    assert e["circuit_id"] == "c1"
    assert e["node_id"] == "n1"
    assert e["stage"] == "core"
    assert e["event"] == "node.enter"
