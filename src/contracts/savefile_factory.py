from __future__ import annotations

"""Canonical Savefile Factory.

Official entry point for creating canonical executable savefiles with the
required explicit root sections:
- meta
- circuit
- resources
- state
- ui

This module reduces ad hoc Savefile construction and ensures the execution-
independent ``ui`` section is always materialized explicitly.
"""

import copy
from typing import Any, Dict, Iterable, Mapping, Sequence

from src.contracts.savefile_format import (
    CircuitSpec,
    EdgeSpec,
    NodeSpec,
    PluginResource,
    PromptResource,
    ProviderResource,
    ResourcesSpec,
    Savefile,
    SavefileMeta,
    StateSpec,
    UISpec,
)


def _deepcopy_dict(value: Mapping[str, Any] | None) -> Dict[str, Any]:
    if value is None:
        return {}
    return copy.deepcopy(dict(value))


def _materialize_node(node: NodeSpec | Mapping[str, Any]) -> NodeSpec:
    if isinstance(node, NodeSpec):
        return NodeSpec(
            id=node.id,
            type=node.type,
            resource_ref=_deepcopy_dict(node.resource_ref),
            inputs=_deepcopy_dict(node.inputs),
            outputs=_deepcopy_dict(node.outputs),
            kind=node.kind,
            label=node.label,
            execution=copy.deepcopy(node.execution),
        )
    return NodeSpec(
        id=str(node["id"]),
        type=str(node["type"]) if node.get("type") is not None else None,
        resource_ref=_deepcopy_dict(node.get("resource_ref")),
        inputs=_deepcopy_dict(node.get("inputs")),
        outputs=_deepcopy_dict(node.get("outputs")),
        kind=str(node.get("kind")) if node.get("kind") is not None else None,
        label=str(node.get("label")) if node.get("label") is not None else None,
        execution=copy.deepcopy(dict(node.get("execution", {}))),
    )


def _materialize_edge(edge: EdgeSpec | Mapping[str, Any]) -> EdgeSpec:
    if isinstance(edge, EdgeSpec):
        return EdgeSpec(from_node=edge.from_node, to_node=edge.to_node)
    from_node = edge.get("from") if isinstance(edge, Mapping) else None
    to_node = edge.get("to") if isinstance(edge, Mapping) else None
    return EdgeSpec(
        from_node=str(from_node or edge["from_node"]),
        to_node=str(to_node or edge["to_node"]),
    )


def _materialize_prompt_resource(value: PromptResource | Mapping[str, Any]) -> PromptResource:
    if isinstance(value, PromptResource):
        return PromptResource(template=value.template)
    return PromptResource(template=str(value["template"]))


def _materialize_provider_resource(value: ProviderResource | Mapping[str, Any]) -> ProviderResource:
    if isinstance(value, ProviderResource):
        return ProviderResource(
            type=value.type,
            model=value.model,
            config=_deepcopy_dict(value.config),
        )
    return ProviderResource(
        type=str(value["type"]),
        model=str(value["model"]),
        config=_deepcopy_dict(value.get("config")),
    )


def _materialize_plugin_resource(value: PluginResource | Mapping[str, Any]) -> PluginResource:
    if isinstance(value, PluginResource):
        return PluginResource(entry=value.entry)
    return PluginResource(entry=str(value["entry"]))


def create_savefile(
    *,
    name: str,
    version: str,
    entry: str,
    nodes: Sequence[NodeSpec | Mapping[str, Any]],
    description: str | None = None,
    edges: Sequence[EdgeSpec | Mapping[str, Any]] | None = None,
    prompts: Mapping[str, PromptResource | Mapping[str, Any]] | None = None,
    providers: Mapping[str, ProviderResource | Mapping[str, Any]] | None = None,
    plugins: Mapping[str, PluginResource | Mapping[str, Any]] | None = None,
    state_input: Mapping[str, Any] | None = None,
    state_working: Mapping[str, Any] | None = None,
    state_memory: Mapping[str, Any] | None = None,
    ui_layout: Mapping[str, Any] | None = None,
    ui_metadata: Mapping[str, Any] | None = None,
) -> Savefile:
    """Create canonical Savefile with explicit root sections.

    This factory always materializes ``resources``, ``state``, and ``ui`` even
    when they are empty. It reduces ad hoc savefile construction while keeping
    node/edge/resource payloads convenient to declare as either dataclass
    instances or plain dictionaries.
    """
    return Savefile(
        meta=SavefileMeta(name=name, version=version, description=description),
        circuit=CircuitSpec(
            entry=entry,
            nodes=[_materialize_node(node) for node in nodes],
            edges=[_materialize_edge(edge) for edge in (edges or [])],
        ),
        resources=ResourcesSpec(
            prompts={
                key: _materialize_prompt_resource(value)
                for key, value in (prompts or {}).items()
            },
            providers={
                key: _materialize_provider_resource(value)
                for key, value in (providers or {}).items()
            },
            plugins={
                key: _materialize_plugin_resource(value)
                for key, value in (plugins or {}).items()
            },
        ),
        state=StateSpec(
            input=_deepcopy_dict(state_input),
            working=_deepcopy_dict(state_working),
            memory=_deepcopy_dict(state_memory),
        ),
        ui=UISpec(
            layout=_deepcopy_dict(ui_layout),
            metadata=_deepcopy_dict(ui_metadata),
        ),
    )


def make_minimal_savefile(
    *,
    name: str,
    version: str,
    entry: str,
    node_type: str,
    resource_ref: Mapping[str, str],
    inputs: Mapping[str, str] | None = None,
    outputs: Mapping[str, str] | None = None,
    description: str | None = None,
    prompts: Mapping[str, PromptResource | Mapping[str, Any]] | None = None,
    providers: Mapping[str, ProviderResource | Mapping[str, Any]] | None = None,
    plugins: Mapping[str, PluginResource | Mapping[str, Any]] | None = None,
    state_input: Mapping[str, Any] | None = None,
    state_working: Mapping[str, Any] | None = None,
    state_memory: Mapping[str, Any] | None = None,
    ui_layout: Mapping[str, Any] | None = None,
    ui_metadata: Mapping[str, Any] | None = None,
) -> Savefile:
    """Create a minimal one-node canonical savefile.

    This is the easiest official path for fixtures, examples, and tests that
    need a valid canonical savefile without manually assembling dataclass
    sections.
    """
    return create_savefile(
        name=name,
        version=version,
        description=description,
        entry=entry,
        nodes=[
            {
                "id": entry,
                "type": node_type,
                "resource_ref": dict(resource_ref),
                "inputs": dict(inputs or {}),
                "outputs": dict(outputs or {}),
            }
        ],
        prompts=prompts,
        providers=providers,
        plugins=plugins,
        state_input=state_input,
        state_working=state_working,
        state_memory=state_memory,
        ui_layout=ui_layout,
        ui_metadata=ui_metadata,
    )
