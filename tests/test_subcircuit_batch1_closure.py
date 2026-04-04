from pathlib import Path
import sys

from src.contracts.savefile_loader import load_savefile
from src.contracts.savefile_validator import SavefileValidationError, validate_savefile
from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.platform.provider_registry import ProviderRegistry


def _plugin_payload(entry_path: str):
    return {
        "meta": {"name": "batch1-demo", "version": "2.0.0"},
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
                    "outputs": {"result": "state.working.result"},
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
        "resources": {
            "prompts": {},
            "providers": {},
            "plugins": {"plugin.echo": {"entry": entry_path}},
        },
        "state": {"input": {"question": "hi"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }


def test_batch1_parser_recognizes_subcircuit_kind_and_registry():
    savefile = load_savefile(_plugin_payload("noop.module"))
    node = savefile.circuit.nodes[0]
    assert node.node_kind == "subcircuit"
    assert "review_bundle" in savefile.circuit.subcircuits


def test_batch1_validator_resolves_internal_reference_and_accepts_valid_shape(tmp_path: Path):
    mod = tmp_path / "batch1_echo_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'result': text}, 'artifacts': [], 'trace': {}, 'error': None}\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        findings = validate_savefile(load_savefile(_plugin_payload("batch1_echo_mod.run")))
    finally:
        sys.path.remove(str(tmp_path))
    assert findings == []


def test_batch1_validator_propagates_child_invalidity_to_parent():
    payload = _plugin_payload("noop.module")
    payload["circuit"]["subcircuits"]["review_bundle"]["outputs"] = [
        {"name": "result", "source": "node.missing.output.result"}
    ]
    with __import__("pytest").raises(SavefileValidationError, match="references unknown child node"):
        validate_savefile(load_savefile(payload))


def test_batch1_runtime_executes_subcircuit_and_binds_parent_output(tmp_path: Path):
    mod = tmp_path / "batch1_echo_mod2.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'result': f'echo:{text}'}, 'artifacts': [], 'trace': {}, 'error': None}\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(_plugin_payload("batch1_echo_mod2.run"))
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="batch1-run")
    finally:
        sys.path.remove(str(tmp_path))
    assert trace.status == "success"
    assert trace.node_results["n1"].output == {"result": "echo:hi"}
    assert trace.final_state["working"]["result"] == "echo:hi"


def test_batch1_runtime_keeps_parent_child_exchange_mapping_based(tmp_path: Path):
    mod = tmp_path / "batch1_mutating_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {\n"
        "        'output': {'result': f'echo:{text}'},\n"
        "        'artifacts': [],\n"
        "        'trace': {'attempted_parent_write': True},\n"
        "        'error': None,\n"
        "        'working': {'hacked': True},\n"
        "    }\n",
        encoding="utf-8",
    )
    payload = _plugin_payload("batch1_mutating_mod.run")
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(payload)
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="batch1-run")
    finally:
        sys.path.remove(str(tmp_path))
    assert trace.status == "success"
    assert trace.final_state["working"]["result"] == "echo:hi"
    assert "hacked" not in trace.final_state["working"]
