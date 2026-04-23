
def test_trace_boundaries_smoke():
    from src.circuit.trace import CircuitTrace
    t = CircuitTrace(circuit_id="x")
    assert t.started_at is not None
