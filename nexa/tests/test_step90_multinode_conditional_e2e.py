from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest

from src.circuit.model import CircuitModel, EdgeModel, NodeModel
from src.circuit.runtime_adapter import execute_circuit
from src.platform.plugin_version_registry import (
    PluginEntry,
    PluginManifestV1,
    PluginRequires,
    PluginVersionRegistry,
)


# Step90: Multi-node circuit E2E proof with conditional branching.
# Goal:
# - Condition edges evaluated on deterministic plugin results (ctx fields)
# - Exactly one branch is executed
# - Registry-based plugin resolution is preserved
# - Circuit trace records condition evaluation and selected edge


class _SetFlagPlugin:
    def run(self, *, flag: str) -> Dict[str, Any]:
        return {"flag": str(flag)}


class _DoublePlugin:
    def run(self, *, x: int) -> Dict[str, Any]:
        return {"result": int(x) * 2}


class _TriplePlugin:
    def run(self, *, x: int) -> Dict[str, Any]:
        return {"result": int(x) * 3}


class _SpyRegistry(PluginVersionRegistry):
    def __init__(self) -> None:
        super().__init__()
        self.resolve_calls: int = 0
        self.last_resolve: Optional[Dict[str, str]] = None

    def resolve(self, *, plugin_id: str, version: str) -> PluginEntry:  # type: ignore[override]
        self.resolve_calls += 1
        self.last_resolve = {"plugin_id": plugin_id, "version": version}
        return super().resolve(plugin_id=plugin_id, version=version)


@dataclass
class _MockProvider:
    """Deterministic provider used only to produce a tool-call for NodeA."""

    negotiate_called: bool = False
    last_flag: Optional[str] = None

    def negotiate(self) -> None:
        self.negotiate_called = True

    def generate_tool_call(self, *, desired_flag: str) -> Dict[str, Any]:
        self.last_flag = desired_flag
        return {
            "tool": {
                "plugin_id": "set_flag",
                "plugin_version": "1.0.0",
                "args": {"flag": desired_flag},
            }
        }


def _register_plugins(reg: PluginVersionRegistry) -> None:
    reg.register(
        entry=PluginEntry(
            manifest=PluginManifestV1(
                plugin_id="set_flag",
                plugin_version="1.0.0",
                description="set flag",
                stages_allowed=["core"],
                default_timeout_ms=1000,
                side_effects=[],
                requires=PluginRequires(node_exec_min="1.0.0", plugin_contract_min="1.0.0"),
            ),
            entrypoint=_SetFlagPlugin,
            factory=_SetFlagPlugin,
        )
    )
    reg.register(
        entry=PluginEntry(
            manifest=PluginManifestV1(
                plugin_id="math_double",
                plugin_version="1.0.0",
                description="double x",
                stages_allowed=["core"],
                default_timeout_ms=1000,
                side_effects=[],
                requires=PluginRequires(node_exec_min="1.0.0", plugin_contract_min="1.0.0"),
            ),
            entrypoint=_DoublePlugin,
            factory=_DoublePlugin,
        )
    )
    reg.register(
        entry=PluginEntry(
            manifest=PluginManifestV1(
                plugin_id="math_triple",
                plugin_version="1.0.0",
                description="triple x",
                stages_allowed=["core"],
                default_timeout_ms=1000,
                side_effects=[],
                requires=PluginRequires(node_exec_min="1.0.0", plugin_contract_min="1.0.0"),
            ),
            entrypoint=_TriplePlugin,
            factory=_TriplePlugin,
        )
    )


