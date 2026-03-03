from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.circuit.model import CircuitModel, NodeModel, EdgeModel
from src.circuit.runtime_adapter import execute_circuit
from src.circuit.node_execution import run_node_pipeline

from src.platform.plugin_version_registry import (
    PluginEntry,
    PluginManifestV1,
    PluginRequires,
    PluginVersionRegistry,
)


# Step88: "symbolic first full integration" (B-structure) proof-of-execution
# - Circuit execution (single node)
# - Prompt render injection (via PromptRegistryLike)
# - Provider negotiate + generate tool-call JSON
# - Plugin registry resolve + plugin.run()
# - Trace enabled on circuit model


class _DoublePlugin:
    def run(self, *, x: int) -> Dict[str, Any]:
        return {"result": x * 2}


class _SpyRegistry(PluginVersionRegistry):
    def __init__(self) -> None:
        super().__init__()
        self.resolve_called: bool = False
        self.last_resolve: Optional[Dict[str, str]] = None

    def resolve(self, *, plugin_id: str, version: str) -> PluginEntry:  # type: ignore[override]
        self.resolve_called = True
        self.last_resolve = {"plugin_id": plugin_id, "version": version}
        return super().resolve(plugin_id=plugin_id, version=version)


@dataclass(frozen=True)
class _PromptSpec:
    prompt_id: str
    version: str
    template: str

    def validate(self, variables: Dict[str, Any]) -> None:
        if not isinstance(variables, dict):
            raise TypeError("variables must be dict")

    def render(self, *, variables: Dict[str, Any]) -> str:
        # minimal deterministic render
        rendered = self.template
        for k, v in variables.items():
            rendered = rendered.replace("{{" + str(k) + "}}", str(v))
        return rendered

    @property
    def prompt_hash(self) -> str:
        import hashlib

        h = hashlib.sha256()
        h.update((self.prompt_id + ":" + self.version + ":" + self.template).encode("utf-8"))
        return h.hexdigest()


class _PromptRegistry:
    def __init__(self, spec: _PromptSpec) -> None:
        self._spec = spec

    def get(self, prompt_id: str) -> _PromptSpec:
        if prompt_id != self._spec.prompt_id:
            raise KeyError(prompt_id)
        return self._spec


class _MockProvider:
    def __init__(self) -> None:
        self.negotiate_called: bool = False
        self.last_prompt: Optional[str] = None

    def negotiate(self) -> None:
        self.negotiate_called = True

    def generate(self, *, prompt: str) -> Dict[str, Any]:
        self.last_prompt = prompt
        # Step88 internal tool-call shape (test-only)
        return {"tool": {"plugin_id": "math_double", "plugin_version": "1.0.0", "args": {"x": 3}}}


def test_step88_symbolic_full_integration_proof():
    # --- Plugin registry ---
    reg = _SpyRegistry()
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

    # --- Prompt registry ---
    prompt_spec = _PromptSpec(prompt_id="p1", version="1.0.0", template="Compute double of {{x}}")
    prompt_registry = _PromptRegistry(prompt_spec)

    # --- Provider ---
    provider = _MockProvider()

    # --- Circuit model: single node ---
    n1 = NodeModel(
        id="n1",
        raw={
            "prompt_id": "p1",
            "prompt_variables": {"x": 3},
        },
    )

    model = CircuitModel(
        circuit_id="c_step88",
        nodes={"n1": n1},
        edges=[],
        entry_node_id="n1",
        raw={"trace_enabled": True},
    )

    # --- Engine-executor callable (bridges circuit -> node pipeline with prompt injection) ---
    def engine_executor(node_id: str, node_raw: Dict[str, Any]) -> Dict[str, Any]:
        def _core(_node_id: str, _node_raw: Dict[str, Any], core_input: Dict[str, Any]) -> Dict[str, Any]:
            # 1) Provider negotiate + generate tool-call
            provider.negotiate()
            tool_call = provider.generate(prompt=str(core_input.get("__rendered_prompt__", "")))

            # 2) Resolve plugin via registry and execute
            tool = tool_call["tool"]
            plugin_id = str(tool["plugin_id"])
            plugin_version = str(tool["plugin_version"])
            args = tool.get("args") or {}
            if not isinstance(args, dict):
                raise TypeError("tool.args must be dict")

            entry = reg.resolve(plugin_id=plugin_id, version=plugin_version)
            plugin = entry.factory()  # type: ignore[call-arg]
            result = plugin.run(**args)  # type: ignore[arg-type]

            # 3) Return enriched output (context)
            out = dict(core_input)
            out["tool_result"] = result
            return out

        return run_node_pipeline(
            node_id=node_id,
            node_raw=node_raw,
            input_payload={},
            handler=_core,
            prompt_registry=prompt_registry,
        )

    # --- Execute circuit ---
    out = execute_circuit(model, engine_executor)

    # --- Assertions: symbolic first integration proof ---
    assert provider.negotiate_called is True
    assert provider.last_prompt == "Compute double of 3"

    assert reg.resolve_called is True
    assert reg.last_resolve == {"plugin_id": "math_double", "version": "1.0.0"}

    assert out["tool_result"]["result"] == 6

    # Trace created and contains the node entry/exit
    trace = model.raw.get("trace")
    assert trace is not None
    assert getattr(trace, "circuit_id", None) == "c_step88"
    assert len(getattr(trace, "nodes", [])) == 1
    assert getattr(trace.nodes[0], "node_id", None) == "n1"
