from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE
from src.storage.models.shared_sections import CircuitModel, MetaBase, ResourcesModel, StateModel


@dataclass(frozen=True)
class CommitSnapshotMeta(MetaBase):
    commit_id: str = ""
    source_working_save_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.storage_role != COMMIT_SNAPSHOT_ROLE:
            raise ValueError("CommitSnapshotMeta.storage_role must be 'commit_snapshot'")


@dataclass(frozen=True)
class CommitValidationModel:
    validation_result: str
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommitApprovalModel:
    approval_completed: bool
    approval_status: Optional[str] = None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommitLineageModel:
    parent_commit_id: Optional[str] = None
    source_working_save_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommitSnapshotModel:
    meta: CommitSnapshotMeta
    circuit: CircuitModel
    resources: ResourcesModel
    state: StateModel
    validation: CommitValidationModel
    approval: CommitApprovalModel
    lineage: CommitLineageModel


# ── Phase 5: Circuit Timeline View ───────────────────────────────────────────
# Produces a structural timeline projection from a CommitSnapshotModel so that
# the UI observability surface (trace_timeline_viewer, storage_panel) can expose
# circuit-level topology without depending on live execution data.


@dataclass(frozen=True)
class CircuitNodeTimelineEntry:
    """One node's slot in the circuit timeline."""
    node_id: str
    node_label: str
    position_index: int
    has_prompt: bool = False
    has_provider: bool = False
    has_plugin: bool = False
    dependency_count: int = 0
    dependent_count: int = 0


@dataclass(frozen=True)
class CircuitTimelineView:
    """Structural circuit timeline derived from a CommitSnapshotModel.

    Represents the topology of a committed circuit as an ordered sequence of
    node slots, enabling the UI to render a pre-execution timeline without
    requiring live trace data.
    """
    commit_id: str
    node_entries: Sequence[CircuitNodeTimelineEntry]
    total_node_count: int
    entry_node_id: Optional[str]
    output_node_ids: Sequence[str]
    edge_count: int
    validation_result: str
    approval_status: Optional[str]
    has_timeline: bool = True


def build_circuit_timeline_view(snapshot: CommitSnapshotModel) -> CircuitTimelineView:
    """Build a CircuitTimelineView from a CommitSnapshotModel.

    Derives node ordering from the circuit's edge topology (topological sort
    approximation via entry-point BFS).  Falls back to raw node list order
    when edge data is insufficient.
    """
    circuit = snapshot.circuit
    nodes: list[dict[str, Any]] = list(circuit.nodes or [])
    edges: list[dict[str, Any]] = list(circuit.edges or [])

    # Build adjacency maps for dependency counting
    dependents_of: dict[str, int] = {}   # node_id → count of nodes that depend on it
    dependencies_of: dict[str, int] = {}  # node_id → count of its own dependencies
    for edge in edges:
        src = str(edge.get("source") or edge.get("from") or "")
        tgt = str(edge.get("target") or edge.get("to") or "")
        if src:
            dependents_of[src] = dependents_of.get(src, 0) + 1
        if tgt:
            dependencies_of[tgt] = dependencies_of.get(tgt, 0) + 1

    # BFS ordering from entry node
    entry_node_id: Optional[str] = circuit.entry or None
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        src = str(edge.get("source") or edge.get("from") or "")
        tgt = str(edge.get("target") or edge.get("to") or "")
        if src and tgt:
            adjacency.setdefault(src, []).append(tgt)

    ordered_ids: list[str] = []
    visited: set[str] = set()
    queue: list[str] = [entry_node_id] if entry_node_id else []
    for node in nodes:
        nid = str(node.get("id") or "")
        if nid and nid not in queue:
            queue.append(nid)
    for nid in queue:
        if nid in visited:
            continue
        visited.add(nid)
        ordered_ids.append(nid)
        for neighbour in adjacency.get(nid, []):
            if neighbour not in visited:
                queue.append(neighbour)

    node_map: dict[str, dict[str, Any]] = {
        str(n.get("id") or ""): n for n in nodes if n.get("id")
    }

    entries: list[CircuitNodeTimelineEntry] = []
    for idx, nid in enumerate(ordered_ids):
        raw = node_map.get(nid, {})
        label = str(raw.get("label") or raw.get("name") or nid)
        resources = raw.get("resources") or {}
        entries.append(CircuitNodeTimelineEntry(
            node_id=nid,
            node_label=label,
            position_index=idx,
            has_prompt=bool(resources.get("prompt") or raw.get("prompt")),
            has_provider=bool(resources.get("provider") or raw.get("provider")),
            has_plugin=bool(resources.get("plugin") or raw.get("plugin")),
            dependency_count=dependencies_of.get(nid, 0),
            dependent_count=dependents_of.get(nid, 0),
        ))

    output_node_ids: list[str] = []
    for out in (circuit.outputs or []):
        if isinstance(out, dict) and out.get("node_id"):
            output_node_ids.append(str(out["node_id"]))
        elif isinstance(out, str):
            output_node_ids.append(out)

    return CircuitTimelineView(
        commit_id=snapshot.meta.commit_id,
        node_entries=tuple(entries),
        total_node_count=len(entries),
        entry_node_id=entry_node_id,
        output_node_ids=tuple(output_node_ids),
        edge_count=len(edges),
        validation_result=snapshot.validation.validation_result,
        approval_status=snapshot.approval.approval_status,
        has_timeline=True,
    )
