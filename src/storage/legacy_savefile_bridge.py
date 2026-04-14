from __future__ import annotations

import re
from pathlib import Path
from typing import Any

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
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.validators.shared_validator import load_nex


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "workspace"


def default_working_save_id(name: str | None, *, fallback: str = "workspace") -> str:
    base = _slugify(name or fallback)
    return f"{base}-draft"


def _node_spec_from_mapping(raw_node: dict[str, Any]) -> NodeSpec:
    node_id = raw_node.get("id") or raw_node.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ValueError("Public .nex node is missing a valid id")
    return NodeSpec(
        id=node_id,
        type=raw_node.get("type"),
        resource_ref=dict(raw_node.get("resource_ref", {})),
        inputs=dict(raw_node.get("inputs", {})),
        outputs=dict(raw_node.get("outputs", {})),
        kind=raw_node.get("kind"),
        label=raw_node.get("label"),
        execution=dict(raw_node.get("execution", {})),
    )


def _legacy_circuit_from_shared_model(circuit: CircuitModel) -> CircuitSpec:
    entry = circuit.entry
    if not entry and circuit.nodes:
        first = circuit.nodes[0]
        entry = first.get("id") or first.get("node_id")
    return CircuitSpec(
        entry=str(entry or ""),
        nodes=[_node_spec_from_mapping(node) for node in circuit.nodes],
        edges=[
            EdgeSpec(
                from_node=str(edge.get("from") or edge.get("from_node") or edge.get("source") or ""),
                to_node=str(edge.get("to") or edge.get("to_node") or edge.get("target") or ""),
            )
            for edge in circuit.edges
        ],
        outputs=list(circuit.outputs),
        subcircuits=dict(circuit.subcircuits),
    )


def _legacy_resources_from_shared_model(resources: ResourcesModel) -> ResourcesSpec:
    return ResourcesSpec(
        prompts={key: PromptResource(template=str((value or {}).get("template", ""))) for key, value in resources.prompts.items()},
        providers={
            key: ProviderResource(
                type=str((value or {}).get("type", "")),
                model=str((value or {}).get("model", "")),
                config=dict((value or {}).get("config", {})),
            )
            for key, value in resources.providers.items()
        },
        plugins={key: PluginResource(entry=str((value or {}).get("entry", ""))) for key, value in resources.plugins.items()},
    )


def _legacy_state_from_shared_model(state: StateModel) -> StateSpec:
    return StateSpec(
        input=dict(state.input),
        working=dict(state.working),
        memory=dict(state.memory),
    )


def savefile_from_working_save_model(model: WorkingSaveModel) -> Savefile:
    return Savefile(
        meta=SavefileMeta(
            name=model.meta.name or model.meta.working_save_id,
            version=model.meta.format_version,
            description=model.meta.description,
        ),
        circuit=_legacy_circuit_from_shared_model(model.circuit),
        resources=_legacy_resources_from_shared_model(model.resources),
        state=_legacy_state_from_shared_model(model.state),
        ui=UISpec(layout=dict(model.ui.layout), metadata=dict(model.ui.metadata)),
    )


def savefile_from_commit_snapshot_model(model: CommitSnapshotModel) -> Savefile:
    metadata = {
        "storage_role": "commit_snapshot",
        "commit_id": model.meta.commit_id,
        "source_working_save_id": model.meta.source_working_save_id,
    }
    if model.approval.approval_status:
        metadata["approval_status"] = model.approval.approval_status
    return Savefile(
        meta=SavefileMeta(
            name=model.meta.name or model.meta.commit_id,
            version=model.meta.format_version,
            description=model.meta.description,
        ),
        circuit=_legacy_circuit_from_shared_model(model.circuit),
        resources=_legacy_resources_from_shared_model(model.resources),
        state=_legacy_state_from_shared_model(model.state),
        ui=UISpec(layout={}, metadata=metadata),
    )


def savefile_from_loaded_nex_artifact(loaded: LoadedNexArtifact) -> Savefile:
    if loaded.parsed_model is None:
        raise ValueError("Cannot adapt rejected public .nex artifact to legacy Savefile")
    if isinstance(loaded.parsed_model, WorkingSaveModel):
        return savefile_from_working_save_model(loaded.parsed_model)
    if isinstance(loaded.parsed_model, CommitSnapshotModel):
        return savefile_from_commit_snapshot_model(loaded.parsed_model)
    raise TypeError(f"Unsupported parsed_model type: {type(loaded.parsed_model).__name__}")


def load_public_nex_as_legacy_savefile(source: str | Path | dict[str, Any]) -> Savefile:
    loaded = load_nex(source)
    return savefile_from_loaded_nex_artifact(loaded)


def _shared_circuit_from_legacy_savefile(savefile: Savefile) -> CircuitModel:
    return CircuitModel(
        nodes=[
            {
                "id": node.id,
                **({"type": node.type} if node.type is not None else {}),
                **({"kind": node.kind} if node.kind is not None else {}),
                **({"label": node.label} if node.label is not None else {}),
                "resource_ref": dict(node.resource_ref),
                "inputs": dict(node.inputs),
                "outputs": dict(node.outputs),
                **({"execution": dict(node.execution)} if node.execution else {}),
            }
            for node in savefile.circuit.nodes
        ],
        edges=[{"from": edge.from_node, "to": edge.to_node} for edge in savefile.circuit.edges],
        entry=savefile.circuit.entry,
        outputs=list(savefile.circuit.outputs),
        subcircuits=dict(savefile.circuit.subcircuits),
    )


def _shared_resources_from_legacy_savefile(savefile: Savefile) -> ResourcesModel:
    return ResourcesModel(
        prompts={key: {"template": value.template} for key, value in savefile.resources.prompts.items()},
        providers={
            key: {"type": value.type, "model": value.model, "config": dict(value.config)}
            for key, value in savefile.resources.providers.items()
        },
        plugins={key: {"entry": value.entry} for key, value in savefile.resources.plugins.items()},
    )


def _shared_state_from_legacy_savefile(savefile: Savefile) -> StateModel:
    return StateModel(
        input=dict(savefile.state.input),
        working=dict(savefile.state.working),
        memory=dict(savefile.state.memory),
    )


def working_save_model_from_legacy_savefile(
    savefile: Savefile,
    *,
    working_save_id: str | None = None,
    format_version: str | None = None,
) -> WorkingSaveModel:
    resolved_id = working_save_id or default_working_save_id(savefile.meta.name)
    ui = savefile.ui or UISpec(layout={}, metadata={})
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version=format_version or savefile.meta.version or "1.0.0",
            storage_role="working_save",
            working_save_id=resolved_id,
            name=savefile.meta.name,
            description=savefile.meta.description,
        ),
        circuit=_shared_circuit_from_legacy_savefile(savefile),
        resources=_shared_resources_from_legacy_savefile(savefile),
        state=_shared_state_from_legacy_savefile(savefile),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout=dict(ui.layout), metadata=dict(ui.metadata)),
    )


__all__ = [
    "default_working_save_id",
    "load_public_nex_as_legacy_savefile",
    "savefile_from_working_save_model",
    "savefile_from_commit_snapshot_model",
    "savefile_from_loaded_nex_artifact",
    "working_save_model_from_legacy_savefile",
]
