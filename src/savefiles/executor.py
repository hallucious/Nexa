"""Savefile Executor - Aligned with Nexa Architecture.

This module integrates savefile execution with existing Nexa subsystems:
- Uses ProviderRegistry (not duplicate provider execution)
- Uses PluginResult contract
- Respects Nexa execution invariants
- Maintains dependency-based DAG execution
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.contracts.savefile_format import EdgeSpec, Savefile, NodeSpec

if TYPE_CHECKING:
    from src.storage.execution_savefile_adapter import ExecutionSavefileAdapter
from src.contracts.provider_contract import ProviderRequest, ProviderResult
from src.platform.plugin_executor import execute_plugin_entry
from src.platform.provider_registry import ProviderRegistry


@dataclass
class NodeExecutionResult:
    """Result of executing a single node."""
    node_id: str
    status: str  # "success" | "failure"
    output: Any = None
    artifacts: List[Any] = field(default_factory=list)
    trace: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class SavefileExecutionTrace:
    """Complete execution trace for savefile."""
    run_id: str
    savefile_name: str
    status: str  # "success" | "failure"
    node_results: Dict[str, NodeExecutionResult]
    final_state: Dict[str, Any]
    all_artifacts: List[Any] = field(default_factory=list)
    started_at_ms: int = 0
    completed_at_ms: int = 0

    @property
    def duration_ms(self) -> int:
        return max(0, self.completed_at_ms - self.started_at_ms)


def resolve_input_value(
    path: str,
    state: Dict[str, Any],
    node_outputs: Dict[str, Any],
) -> Any:
    """Resolve input reference path to value."""
    if path.startswith("state.input."):
        key = path[len("state.input."):]
        return _get_nested(state.get("input", {}), key)
    elif path.startswith("state.working."):
        key = path[len("state.working."):]
        return _get_nested(state.get("working", {}), key)
    elif path.startswith("state.memory."):
        key = path[len("state.memory."):]
        return _get_nested(state.get("memory", {}), key)
    elif path.startswith("input."):
        key = path[len("input."):]
        return _get_nested(state.get("input", {}), key)
    elif path.startswith("node."):
        parts = path.split(".", 3)
        if len(parts) < 3:
            raise KeyError(f"Invalid node path: {path}")
        node_id = parts[1]
        if node_id not in node_outputs:
            raise KeyError(f"Node output not available: {node_id}")
        if len(parts) >= 4 and parts[2] == "output":
            output_key = parts[3]
        else:
            output_key = path.split(".", 2)[2]
        return _get_nested(node_outputs[node_id], output_key)
    else:
        raise KeyError(f"Invalid path format: {path}")


def _get_nested(data: Any, key: str) -> Any:
    """Get nested value using dot notation."""
    if not isinstance(data, dict):
        raise KeyError(f"Cannot access '{key}' on non-dict")

    parts = key.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            raise KeyError(f"Path '{key}' traverses non-dict at '{part}'")
        if part not in current:
            raise KeyError(f"Key not found: {key}")
        current = current[part]
    return current


def _set_nested(data: Dict[str, Any], key: str, value: Any) -> None:
    """Set nested value using dot notation."""
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def topological_sort(savefile: Savefile | "ExecutionSavefileAdapter") -> List[str]:
    """Return nodes in correct dependency order (full DAG execution)."""
    in_degree: Dict[str, int] = {node.id: 0 for node in savefile.circuit.nodes}
    graph: Dict[str, List[str]] = {node.id: [] for node in savefile.circuit.nodes}

    for edge in savefile.circuit.edges:
        graph[edge.from_node].append(edge.to_node)
        in_degree[edge.to_node] += 1

    queue = [node_id for node_id, deg in in_degree.items() if deg == 0]

    result = []

    while queue:
        current = queue.pop(0)
        result.append(current)

        for neighbor in graph.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(savefile.circuit.nodes):
        raise ValueError("Cycle detected or disconnected graph")

    return result


def execute_plugin_node(
    node: NodeSpec,
    savefile: Savefile | "ExecutionSavefileAdapter",
    state: Dict[str, Any],
    node_outputs: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute plugin node through the canonical plugin executor."""
    plugin_name = node.resource_ref.get("plugin")
    if not plugin_name:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error="No plugin specified in resource_ref",
        )

    if plugin_name not in savefile.resources.plugins:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Plugin '{plugin_name}' not found in resources",
        )

    plugin_resource = savefile.resources.plugins[plugin_name]

    try:
        inputs = {}
        for input_key, input_path in node.inputs.items():
            inputs[input_key] = resolve_input_value(input_path, state, node_outputs)
    except KeyError as e:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Input resolution failed: {e}",
        )

    try:
        plugin_result = execute_plugin_entry(
            plugin_name=plugin_name,
            entry=plugin_resource.entry,
            stage="CORE",
            timeout_ms=None,
            **inputs,
        )
    except Exception as e:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Plugin execution error: {e}",
        )

    if not plugin_result.success:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=plugin_result.error or "Plugin execution failed",
            trace={
                "reason_code": plugin_result.reason_code,
                "latency_ms": plugin_result.latency_ms,
                "stage": plugin_result.stage,
                "resource_usage": plugin_result.resource_usage or {},
                "plugin_trace": plugin_result.trace or {},
            },
        )

    return NodeExecutionResult(
        node_id=node.id,
        status="success",
        output=plugin_result.output,
        artifacts=list(plugin_result.artifacts),
        trace={
            "latency_ms": plugin_result.latency_ms,
            "stage": plugin_result.stage,
            "resource_usage": plugin_result.resource_usage or {},
            "plugin_trace": plugin_result.trace or {},
        },
    )


