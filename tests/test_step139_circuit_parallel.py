from src.circuit.circuit_scheduler import CircuitScheduler


def test_step139_execution_waves():

    nodes = [
        {"id": "A"},
        {"id": "B", "depends_on": ["A"]},
        {"id": "C", "depends_on": ["A"]},
        {"id": "D", "depends_on": ["B", "C"]},
    ]

    scheduler = CircuitScheduler(nodes)

    waves = scheduler.execution_waves()

    assert waves == [["A"], ["B", "C"], ["D"]]