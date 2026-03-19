from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from src.contracts.nex_format import (
    CircuitMeta,
    EdgeSpec,
    ExecutionConfig,
    FlowRule as NexFlowRule,
    NexCircuit,
    NexFormat,
    NodeSpec,
    PluginSpec,
    ResourceSpec,
    RetryConfig as NexRetryConfig,
)
from src.contracts.nex_validator import validate_nex
from src.engine.engine import Engine, RetryConfig as EngineRetryConfig
from src.engine.model import Channel, FlowRule as EngineFlowRule
from src.engine.types import FlowPolicy, NodeFailurePolicy

_NEX_META_KEY = "_nex_adapter"


def _node_specs_map(circuit: NexCircuit) -> Dict[str, Dict[str, Any]]:
    return {
        node.node_id: {
            "kind": node.kind,
            "prompt_ref": node.prompt_ref,
            "provider_ref": node.provider_ref,
            "plugin_refs": list(node.plugin_refs),
        }
        for node in circuit.nodes
    }


def _engine_meta_from_nex(circuit: NexCircuit) -> Dict[str, Any]:
    return {
        _NEX_META_KEY: {
            "format": asdict(circuit.format),
            "circuit": {
                "circuit_id": circuit.circuit.circuit_id,
                "name": circuit.circuit.name,
                "description": circuit.circuit.description,
            },
            "node_specs": _node_specs_map(circuit),
            "resources": asdict(circuit.resources),
            "plugins": [asdict(plugin) for plugin in circuit.plugins],
            "strict_determinism": circuit.execution.strict_determinism,
        }
    }


def build_engine_from_nex(circuit: NexCircuit) -> Engine:
    """Convert NexCircuit into Engine.

    This adapter intentionally reconstructs only the structural/runtime state that
    the current Engine datamodel can represent. Prompt/provider/plugin resources
    are preserved in engine.meta for reverse conversion.
    """
    validate_nex(circuit)

    channels: List[Channel] = [
        Channel(
            channel_id=edge.edge_id,
            src_node_id=edge.src_node_id,
            dst_node_id=edge.dst_node_id,
        )
        for edge in circuit.edges
    ]

    flow: List[EngineFlowRule] = [
        EngineFlowRule(
            rule_id=rule.rule_id,
            node_id=rule.node_id,
            policy=FlowPolicy(rule.policy),
        )
        for rule in circuit.flow
    ]

    node_failure_policies = {
        node_id: NodeFailurePolicy(policy)
        for node_id, policy in circuit.execution.node_failure_policies.items()
    }

    node_retry_policy = {
        node_id: EngineRetryConfig(max_attempts=retry.max_attempts)
        for node_id, retry in circuit.execution.node_retry_policy.items()
    }

    return Engine(
        entry_node_id=circuit.circuit.entry_node_id,
        node_ids=[node.node_id for node in circuit.nodes],
        channels=channels,
        flow=flow,
        meta=_engine_meta_from_nex(circuit),
        node_failure_policies=node_failure_policies,
        node_fallback_map=dict(circuit.execution.node_fallback_map),
        node_retry_policy=node_retry_policy,
    )


def build_nex_from_engine(engine: Engine) -> NexCircuit:
    """Convert Engine back into NexCircuit.

    If the Engine originated from a NexCircuit, rich metadata is restored from
    engine.meta[_NEX_META_KEY]. Otherwise, sane defaults are used.
    """
    adapter_meta: Dict[str, Any] = dict(engine.meta.get(_NEX_META_KEY, {}))

    format_meta = adapter_meta.get("format", {"kind": "nexa.circuit", "version": "1.0.0"})
    circuit_meta = adapter_meta.get("circuit", {})
    node_specs_map = adapter_meta.get("node_specs", {})
    resources_raw = adapter_meta.get("resources", {})
    plugins_raw = adapter_meta.get("plugins", [])
    strict_determinism = bool(adapter_meta.get("strict_determinism", False))

    nodes = []
    for node_id in engine.node_ids:
        spec = node_specs_map.get(node_id, {})
        nodes.append(
            NodeSpec(
                node_id=node_id,
                kind=spec.get("kind", "execution"),
                prompt_ref=spec.get("prompt_ref"),
                provider_ref=spec.get("provider_ref"),
                plugin_refs=list(spec.get("plugin_refs", [])),
            )
        )

    edges = [
        EdgeSpec(
            edge_id=channel.channel_id,
            src_node_id=channel.src_node_id,
            dst_node_id=channel.dst_node_id,
        )
        for channel in engine.channels
    ]

    flow = [
        NexFlowRule(
            rule_id=rule.rule_id,
            node_id=rule.node_id,
            policy=rule.policy.value,
        )
        for rule in engine.flow
    ]

    execution = ExecutionConfig(
        strict_determinism=strict_determinism,
        node_failure_policies={
            node_id: policy.value for node_id, policy in engine.node_failure_policies.items()
        },
        node_fallback_map=dict(engine.node_fallback_map),
        node_retry_policy={
            node_id: NexRetryConfig(max_attempts=retry.max_attempts)
            for node_id, retry in engine.node_retry_policy.items()
        },
    )

    resources = ResourceSpec(
        prompts={
            key: __import__("src.contracts.nex_format", fromlist=["PromptResource"]).PromptResource(**value)
            for key, value in resources_raw.get("prompts", {}).items()
        },
        providers={
            key: __import__("src.contracts.nex_format", fromlist=["ProviderResource"]).ProviderResource(**value)
            for key, value in resources_raw.get("providers", {}).items()
        },
    )

    plugins = [PluginSpec(**plugin) for plugin in plugins_raw]

    return NexCircuit(
        format=NexFormat(**format_meta),
        circuit=CircuitMeta(
            circuit_id=circuit_meta.get("circuit_id", engine.entry_node_id),
            name=circuit_meta.get("name", engine.entry_node_id),
            entry_node_id=engine.entry_node_id,
            description=circuit_meta.get("description"),
        ),
        nodes=nodes,
        edges=edges,
        flow=flow,
        execution=execution,
        resources=resources,
        plugins=plugins,
    )