def execute_ai_node(
    node: NodeSpec,
    savefile: Savefile | "ExecutionSavefileAdapter",
    state: Dict[str, Any],
    node_outputs: Dict[str, Any],
    provider_registry: ProviderRegistry,
) -> NodeExecutionResult:
    """Execute AI node via provider registry."""
    prompt_ref = node.resource_ref.get("prompt")
    provider_ref = node.resource_ref.get("provider")

    if not prompt_ref or not provider_ref:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error="AI node requires both prompt and provider in resource_ref",
        )

    if prompt_ref not in savefile.resources.prompts:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Prompt '{prompt_ref}' not found in resources",
        )

    if provider_ref not in savefile.resources.providers:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Provider '{provider_ref}' not found in resources",
        )

    prompt_resource = savefile.resources.prompts[prompt_ref]
    provider_resource = savefile.resources.providers[provider_ref]

    try:
        inputs = {}
        for input_key, input_path in node.inputs.items():
            inputs[input_key] = resolve_input_value(input_path, state, node_outputs)
    except KeyError as e:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Input resolution failed: {e}",
        )

    rendered_prompt = prompt_resource.template
    for key, value in inputs.items():
        placeholder = f"{{{{{key}}}}}"
        rendered_prompt = rendered_prompt.replace(placeholder, str(value))

    try:
        provider = provider_registry.resolve(provider_ref)
    except KeyError as e:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Provider not found in registry: {e}",
        )

    provider_request = ProviderRequest(
        provider_id=provider_ref,
        prompt=rendered_prompt,
        context={},
        options=provider_resource.config,
        metadata={"node_id": node.id},
    )

    try:
        provider_result: ProviderResult = provider.execute(provider_request)
        trace_payload = getattr(provider_result, "trace", {}) or {}
        artifacts_payload = getattr(provider_result, "artifacts", []) or []
        if hasattr(provider_result, "output"):
            output_payload = provider_result.output
        else:
            output_payload = {"text": getattr(provider_result, "text", None)}

        if getattr(provider_result, "error", None):
            error_val = provider_result.error
            error_msg = error_val.message if hasattr(error_val, "message") else str(error_val)
            return NodeExecutionResult(
                node_id=node.id,
                status="failure",
                error=f"Provider error: {error_msg}",
                trace=trace_payload,
            )

    except Exception as e:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Provider execution failed: {e}",
        )

    return NodeExecutionResult(
        node_id=node.id,
        status="success",
        output=output_payload,
        artifacts=artifacts_payload,
        trace=trace_payload,
    )


