from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Callable, Dict, Iterable, Optional, Set


class CompiledResourceGraphError(ValueError):
    """Raised when an ExecutionConfig cannot be compiled into a valid resource graph."""


@dataclass(frozen=True)
class ResourceNode:
    """Single executable resource inside a Node."""

    id: str
    type: str
    reads: Set[str] = field(default_factory=set)
    writes: Set[str] = field(default_factory=set)
    executor: Optional[Callable[..., Any]] = None


@dataclass(frozen=True)
class CompiledResourceGraph:
    """Execution-ready representation derived from an ExecutionConfig."""

    resources: Dict[str, ResourceNode]
    dependencies: Dict[str, Set[str]]
    dependents: Dict[str, Set[str]]
    final_candidates: Set[str]


INPUT_DOMAIN_PREFIXES = ("input.", "system.", "node.")
NODE_OUTPUT_REFERENCE_PATTERN = re.compile(r"^[a-zA-Z0-9_]+\.output(?:\.[a-zA-Z0-9_]+)*$")


def _is_external_reference(read_key: str) -> bool:
    if read_key.startswith(INPUT_DOMAIN_PREFIXES):
        return True
    return bool(NODE_OUTPUT_REFERENCE_PATTERN.match(read_key))


def _as_string_mapping(value: Any, field_name: str) -> Dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CompiledResourceGraphError(f"{field_name} must be dict[str, str]")
    out: Dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise CompiledResourceGraphError(f"{field_name} must be dict[str, str]")
        out[key] = item
    return out


def _as_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CompiledResourceGraphError(f"{field_name} must be list[str]")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise CompiledResourceGraphError(f"{field_name} entries must be non-empty string")
        out.append(item)
    return out


def _normalize_prompt_resource(prompt_config: Dict[str, Any]) -> ResourceNode:
    prompt_id = prompt_config.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise CompiledResourceGraphError("prompt.prompt_id must be non-empty string")

    reads = set(_as_string_mapping(prompt_config.get("inputs"), "prompt.inputs").values())
    writes = {f"prompt.{prompt_id}.rendered"}
    return ResourceNode(id=f"prompt.{prompt_id}", type="prompt", reads=reads, writes=writes)


def _normalize_provider_resource(provider_config: Dict[str, Any], prompt_node: Optional[ResourceNode]) -> ResourceNode:
    provider_id = provider_config.get("provider_id")
    if not isinstance(provider_id, str) or not provider_id:
        raise CompiledResourceGraphError("provider.provider_id must be non-empty string")

    reads = set(_as_string_mapping(provider_config.get("inputs"), "provider.inputs").values())
    if not reads and prompt_node is not None:
        reads = set(prompt_node.writes)

    writes = {f"provider.{provider_id}.output"}
    writes.update(
        f"provider.{provider_id}.{field_name}"
        for field_name in _as_string_list(provider_config.get("output_fields"), "provider.output_fields")
    )
    return ResourceNode(id=f"provider.{provider_id}", type="provider", reads=reads, writes=writes)


def _normalize_plugin_resource(plugin_config: Dict[str, Any], index: int) -> ResourceNode:
    plugin_id = plugin_config.get("plugin_id")
    if not isinstance(plugin_id, str) or not plugin_id:
        raise CompiledResourceGraphError("plugin.plugin_id must be non-empty string")

    instance_id = plugin_config.get("id") or plugin_id
    if not isinstance(instance_id, str) or not instance_id:
        raise CompiledResourceGraphError("plugin.id must be non-empty string when present")

    reads = set(_as_string_mapping(plugin_config.get("inputs"), f"plugins[{index}].inputs").values())

    output_fields = _as_string_list(plugin_config.get("output_fields"), f"plugins[{index}].output_fields")
    if not output_fields:
        output_fields = ["result"]
    writes = {f"plugin.{plugin_id}.{field_name}" for field_name in output_fields}

    return ResourceNode(id=f"plugin.{instance_id}", type="plugin", reads=reads, writes=writes)


