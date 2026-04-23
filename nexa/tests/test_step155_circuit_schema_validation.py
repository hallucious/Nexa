import pytest
import yaml

from src.circuit.circuit_io import load_circuit
from src.circuit.circuit_schema_validator import (
    CircuitSchemaValidationError,
    CircuitSchemaValidator,
)


def test_step155_rejects_non_object_root():
    with pytest.raises(CircuitSchemaValidationError, match="root must be an object"):
        CircuitSchemaValidator([{"id": "n1"}]).validate()


def test_step155_rejects_missing_nodes_field(tmp_path):
    path = tmp_path / "missing_nodes.nex"
    path.write_text(yaml.safe_dump({"version": "1.0.0"}), encoding="utf-8")

    with pytest.raises(CircuitSchemaValidationError, match="missing required field: nodes"):
        load_circuit(str(path))


def test_step155_rejects_non_list_nodes(tmp_path):
    path = tmp_path / "bad_nodes.nex"
    path.write_text(yaml.safe_dump({"nodes": {"id": "n1"}}), encoding="utf-8")

    with pytest.raises(CircuitSchemaValidationError, match="'nodes' must be a list"):
        load_circuit(str(path))


def test_step155_rejects_invalid_node_shape(tmp_path):
    path = tmp_path / "bad_node.nex"
    path.write_text(
        yaml.safe_dump({"nodes": [{"id": "n1", "depends_on": []}]}),
        encoding="utf-8",
    )

    with pytest.raises(
        CircuitSchemaValidationError,
        match="missing valid string field: execution_config_ref",
    ):
        load_circuit(str(path))


def test_step155_rejects_invalid_depends_on_type(tmp_path):
    path = tmp_path / "bad_depends_on.nex"
    path.write_text(
        yaml.safe_dump(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "execution_config_ref": "answer.basic",
                        "depends_on": "n0",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CircuitSchemaValidationError, match="field 'depends_on' must be a list"):
        load_circuit(str(path))


def test_step155_rejects_unknown_node_fields(tmp_path):
    path = tmp_path / "unknown_node_field.nex"
    path.write_text(
        yaml.safe_dump(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "execution_config_ref": "answer.basic",
                        "unexpected": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CircuitSchemaValidationError, match="unsupported field"):
        load_circuit(str(path))


def test_step155_accepts_minimal_valid_circuit(tmp_path):
    path = tmp_path / "valid.nex"
    payload = {
        "version": "1.0.0",
        "nodes": [
            {"id": "n1", "execution_config_ref": "answer.basic"},
            {"id": "n2", "execution_config_ref": "reasoning.chain", "depends_on": ["n1"]},
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    loaded = load_circuit(str(path))

    assert loaded == payload