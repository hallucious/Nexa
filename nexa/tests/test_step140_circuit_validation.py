import pytest

from src.circuit.circuit_validator import CircuitValidator, CircuitValidationError


def test_duplicate_node_detection():

    nodes = [
        {"id": "A"},
        {"id": "A"}
    ]

    validator = CircuitValidator(nodes)

    with pytest.raises(CircuitValidationError):
        validator.validate()


def test_missing_dependency():

    nodes = [
        {"id": "A", "depends_on": ["B"]}
    ]

    validator = CircuitValidator(nodes)

    with pytest.raises(CircuitValidationError):
        validator.validate()


def test_cycle_detection():

    nodes = [
        {"id": "A", "depends_on": ["B"]},
        {"id": "B", "depends_on": ["A"]}
    ]

    validator = CircuitValidator(nodes)

    with pytest.raises(CircuitValidationError):
        validator.validate()