def _make_model(*, desired_flag: str) -> CircuitModel:
    nodes = {
        "A": NodeModel("A", {"id": "A", "desired_flag": desired_flag}),
        "B": NodeModel(
            "B",
            {
                "id": "B",
                "tool": {"plugin_id": "math_double", "plugin_version": "1.0.0", "args": {"x": 1}},
            },
        ),
        "C": NodeModel(
            "C",
            {
                "id": "C",
                "tool": {"plugin_id": "math_triple", "plugin_version": "1.0.0", "args": {"x": 1}},
            },
        ),
        "D": NodeModel("D", {"id": "D"}),
    }

    edges = [
        EdgeModel(
            "A",
            "B",
            "conditional",
            {
                "from": "A",
                "to": "B",
                "kind": "conditional",
                "priority": 1,
                "condition": {"expr": 'eq("flag","true")'},
            },
        ),
        EdgeModel(
            "A",
            "C",
            "conditional",
            {
                "from": "A",
                "to": "C",
                "kind": "conditional",
                "priority": 2,
                "condition": {"expr": 'eq("flag","false")'},
            },
        ),
        EdgeModel(
            "B",
            "D",
            "next",
            {"from": "B", "to": "D", "kind": "next"},
        ),
        EdgeModel(
            "C",
            "D",
            "next",
            {"from": "C", "to": "D", "kind": "next"},
        ),
    ]

    return CircuitModel(
        circuit_id="c_step90",
        nodes=nodes,
        edges=edges,
        entry_node_id="A",
        raw={"trace_enabled": True},
    )


def _make_executor(*, reg: PluginVersionRegistry, provider: _MockProvider):
    """Pipeline handler so runtime_adapter passes last_result as input_payload."""

    def core(node_id: str, node_raw: Dict[str, Any], core_input: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(core_input)

        if node_id == "A":
            desired_flag = str(node_raw.get("desired_flag"))
            provider.negotiate()
            tool_call = provider.generate_tool_call(desired_flag=desired_flag)
            tool = tool_call["tool"]
        else:
            tool = node_raw.get("tool")

        if tool is None:
            return out

        plugin_id = str(tool["plugin_id"])
        plugin_version = str(tool["plugin_version"])
        args = tool.get("args") or {}
        if not isinstance(args, dict):
            raise TypeError("tool.args must be dict")

        entry = reg.resolve(plugin_id=plugin_id, version=plugin_version)
        plugin = entry.factory()  # type: ignore[call-arg]
        result = plugin.run(**args)  # type: ignore[arg-type]

        # Flatten key results for condition_eval and later nodes.
        if "flag" in result:
            out["flag"] = str(result["flag"]).lower()
        if "result" in result:
            out["result"] = result["result"]
        out.setdefault("_tool_results", []).append({"plugin_id": plugin_id, "result": result})
        return out

    return {"core": core}


@pytest.mark.parametrize(
    "desired_flag, expected_branch, expected_result",
    [
        ("true", "B", 2),
        ("false", "C", 3),
    ],
)
def test_step90_multinode_conditional_e2e(desired_flag: str, expected_branch: str, expected_result: int):
    reg = _SpyRegistry()
    _register_plugins(reg)
    provider = _MockProvider()

    model = _make_model(desired_flag=desired_flag)
    executor = _make_executor(reg=reg, provider=provider)

    out = execute_circuit(model, executor)

    assert provider.negotiate_called is True
    assert provider.last_flag == desired_flag

    # Branch correctness
    trace = model.raw.get("trace")
    assert trace is not None
    visited = [nt.node_id for nt in trace.nodes]
    assert visited[0] == "A"
    assert expected_branch in visited
    assert ("B" in visited) is (expected_branch == "B")
    assert ("C" in visited) is (expected_branch == "C")
    assert visited[-1] == "D"

    # Condition trace on node A
    nt_a = trace.nodes[0]
    assert nt_a.condition_result is not None
    assert nt_a.selected_edge is not None
    assert nt_a.selected_edge.to_node_id == expected_branch
    assert nt_a.condition_result.value is True

    # Output correctness from chosen branch
    assert out["result"] == expected_result

    # Registry-based resolution used multiple times (A + chosen branch)
    assert reg.resolve_calls >= 2
