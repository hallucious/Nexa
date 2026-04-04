import pytest

from src.contracts.savefile_loader import load_savefile
from src.contracts.savefile_validator import SavefileValidationError, validate_savefile


def _base_payload():
    return {
        "meta": {"name": "demo", "version": "2.0.0"},
        "circuit": {
            "entry": "n1",
            "nodes": [
                {
                    "id": "n1",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:review_bundle",
                            "input_mapping": {"question": "input.question"},
                            "output_binding": {"result": "child.output.result"},
                        }
                    },
                }
            ],
            "edges": [],
            "subcircuits": {
                "review_bundle": {
                    "entry": "c1",
                    "nodes": [
                        {
                            "id": "c1",
                            "type": "plugin",
                            "resource_ref": {"plugin": "plugin.echo"},
                            "inputs": {"text": "input.question"},
                            "outputs": {"result": "state.working.result"},
                        }
                    ],
                    "edges": [],
                    "outputs": [{"name": "result", "source": "state.working.result"}],
                }
            },
        },
        "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.echo": {"entry": "pkg.echo"}}},
        "state": {"input": {"question": "hi"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }


def test_validate_savefile_accepts_valid_subcircuit_node():
    savefile = load_savefile(_base_payload())
    assert validate_savefile(savefile) == []


def test_validate_savefile_rejects_missing_child_registry_target():
    payload = _base_payload()
    payload["circuit"]["subcircuits"] = {}
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="not found in local subcircuits registry"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_missing_child_output_binding_target():
    payload = _base_payload()
    payload["circuit"]["nodes"][0]["execution"]["subcircuit"]["output_binding"] = {"result": "child.output.missing"}
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="references missing child output"):
        validate_savefile(savefile)
