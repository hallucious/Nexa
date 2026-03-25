from __future__ import annotations

import sys
from pathlib import Path

from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.contracts.savefile_format import (
    CircuitSpec,
    NodeSpec,
    PluginResource,
    ResourcesSpec,
    Savefile,
    SavefileMeta,
    StateSpec,
    UISpec,
)
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry


class _UnusedProviderExecutor:
    def execute(self, provider_id, **kwargs):
        raise RuntimeError("provider should not be called")


def test_step196_runtime_graph_plugin_counts_one_call_per_execution(tmp_path: Path):
    runtime = NodeExecutionRuntime(
        provider_executor=_UnusedProviderExecutor(),
        plugin_registry={"search": lambda query: {"result": f"search:{query}"}},
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    result = runtime.execute(
        {
            "config_id": "ec_step196",
            "plugins": [
                {
                    "plugin_id": "search",
                    "inputs": {"query": "input.query"},
                    "output_fields": ["result"],
                }
            ],
        },
        {"query": "nexa"},
    )

    assert result.output == "search:nexa"
    assert runtime.get_metrics()["plugin_calls"] == 1
    assert any(event.startswith("plugin_execute:search") for event in result.trace.events)


def test_step196_savefile_plugin_preserves_artifacts_and_trace(tmp_path: Path):
    module_path = tmp_path / "artifact_plugin.py"
    module_path.write_text(
        "from src.engine.node_execution_runtime import Artifact\n"
        "def run_plugin(msg):\n"
        "    return {\n"
        "        'output': {'echo': msg},\n"
        "        'artifacts': [Artifact(type='preview', name='plugin_preview', data={'value': msg})],\n"
        "        'trace': {'progress': {'processed': 1, 'total': 1}},\n"
        "    }\n",
        encoding="utf-8",
    )

    savefile = Savefile(
        meta=SavefileMeta(name="plugin-trace", version="2.0.0"),
        circuit=CircuitSpec(
            entry="plugin_node",
            nodes=[
                NodeSpec(
                    id="plugin_node",
                    type="plugin",
                    resource_ref={"plugin": "plugin.main"},
                    inputs={"msg": "state.input.msg"},
                    outputs={"echo": "state.working.echo"},
                )
            ],
        ),
        resources=ResourcesSpec(
            plugins={"plugin.main": PluginResource(entry="artifact_plugin.run_plugin")}
        ),
        state=StateSpec(input={"msg": "hello"}),
        ui=UISpec(),
    )

    sys.path.insert(0, str(tmp_path))
    try:
        trace = SavefileExecutor(ProviderRegistry()).execute(savefile)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("artifact_plugin", None)

    node_result = trace.node_results["plugin_node"]
    assert node_result.status == "success"
    assert node_result.output == {"echo": "hello"}
    assert len(node_result.artifacts) == 1
    assert node_result.artifacts[0].name == "plugin_preview"
    assert node_result.trace["plugin_trace"]["progress"]["processed"] == 1
    assert trace.all_artifacts[0].name == "plugin_preview"