def _child_output_source_map(child_circuit: Dict[str, Any]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for item in child_circuit.get("outputs", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("source"), str):
            mapping[item["name"]] = item["source"]
    return mapping




def _subcircuit_trace_summary(
    *,
    child_ref: str,
    child_trace: SavefileExecutionTrace,
    source_map: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    failed_nodes = [nid for nid, res in child_trace.node_results.items() if res.status == "failure"]
    warning_count = sum(
        len(res.trace.get("warnings", ()))
        for res in child_trace.node_results.values()
        if res.status == "success" and isinstance(res.trace, dict)
    )
    error_count = len(failed_nodes)
    artifact_refs = [f"artifact:{child_trace.run_id}:{idx}" for idx, _ in enumerate(child_trace.all_artifacts)]
    return {
        "child_circuit_ref": child_ref,
        "child_run_id": child_trace.run_id,
        "child_trace_ref": child_trace.run_id,
        "child_status": child_trace.status,
        "child_failed_nodes": failed_nodes,
        "child_artifact_count": len(child_trace.all_artifacts),
        "child_artifact_refs": artifact_refs,
        "child_warning_count": warning_count if child_trace.status == "success" else 0,
        "child_error_count": error_count,
        "child_duration_ms": child_trace.duration_ms,
        "child_node_statuses": {nid: res.status for nid, res in child_trace.node_results.items()},
        "child_output_provenance": dict(source_map or {}),
    }

def _resolve_bound_subcircuit_outputs(
    *,
    output_binding: Dict[str, Any],
    source_map: Dict[str, str],
    child_final_state: Dict[str, Any],
    child_node_outputs: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    bound_output: Dict[str, Any] = {}
    for parent_key, binding in output_binding.items():
        if not isinstance(binding, str) or not binding.startswith("child.output."):
            return None, f"Invalid subcircuit output binding target: {binding!r}"
        child_name = binding[len("child.output."):]
        source = source_map.get(child_name)
        if source is None:
            return None, f"Subcircuit binding references missing child output: {child_name}"
        try:
            bound_output[parent_key] = resolve_input_value(source, child_final_state, child_node_outputs)
        except Exception as exc:
            return None, f"Subcircuit output resolution failed for '{child_name}': {exc}"
    return bound_output, None

def execute_subcircuit_node(
    node: NodeSpec,
    savefile: Savefile | "ExecutionSavefileAdapter",
    state: Dict[str, Any],
    node_outputs: Dict[str, Any],
    provider_registry: ProviderRegistry,
    *,
    _depth: int = 0,
    _max_child_depth: Optional[int] = None,
) -> NodeExecutionResult:
    sub = node.execution.get("subcircuit", {})
    child_ref = sub.get("child_circuit_ref")
    if not isinstance(child_ref, str) or not child_ref.startswith("internal:"):
        return NodeExecutionResult(node_id=node.id, status="failure", error="Unsupported child_circuit_ref")

    name = child_ref.split(":", 1)[1]
    child_circuit = savefile.circuit.subcircuits.get(name)
    if not isinstance(child_circuit, dict):
        return NodeExecutionResult(node_id=node.id, status="failure", error=f"Child subcircuit not found: {child_ref}")

    runtime_policy = sub.get("runtime_policy", {}) if isinstance(sub.get("runtime_policy"), dict) else {}
    local_max_child_depth = int(runtime_policy.get("max_child_depth", 2))
    effective_max_child_depth = local_max_child_depth
    if _max_child_depth is not None:
        effective_max_child_depth = min(effective_max_child_depth, _max_child_depth)
    if _depth >= effective_max_child_depth:
        return NodeExecutionResult(node_id=node.id, status="failure", error="Subcircuit max depth exceeded")

    input_mapping = sub.get("input_mapping", {})
    child_input: Dict[str, Any] = {}
    try:
        for input_key, input_path in input_mapping.items():
            child_input[input_key] = resolve_input_value(input_path, state, node_outputs)
    except KeyError as e:
        return NodeExecutionResult(node_id=node.id, status="failure", error=f"Input resolution failed: {e}")

    child_nodes = [
        NodeSpec(
            id=n["id"],
            type=n.get("type"),
            resource_ref=dict(n.get("resource_ref", {})),
            inputs=dict(n.get("inputs", {})),
            outputs=dict(n.get("outputs", {})),
            kind=n.get("kind"),
            label=n.get("label"),
            execution=dict(n.get("execution", {})),
        )
        for n in child_circuit.get("nodes", [])
    ]
    child_edges = [
        EdgeSpec(
            from_node=e.get("from") or e.get("from_node"),
            to_node=e.get("to") or e.get("to_node"),
        )
        for e in child_circuit.get("edges", [])
    ]
    from src.contracts.savefile_format import CircuitSpec, Savefile as SavefileModel
    child_savefile = SavefileModel(
        meta=savefile.meta,
        circuit=CircuitSpec(
            entry=child_circuit.get("entry") or (child_nodes[0].id if child_nodes else ""),
            nodes=child_nodes,
            edges=child_edges,
            outputs=list(child_circuit.get("outputs", [])),
            subcircuits=dict(savefile.circuit.subcircuits),
        ),
        resources=savefile.resources,
        state=type(savefile.state)(input=child_input, working={}, memory={}),
        ui=savefile.ui,
    )

    child_trace = SavefileExecutor(provider_registry).execute(
        child_savefile,
        run_id=f"subcircuit:{node.id}:{name}",
        _depth=_depth + 1,
        _max_child_depth=effective_max_child_depth,
    )
    source_map = _child_output_source_map(child_circuit)
    trace_mode = str(runtime_policy.get("trace_mode", "summary"))
    trace_summary = _subcircuit_trace_summary(child_ref=child_ref, child_trace=child_trace, source_map=source_map)
    if trace_mode == "full":
        trace_summary["child_trace"] = child_trace

    if child_trace.status != "success":
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error="Child subcircuit execution failed",
            trace=trace_summary,
        )

    child_final_state = child_trace.final_state
    child_node_outputs = {
        nid: res.output for nid, res in child_trace.node_results.items() if res.status == "success"
    }

    bound_output, binding_error = _resolve_bound_subcircuit_outputs(
        output_binding=sub.get("output_binding", {}),
        source_map=source_map,
        child_final_state=child_final_state,
        child_node_outputs=child_node_outputs,
    )
    if binding_error is not None or bound_output is None:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=binding_error or "Subcircuit output binding failed",
            trace=trace_summary,
        )

    return NodeExecutionResult(
        node_id=node.id,
        status="success",
        output=bound_output,
        artifacts=list(child_trace.all_artifacts),
        trace=trace_summary,
    )


class SavefileExecutor:
    """Savefile executor aligned with Nexa architecture."""

    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry

    def execute(
        self,
        savefile: Savefile | "ExecutionSavefileAdapter",
        run_id: str = "savefile-run",
        *,
        _depth: int = 0,
        _max_child_depth: Optional[int] = None,
    ) -> SavefileExecutionTrace:
        """Execute savefile using Nexa subsystems."""
        state = {
            "input": copy.deepcopy(savefile.state.input),
            "working": copy.deepcopy(savefile.state.working),
            "memory": copy.deepcopy(savefile.state.memory),
        }

        node_outputs: Dict[str, Any] = {}
        node_results: Dict[str, NodeExecutionResult] = {}
        all_artifacts: List[Any] = []

        execution_order = topological_sort(savefile)

        for node_id in execution_order:
            node = next((n for n in savefile.circuit.nodes if n.id == node_id), None)
            if node is None:
                continue

            node_kind = node.node_kind
            if node_kind == "plugin":
                result = execute_plugin_node(
                    node=node,
                    savefile=savefile,
                    state=state,
                    node_outputs=node_outputs,
                )
            elif node_kind == "ai":
                result = execute_ai_node(
                    node, savefile, state, node_outputs, self.provider_registry
                )
            elif node_kind == "subcircuit":
                result = execute_subcircuit_node(
                    node,
                    savefile,
                    state,
                    node_outputs,
                    self.provider_registry,
                    _depth=_depth,
                    _max_child_depth=_max_child_depth,
                )
            else:
                result = NodeExecutionResult(
                    node_id=node_id,
                    status="failure",
                    error=f"Unknown node type: {node_kind}",
                )

            node_results[node_id] = result

            if result.artifacts:
                all_artifacts.extend(result.artifacts)

            if result.status == "success":
                node_outputs[node_id] = result.output or {}

                for output_key, state_path in node.outputs.items():
                    if state_path.startswith("state.working."):
                        key = state_path[len("state.working."):]
                        if isinstance(result.output, dict):
                            value = result.output.get(output_key)
                        else:
                            value = result.output

                        if value is not None:
                            _set_nested(state["working"], key, value)

        has_failure = any(r.status == "failure" for r in node_results.values())
        overall_status = "failure" if has_failure else "success"

        return SavefileExecutionTrace(
            run_id=run_id,
            savefile_name=savefile.meta.name,
            status=overall_status,
            node_results=node_results,
            final_state=state,
            all_artifacts=all_artifacts,
        )