def _topological_order(resource_ids: Iterable[str], dependencies: Dict[str, Set[str]]) -> list[str]:
    pending = {resource_id: set(dependencies.get(resource_id, set())) for resource_id in resource_ids}
    ready = sorted(resource_id for resource_id, deps in pending.items() if not deps)
    order: list[str] = []

    while ready:
        current = ready.pop(0)
        order.append(current)
        for resource_id, deps in pending.items():
            if current in deps:
                deps.remove(current)
                if not deps and resource_id not in order and resource_id not in ready:
                    ready.append(resource_id)
        ready.sort()

    if len(order) != len(pending):
        unresolved = sorted(resource_id for resource_id in pending if resource_id not in order)
        raise CompiledResourceGraphError(
            "resource dependency cycle detected: " + ", ".join(unresolved)
        )
    return order


def compile_execution_config_to_graph(config: Dict[str, Any]) -> CompiledResourceGraph:
    if not isinstance(config, dict):
        raise CompiledResourceGraphError("execution config must be dict")

    resources: Dict[str, ResourceNode] = {}

    prompt_node: Optional[ResourceNode] = None
    prompt_config = config.get("prompt")
    if prompt_config is not None:
        if not isinstance(prompt_config, dict):
            raise CompiledResourceGraphError("prompt must be object")
        prompt_node = _normalize_prompt_resource(prompt_config)
        resources[prompt_node.id] = prompt_node

    provider_config = config.get("provider")
    if provider_config is not None:
        if not isinstance(provider_config, dict):
            raise CompiledResourceGraphError("provider must be object")
        provider_node = _normalize_provider_resource(provider_config, prompt_node)
        if provider_node.id in resources:
            raise CompiledResourceGraphError(f"duplicate resource id: {provider_node.id}")
        resources[provider_node.id] = provider_node

    plugin_configs = config.get("plugins") or []
    if not isinstance(plugin_configs, list):
        raise CompiledResourceGraphError("plugins must be list")
    for index, plugin_config in enumerate(plugin_configs):
        if not isinstance(plugin_config, dict):
            raise CompiledResourceGraphError("plugins entries must be object")
        plugin_node = _normalize_plugin_resource(plugin_config, index)
        if plugin_node.id in resources:
            raise CompiledResourceGraphError(f"duplicate resource id: {plugin_node.id}")
        resources[plugin_node.id] = plugin_node

    if not resources:
        raise CompiledResourceGraphError("execution config must declare at least one resource")

    produced_by_key: Dict[str, str] = {}
    all_reads: Set[str] = set()
    for resource in resources.values():
        for write_key in resource.writes:
            if write_key in produced_by_key:
                raise CompiledResourceGraphError(
                    f"duplicate write key detected: {write_key}"
                )
            produced_by_key[write_key] = resource.id
        all_reads.update(resource.reads)

    dependencies: Dict[str, Set[str]] = {resource_id: set() for resource_id in resources}
    dependents: Dict[str, Set[str]] = {resource_id: set() for resource_id in resources}

    for resource in resources.values():
        for read_key in resource.reads:
            producer_id = produced_by_key.get(read_key)
            if producer_id is not None:
                if producer_id == resource.id:
                    raise CompiledResourceGraphError(
                        f"resource cannot read its own write key: {resource.id} -> {read_key}"
                    )
                dependencies[resource.id].add(producer_id)
                dependents[producer_id].add(resource.id)
                continue
            if not _is_external_reference(read_key):
                raise CompiledResourceGraphError(
                    f"unresolved input reference: {resource.id} reads {read_key}"
                )

    _topological_order(resources.keys(), dependencies)

    final_candidates = set(produced_by_key.keys()) - all_reads
    if not final_candidates:
        raise CompiledResourceGraphError("compiled graph has no final output candidates")

    return CompiledResourceGraph(
        resources=resources,
        dependencies=dependencies,
        dependents=dependents,
        final_candidates=final_candidates,
    )