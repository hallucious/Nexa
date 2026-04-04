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



def test_savefile_executor_propagates_child_failure_with_trace_summary(tmp_path: Path):
    mod = tmp_path / "fail_plugin_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {}, 'artifacts': [], 'trace': {'reason': 'boom'}, 'error': {'message': 'boom'}, 'success': False}\n",
        encoding="utf-8",
    )
    payload = _payload("fail_plugin_mod.run")
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(payload)
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="test-run")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "failure"
    result = trace.node_results["n1"]
    assert result.status == "failure"
    assert result.error == "Child subcircuit execution failed"
    assert result.trace["child_circuit_ref"] == "internal:review_bundle"
    assert result.trace["child_run_id"] == "subcircuit:n1:review_bundle"
    assert result.trace["child_status"] == "failure"
    assert result.trace["child_failed_nodes"] == ["c1"]


def test_savefile_executor_fails_when_bound_child_output_cannot_be_resolved(tmp_path: Path):
    mod = tmp_path / "bad_output_plugin_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'other': text}, 'artifacts': [], 'trace': {}, 'error': None}\n",
        encoding="utf-8",
    )
    payload = _payload("bad_output_plugin_mod.run")
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(payload)
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="test-run")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "failure"
    result = trace.node_results["n1"]
    assert result.status == "failure"
    assert "Subcircuit output resolution failed" in result.error
    assert result.trace["child_status"] == "success"



def test_savefile_executor_supports_node_output_input_mapping_into_subcircuit(tmp_path: Path):
    mod = tmp_path / "echo_plugin_mod2.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'result': f'child:{text}'}, 'artifacts': [], 'trace': {}, 'error': None}\n",
        encoding="utf-8",
    )
    payload = {
        "meta": {"name": "demo", "version": "2.0.0"},
        "circuit": {
            "entry": "n0",
            "nodes": [
                {
                    "id": "n0",
                    "type": "plugin",
                    "resource_ref": {"plugin": "plugin.seed"},
                    "inputs": {"text": "input.question"},
                    "outputs": {"result": "state.working.seed"},
                },
                {
                    "id": "n1",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:review_bundle",
                            "input_mapping": {"question": "node.n0.output.result"},
                            "output_binding": {"result": "child.output.result"},
                        }
                    },
                    "outputs": {"result": "state.working.result"},
                },
            ],
            "edges": [{"from": "n0", "to": "n1"}],
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
            "plugins": {
                "plugin.seed": {"entry": "echo_plugin_mod2.run"},
                "plugin.echo": {"entry": "echo_plugin_mod2.run"},
            },
        },
        "state": {"input": {"question": "hi"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(payload)
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="test-run")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "success"
    assert trace.node_results["n1"].output == {"result": "child:child:hi"}
    assert trace.final_state["working"]["result"] == "child:child:hi"



def test_savefile_executor_subcircuit_trace_mode_full_includes_child_trace_and_artifacts(tmp_path: Path):
    mod = tmp_path / "artifact_plugin_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'result': f'echo:{text}'}, 'artifacts': [{'kind': 'note', 'value': text}], 'trace': {'plugin': 'ok'}, 'error': None}\n",
        encoding="utf-8",
    )
    payload = _payload("artifact_plugin_mod.run")
    payload["circuit"]["nodes"][0]["execution"]["subcircuit"]["runtime_policy"] = {"trace_mode": "full"}
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(payload)
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="test-run")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "success"
    result = trace.node_results["n1"]
    assert result.status == "success"
    assert result.trace["child_status"] == "success"
    assert result.trace["child_artifact_count"] == 1
    assert "child_trace" in result.trace
    child_trace = result.trace["child_trace"]
    assert child_trace.status == "success"
    assert child_trace.run_id == "subcircuit:n1:review_bundle"
    assert result.artifacts == [{"kind": "note", "value": "hi"}]


def test_savefile_executor_subcircuit_max_depth_exceeded_for_nested_subcircuits(tmp_path: Path):
    mod = tmp_path / "nested_plugin_mod.py"
    mod.write_text(
        "def run(text):\n"
        "    return {'output': {'result': text}, 'artifacts': [], 'trace': {}, 'error': None}\n",
        encoding="utf-8",
    )
    payload = {
        "meta": {"name": "demo", "version": "2.0.0"},
        "circuit": {
            "entry": "n1",
            "nodes": [
                {
                    "id": "n1",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:level1",
                            "input_mapping": {"question": "input.question"},
                            "output_binding": {"result": "child.output.result"},
                            "runtime_policy": {"max_child_depth": 1},
                        }
                    },
                    "outputs": {"result": "state.working.result"},
                }
            ],
            "edges": [],
            "subcircuits": {
                "level1": {
                    "entry": "c1",
                    "nodes": [
                        {
                            "id": "c1",
                            "kind": "subcircuit",
                            "execution": {
                                "subcircuit": {
                                    "child_circuit_ref": "internal:level2",
                                    "input_mapping": {"question": "input.question"},
                                    "output_binding": {"result": "child.output.result"},
                                }
                            },
                            "outputs": {"result": "state.working.result"},
                        }
                    ],
                    "edges": [],
                    "outputs": [{"name": "result", "source": "state.working.result"}],
                },
                "level2": {
                    "entry": "c2",
                    "nodes": [
                        {
                            "id": "c2",
                            "type": "plugin",
                            "resource_ref": {"plugin": "plugin.echo"},
                            "inputs": {"text": "input.question"},
                            "outputs": {"result": "state.working.result"},
                        }
                    ],
                    "edges": [],
                    "outputs": [{"name": "result", "source": "state.working.result"}],
                },
            },
        },
        "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.echo": {"entry": "nested_plugin_mod.run"}}},
        "state": {"input": {"question": "hi"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = load_savefile(payload)
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile, run_id="test-run")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "failure"
    result = trace.node_results["n1"]
    assert result.status == "failure"
    assert result.error == "Child subcircuit execution failed"
    assert result.trace["child_status"] == "failure"
    assert result.trace["child_failed_nodes"] == ["c1"]
