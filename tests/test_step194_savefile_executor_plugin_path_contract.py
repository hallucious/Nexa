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
from src.platform.provider_registry import ProviderRegistry


def _build_plugin_savefile(entry: str) -> Savefile:
    return Savefile(
        meta=SavefileMeta(name="plugin-savefile", version="2.0.0"),
        circuit=CircuitSpec(
            entry="plugin_node",
            nodes=[
                NodeSpec(
                    id="plugin_node",
                    type="plugin",
                    resource_ref={"plugin": "echo"},
                    inputs={"msg": "state.input.msg"},
                    outputs={"echo": "state.working.echo"},
                )
            ],
            edges=[],
        ),
        resources=ResourcesSpec(
            plugins={"echo": PluginResource(entry=entry)},
        ),
        state=StateSpec(input={"msg": "hello"}),
        ui=UISpec(),
    )


def test_step194_savefile_executor_runs_plugin_node_via_auto_loader(tmp_path: Path):
    module_path = tmp_path / "demo_plugin.py"
    module_path.write_text(
        "def run_plugin(msg):\n    return {\"echo\": msg}\n",
        encoding="utf-8",
    )

    sys.path.insert(0, str(tmp_path))
    try:
        savefile = _build_plugin_savefile("demo_plugin.run_plugin")
        executor = SavefileExecutor(ProviderRegistry())

        trace = executor.execute(savefile, run_id="step194")

        assert trace.status == "success"
        assert trace.node_results["plugin_node"].status == "success"
        assert trace.node_results["plugin_node"].output == {"echo": "hello"}
        assert trace.final_state["working"]["echo"] == "hello"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("demo_plugin", None)
