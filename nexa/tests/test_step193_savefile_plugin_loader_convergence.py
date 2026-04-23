from __future__ import annotations

import sys
from pathlib import Path

from src.savefiles.executor import execute_plugin_node
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
from src.platform.plugin_auto_loader import load_plugin_entry


def _build_savefile(entry: str) -> Savefile:
    return Savefile(
        meta=SavefileMeta(name="x", version="2.0.0"),
        circuit=CircuitSpec(entry="n1", nodes=[]),
        resources=ResourcesSpec(plugins={"echo": PluginResource(entry=entry)}),
        state=StateSpec(input={"msg": "hello"}),
        ui=UISpec(),
    )


def test_load_plugin_entry_loads_module_function(tmp_path: Path):
    module_path = tmp_path / "my_plugin.py"
    module_path.write_text(
        "def run_plugin(msg):\n    return {'echo': msg}\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        fn = load_plugin_entry("my_plugin.run_plugin")
        assert callable(fn)
        assert fn("hi") == {"echo": "hi"}
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("my_plugin", None)


def test_execute_plugin_node_uses_plugin_auto_loader_entry_path(tmp_path: Path):
    module_path = tmp_path / "my_plugin.py"
    module_path.write_text(
        "def run_plugin(msg):\n    return {'echo': msg}\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        savefile = _build_savefile("my_plugin.run_plugin")
        node = NodeSpec(
            id="n1",
            type="plugin",
            resource_ref={"plugin": "echo"},
            inputs={"msg": "state.input.msg"},
        )
        result = execute_plugin_node(
            node=node,
            savefile=savefile,
            state={"input": {"msg": "hello"}, "working": {}, "memory": {}},
            node_outputs={},
        )
        assert result.status == "success"
        assert result.output == {"echo": "hello"}
        assert result.trace["stage"] == "CORE"
        assert "latency_ms" in result.trace
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("my_plugin", None)
