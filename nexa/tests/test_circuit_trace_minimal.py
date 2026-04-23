
def test_trace_module_import():
    from src.circuit.trace import CircuitTrace
    t = CircuitTrace(circuit_id="x")
    assert t.circuit_id == "x"
