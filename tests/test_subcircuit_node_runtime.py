from pathlib import Path
import sys

from src.contracts.savefile_loader import load_savefile
from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.platform.provider_registry import ProviderRegistry


def _payload(entry_path: str):
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
        "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.echo": {"entry": entry_path}}},
        "state": {"input": {"question": "hi"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }


def test_savefile_executor_executes_subcircuit_node_and_binds_outputs(tmp_path: Path):
    mod = tmp_path / "echo_plugin_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'result': f'echo:{text}'}, 'artifacts': [], 'trace': {}, 'error': None}\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(_payload("echo_plugin_mod.run"))
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="test-run")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "success"
    assert trace.node_results["n1"].output == {"result": "echo:hi"}
    assert trace.final_state["working"]["result"] == "echo:hi"
