"""Savefile Executor - Aligned with Nexa Architecture.

This module integrates savefile execution with existing Nexa subsystems:
- Uses ProviderRegistry (not duplicate provider execution)
- Uses PluginResult contract
- Respects Nexa execution invariants
- Maintains dependency-based DAG execution
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.contracts.savefile_format import Savefile, NodeSpec
from src.contracts.provider_contract import ProviderRequest, ProviderResult
from src.platform.plugin import Plugin, PluginResult, safe_execute_plugin
from src.platform.plugin_auto_loader import load_plugin_entry
from src.platform.plugin_result import normalize_plugin_result
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
    elif path.startswith("node."):
        parts = path.split(".", 2)
        if len(parts) < 3:
            raise KeyError(f"Invalid node path: {path}")
        node_id = parts[1]
        output_key = parts[2]
        if node_id not in node_outputs:
            raise KeyError(f"Node output not available: {node_id}")
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


def topological_sort(savefile: Savefile) -> List[str]:
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
    savefile: Savefile,
    state: Dict[str, Any],
    node_outputs: Dict[str, Any],
) -> NodeExecutionResult:
    """Execute plugin node."""
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
        plugin_func = load_plugin_entry(plugin_resource.entry)
    except Exception as e:
        return NodeExecutionResult(
            node_id=node.id,
            status="failure",
            error=f"Plugin load failed: {e}",
        )

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
        class _CallablePluginAdapter(Plugin):
            name = plugin_name

            def execute(self, **kwargs: Any) -> PluginResult:
                call_kwargs = dict(kwargs)
                call_kwargs.pop("stage", None)
                raw_result = plugin_func(**call_kwargs)
                if isinstance(raw_result, PluginResult):
                    return raw_result
                compat = normalize_plugin_result(raw_result)
                output = compat.output
                if isinstance(raw_result, dict) and output is None:
                    output = raw_result
                return PluginResult(
                    success=True,
                    output=output,
                    error=None,
                    latency_ms=0,
                    stage=kwargs.get("stage"),
                    resource_usage=None,
                )

        plugin_result = safe_execute_plugin(
            plugin=_CallablePluginAdapter(),
            timeout_ms=None,
            stage="CORE",
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
            },
        )

    return NodeExecutionResult(
        node_id=node.id,
        status="success",
        output=plugin_result.output,
        artifacts=[],
        trace={
            "latency_ms": plugin_result.latency_ms,
            "stage": plugin_result.stage,
            "resource_usage": plugin_result.resource_usage or {},
        },
    )


def execute_ai_node(
    node: NodeSpec,
    savefile: Savefile,
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

        if provider_result.error:
            return NodeExecutionResult(
                node_id=node.id,
                status="failure",
                error=f"Provider error: {provider_result.error.message}",
                trace=provider_result.trace or {},
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
        output=provider_result.output,
        artifacts=provider_result.artifacts or [],
        trace=provider_result.trace or {},
    )


class SavefileExecutor:
    """Savefile executor aligned with Nexa architecture."""

    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry

    def execute(
        self,
        savefile: Savefile,
        run_id: str = "savefile-run",
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

            if node.type == "plugin":
                result = execute_plugin_node(
                    node, savefile, state, node_outputs, self.plugin_loader
                )
            elif node.type == "ai":
                result = execute_ai_node(
                    node, savefile, state, node_outputs, self.provider_registry
                )
            else:
                result = NodeExecutionResult(
                    node_id=node_id,
                    status="failure",
                    error=f"Unknown node type: {node.type}",
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
