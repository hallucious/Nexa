from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# =========================================================
# 1. FORMAT
# =========================================================

@dataclass
class NexFormat:
    kind: str  # "nexa.circuit"
    version: str  # "1.0.0"


# =========================================================
# 2. CIRCUIT
# =========================================================

@dataclass
class CircuitMeta:
    circuit_id: str
    name: str
    entry_node_id: str
    description: Optional[str] = None


# =========================================================
# 3. NODE
# =========================================================

@dataclass
class NodeSpec:
    node_id: str
    kind: str  # execution / decision / etc
    prompt_ref: Optional[str] = None
    provider_ref: Optional[str] = None
    plugin_refs: List[str] = field(default_factory=list)


# =========================================================
# 4. EDGE
# =========================================================

@dataclass
class EdgeSpec:
    edge_id: str
    src_node_id: str
    dst_node_id: str


# =========================================================
# 5. FLOW POLICY
# =========================================================

@dataclass
class FlowRule:
    rule_id: str
    node_id: str
    policy: str  # ALL_SUCCESS / ANY_SUCCESS / etc


# =========================================================
# 6. EXECUTION CONFIG
# =========================================================

@dataclass
class RetryConfig:
    max_attempts: int


@dataclass
class ExecutionConfig:
    strict_determinism: bool = False
    node_failure_policies: Dict[str, str] = field(default_factory=dict)
    node_fallback_map: Dict[str, str] = field(default_factory=dict)
    node_retry_policy: Dict[str, RetryConfig] = field(default_factory=dict)


# =========================================================
# 7. RESOURCES
# =========================================================

@dataclass
class PromptResource:
    template: str


@dataclass
class ProviderResource:
    provider_type: str
    model: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceSpec:
    prompts: Dict[str, PromptResource] = field(default_factory=dict)
    providers: Dict[str, ProviderResource] = field(default_factory=dict)


# =========================================================
# 8. PLUGIN
# =========================================================

@dataclass
class PluginSpec:
    plugin_id: str
    version: Optional[str] = None
    required: bool = True


# =========================================================
# 9. ROOT STRUCTURE
# =========================================================

@dataclass
class NexCircuit:
    format: NexFormat
    circuit: CircuitMeta
    nodes: List[NodeSpec]
    edges: List[EdgeSpec]
    flow: List[FlowRule]
    execution: ExecutionConfig
    resources: ResourceSpec
    plugins: List[PluginSpec]
