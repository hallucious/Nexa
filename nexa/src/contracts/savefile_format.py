"""Savefile Format v2.0 - Complete Executable Contract.

This module defines the canonical savefile structure for Nexa execution.

Root contract (required 5 sections):
- meta
- circuit
- resources
- state
- ui

The legacy savefile contract remains supported, but node/circuit structures are
extended so newer schemas such as SubcircuitNode can be represented without
breaking older savefile tests and callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# =========================================================
# META
# =========================================================

@dataclass
class SavefileMeta:
    """Savefile metadata."""
    name: str
    version: str
    description: Optional[str] = None


# =========================================================
# CIRCUIT
# =========================================================

@dataclass
class NodeSpec:
    """Node specification in circuit.

    Legacy canonical nodes use ``type`` + ``resource_ref``.
    Extended schemas may additionally use ``kind`` + ``execution``.
    """

    id: str
    type: Optional[str] = None  # legacy: "plugin" | "ai"
    resource_ref: Dict[str, str] = field(default_factory=dict)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    kind: Optional[str] = None
    label: Optional[str] = None
    execution: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_kind(self) -> str:
        kind = self.kind or self.type or "unknown"
        if kind == "provider":
            return "ai"
        return kind


@dataclass
class EdgeSpec:
    """Edge connecting two nodes."""
    from_node: str  # src_node_id
    to_node: str    # dst_node_id


@dataclass
class CircuitSpec:
    """Circuit topology."""
    entry: str  # entry node id
    nodes: List[NodeSpec]
    edges: List[EdgeSpec] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    subcircuits: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# =========================================================
# RESOURCES
# =========================================================

@dataclass
class PromptResource:
    """Prompt template resource."""
    template: str


@dataclass
class ProviderResource:
    """AI provider resource."""
    type: str  # "openai" | "anthropic" | "test" | etc
    model: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResource:
    """Plugin function resource."""
    entry: str  # "module.function"


@dataclass
class ResourcesSpec:
    """All resources referenced by nodes."""
    prompts: Dict[str, PromptResource] = field(default_factory=dict)
    providers: Dict[str, ProviderResource] = field(default_factory=dict)
    plugins: Dict[str, PluginResource] = field(default_factory=dict)


# =========================================================
# STATE
# =========================================================

@dataclass
class StateSpec:
    """Execution state embedded in savefile."""
    input: Dict[str, Any] = field(default_factory=dict)
    working: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# UI
# =========================================================

@dataclass
class UISpec:
    """UI layout metadata (execution-independent).
    
    This section contains visual editor metadata and layout information.
    It MUST NOT affect execution behavior.
    """
    layout: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# ROOT SAVEFILE
# =========================================================

@dataclass
class Savefile:
    """Root savefile structure - complete executable contract."""

    meta: SavefileMeta
    circuit: CircuitSpec
    resources: ResourcesSpec
    state: StateSpec
    ui: Optional[UISpec]
