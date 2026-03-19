from __future__ import annotations

import json
from typing import Any, Dict

from src.contracts.nex_format import (
    CircuitMeta,
    EdgeSpec,
    ExecutionConfig,
    FlowRule,
    NexCircuit,
    NexFormat,
    NodeSpec,
    PluginSpec,
    PromptResource,
    ProviderResource,
    ResourceSpec,
    RetryConfig,
)


def _load_retry_policy(raw: Dict[str, Any]) -> Dict[str, RetryConfig]:
    return {
        node_id: RetryConfig(max_attempts=value["max_attempts"])
        for node_id, value in raw.items()
    }


def _load_resources(raw: Dict[str, Any]) -> ResourceSpec:
    prompts = {
        key: PromptResource(template=value["template"])
        for key, value in raw.get("prompts", {}).items()
    }
    providers = {
        key: ProviderResource(
            provider_type=value["provider_type"],
            model=value["model"],
            config=value.get("config", {}),
        )
        for key, value in raw.get("providers", {}).items()
    }
    return ResourceSpec(prompts=prompts, providers=providers)


def deserialize_nex(data: Dict[str, Any]) -> NexCircuit:
    """Convert dict data into NexCircuit dataclass tree."""
    return NexCircuit(
        format=NexFormat(**data["format"]),
        circuit=CircuitMeta(**data["circuit"]),
        nodes=[NodeSpec(**item) for item in data.get("nodes", [])],
        edges=[EdgeSpec(**item) for item in data.get("edges", [])],
        flow=[FlowRule(**item) for item in data.get("flow", [])],
        execution=ExecutionConfig(
            strict_determinism=data.get("execution", {}).get("strict_determinism", False),
            node_failure_policies=data.get("execution", {}).get("node_failure_policies", {}),
            node_fallback_map=data.get("execution", {}).get("node_fallback_map", {}),
            node_retry_policy=_load_retry_policy(
                data.get("execution", {}).get("node_retry_policy", {})
            ),
        ),
        resources=_load_resources(data.get("resources", {})),
        plugins=[PluginSpec(**item) for item in data.get("plugins", [])],
    )


def load_nex_file(file_path: str) -> NexCircuit:
    """Load a .nex JSON file and convert it into NexCircuit."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return deserialize_nex(data)
