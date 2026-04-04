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


def test_validate_savefile_rejects_invalid_subcircuit_input_mapping_path():
    payload = _base_payload()
    payload["circuit"]["nodes"][0]["execution"]["subcircuit"]["input_mapping"] = {"question": "ui.layout"}
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="UI must not affect execution"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_invalid_subcircuit_output_binding_target():
    payload = _base_payload()
    payload["circuit"]["nodes"][0]["execution"]["subcircuit"]["output_binding"] = {"result": "state.working.result"}
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="must target child.output"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_recursive_subcircuit_reference():
    payload = _base_payload()
    payload["circuit"]["subcircuits"]["review_bundle"]["nodes"] = [
        {
            "id": "c1",
            "kind": "subcircuit",
            "execution": {
                "subcircuit": {
                    "child_circuit_ref": "internal:review_bundle",
                    "input_mapping": {"question": "input.question"},
                    "output_binding": {"result": "child.output.result"},
                }
            },
        }
    ]
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="recursive reference"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_subcircuit_depth_overflow():
    payload = _base_payload()
    payload["circuit"]["subcircuits"] = {
        "review_bundle": {
            "entry": "s1",
            "nodes": [
                {
                    "id": "s1",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:level2",
                            "input_mapping": {"question": "input.question"},
                            "output_binding": {"result": "child.output.result"},
                        }
                    },
                }
            ],
            "edges": [],
            "outputs": [{"name": "result", "source": "node.s1.output.result"}],
        },
        "level2": {
            "entry": "s2",
            "nodes": [
                {
                    "id": "s2",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:level3",
                            "input_mapping": {"question": "input.question"},
                            "output_binding": {"result": "child.output.result"},
                        }
                    },
                }
            ],
            "edges": [],
            "outputs": [{"name": "result", "source": "node.s2.output.result"}],
        },
        "level3": {
            "entry": "s3",
            "nodes": [
                {
                    "id": "s3",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:level4",
                            "input_mapping": {"question": "input.question"},
                            "output_binding": {"result": "child.output.result"},
                        }
                    },
                }
            ],
            "edges": [],
            "outputs": [{"name": "result", "source": "node.s3.output.result"}],
        },
        "level4": {
            "entry": "c4",
            "nodes": [
                {
                    "id": "c4",
                    "type": "plugin",
                    "resource_ref": {"plugin": "plugin.echo"},
                    "inputs": {"text": "input.question"},
                    "outputs": {"result": "state.working.result"},
                }
            ],
            "edges": [],
            "outputs": [{"name": "result", "source": "state.working.result"}],
        },
    }
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="max depth exceeded"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_invalid_child_circuit_and_propagates_to_parent():
    payload = _base_payload()
    payload["circuit"]["subcircuits"]["review_bundle"]["nodes"][0]["resource_ref"] = {"plugin": "plugin.missing"}
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="references unknown plugin"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_invalid_child_output_source():
    payload = _base_payload()
    payload["circuit"]["subcircuits"]["review_bundle"]["outputs"] = [
        {"name": "result", "source": "node.missing.output.result"}
    ]
    savefile = load_savefile(payload)
    with pytest.raises(SavefileValidationError, match="references unknown child node"):
        validate_savefile(savefile)
