from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import WorkingSaveModel


@dataclass(frozen=True)
class ExecutionMeta:
    name: str
    version: str
    description: Optional[str] = None


@dataclass(frozen=True)
class ExecutionNode:
    id: str
    resource_ref: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    type: Optional[str] = None
    kind: Optional[str] = None
    label: Optional[str] = None
    execution: dict[str, Any] = field(default_factory=dict)

    @property
    def node_kind(self) -> str:
        kind = self.kind or self.type or "unknown"
        if kind == "provider":
            return "ai"
        return kind


@dataclass(frozen=True)
class ExecutionEdge:
    from_node: str
    to_node: str


@dataclass(frozen=True)
class ExecutionCircuit:
    entry: str
    nodes: list[ExecutionNode]
    edges: list[ExecutionEdge] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    subcircuits: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPromptResource:
    template: str


@dataclass(frozen=True)
class ExecutionProviderResource:
    type: str
    model: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPluginResource:
    entry: str


@dataclass(frozen=True)
class ExecutionResources:
    prompts: dict[str, ExecutionPromptResource] = field(default_factory=dict)
    providers: dict[str, ExecutionProviderResource] = field(default_factory=dict)
    plugins: dict[str, ExecutionPluginResource] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionState:
    input: dict[str, Any] = field(default_factory=dict)
    working: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionUI:
    layout: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionSavefileAdapter:
    meta: ExecutionMeta
    circuit: ExecutionCircuit
    resources: ExecutionResources
    state: ExecutionState
    ui: ExecutionUI


def _node_from_mapping(raw_node: dict[str, Any]) -> ExecutionNode:
    node_id = raw_node.get("id") or raw_node.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ValueError("Execution adapter node is missing a valid id")
    return ExecutionNode(
        id=node_id,
        type=raw_node.get("type"),
        kind=raw_node.get("kind"),
        label=raw_node.get("label"),
        resource_ref=dict(raw_node.get("resource_ref", {})),
        inputs=dict(raw_node.get("inputs", {})),
        outputs=dict(raw_node.get("outputs", {})),
        execution=dict(raw_node.get("execution", {})),
    )


def _execution_circuit_from_shared_model(circuit: CircuitModel) -> ExecutionCircuit:
    entry = circuit.entry
    if not entry and circuit.nodes:
        first = circuit.nodes[0]
        entry = first.get("id") or first.get("node_id")
    return ExecutionCircuit(
        entry=str(entry or ""),
        nodes=[_node_from_mapping(node) for node in circuit.nodes],
        edges=[
            ExecutionEdge(
                from_node=str(edge.get("from") or edge.get("from_node") or edge.get("source") or ""),
                to_node=str(edge.get("to") or edge.get("to_node") or edge.get("target") or ""),
            )
            for edge in circuit.edges
        ],
        outputs=list(circuit.outputs),
        subcircuits=dict(circuit.subcircuits),
    )


def _execution_resources_from_shared_model(resources: ResourcesModel) -> ExecutionResources:
    return ExecutionResources(
        prompts={
            key: ExecutionPromptResource(template=str((value or {}).get("template", "")))
            for key, value in resources.prompts.items()
        },
        providers={
            key: ExecutionProviderResource(
                type=str((value or {}).get("type", "")),
                model=str((value or {}).get("model", "")),
                config=dict((value or {}).get("config", {})),
            )
            for key, value in resources.providers.items()
        },
        plugins={
            key: ExecutionPluginResource(entry=str((value or {}).get("entry", "")))
            for key, value in resources.plugins.items()
        },
    )


def _execution_state_from_shared_model(state: StateModel) -> ExecutionState:
    return ExecutionState(
        input=dict(state.input),
        working=dict(state.working),
        memory=dict(state.memory),
    )


def execution_savefile_from_working_save_model(model: WorkingSaveModel) -> ExecutionSavefileAdapter:
    return ExecutionSavefileAdapter(
        meta=ExecutionMeta(
            name=model.meta.name or model.meta.working_save_id,
            version=model.meta.format_version,
            description=model.meta.description,
        ),
        circuit=_execution_circuit_from_shared_model(model.circuit),
        resources=_execution_resources_from_shared_model(model.resources),
        state=_execution_state_from_shared_model(model.state),
        ui=ExecutionUI(layout=dict(model.ui.layout), metadata=dict(model.ui.metadata)),
    )


def execution_savefile_from_commit_snapshot_model(model: CommitSnapshotModel) -> ExecutionSavefileAdapter:
    metadata = {
        "storage_role": "commit_snapshot",
        "commit_id": model.meta.commit_id,
        "source_working_save_id": model.meta.source_working_save_id,
    }
    if model.approval.approval_status:
        metadata["approval_status"] = model.approval.approval_status
    return ExecutionSavefileAdapter(
        meta=ExecutionMeta(
            name=model.meta.name or model.meta.commit_id,
            version=model.meta.format_version,
            description=model.meta.description,
        ),
        circuit=_execution_circuit_from_shared_model(model.circuit),
        resources=_execution_resources_from_shared_model(model.resources),
        state=_execution_state_from_shared_model(model.state),
        ui=ExecutionUI(layout={}, metadata=metadata),
    )


def execution_savefile_from_loaded_nex_artifact(loaded: LoadedNexArtifact) -> ExecutionSavefileAdapter:
    if loaded.parsed_model is None:
        raise ValueError("Cannot adapt rejected public .nex artifact to an execution adapter")
    if isinstance(loaded.parsed_model, WorkingSaveModel):
        return execution_savefile_from_working_save_model(loaded.parsed_model)
    if isinstance(loaded.parsed_model, CommitSnapshotModel):
        return execution_savefile_from_commit_snapshot_model(loaded.parsed_model)
    raise TypeError(f"Unsupported parsed_model type: {type(loaded.parsed_model).__name__}")


__all__ = [
    "ExecutionCircuit",
    "ExecutionEdge",
    "ExecutionMeta",
    "ExecutionNode",
    "ExecutionPluginResource",
    "ExecutionPromptResource",
    "ExecutionProviderResource",
    "ExecutionResources",
    "ExecutionSavefileAdapter",
    "ExecutionState",
    "ExecutionUI",
    "execution_savefile_from_commit_snapshot_model",
    "execution_savefile_from_loaded_nex_artifact",
    "execution_savefile_from_working_save_model",
]
