from __future__ import annotations

from dataclasses import replace
from typing import Any

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel


def unwrap_beginner_source(source: Any) -> Any:
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def beginner_ui_metadata(source: Any) -> dict[str, Any]:
    source = unwrap_beginner_source(source)
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}



def build_beginner_first_success_completion_metadata_patch(
    *,
    run_id: str | None = None,
    output_ref: str | None = None,
    artifact_ref: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "beginner_first_success_achieved": True,
        "advanced_surfaces_unlocked": True,
        "beginner_current_step": "read_result",
    }
    if run_id:
        patch["beginner_first_success_run_id"] = run_id
    if output_ref:
        patch["beginner_first_success_output_ref"] = output_ref
    if artifact_ref:
        patch["beginner_first_success_artifact_ref"] = artifact_ref
    if completed_at:
        patch["beginner_first_success_completed_at"] = completed_at
    return patch


def apply_beginner_first_success_completion(
    source: WorkingSaveModel,
    *,
    run_id: str | None = None,
    output_ref: str | None = None,
    artifact_ref: str | None = None,
    completed_at: str | None = None,
) -> WorkingSaveModel:
    source = unwrap_beginner_source(source)
    if not isinstance(source, WorkingSaveModel):
        raise TypeError("beginner first-success completion can only be applied to a WorkingSaveModel")
    metadata = dict(source.ui.metadata or {})
    metadata.update(
        build_beginner_first_success_completion_metadata_patch(
            run_id=run_id,
            output_ref=output_ref,
            artifact_ref=artifact_ref,
            completed_at=completed_at,
        )
    )
    return replace(source, ui=replace(source.ui, metadata=metadata))


def explicit_beginner_first_success_achieved(*sources: Any) -> bool:
    return any(
        bool(beginner_ui_metadata(source).get("beginner_first_success_achieved"))
        for source in sources
    )


def explicit_advanced_surface_unlock_requested(*sources: Any) -> bool:
    for source in sources:
        metadata = beginner_ui_metadata(source)
        if bool(metadata.get("advanced_surfaces_unlocked")):
            return True
        if bool(metadata.get("advanced_mode_requested")):
            return True
        if str(metadata.get("user_mode") or "").lower() == "advanced":
            return True
    return False


def beginner_surface_active(*sources: Any) -> bool:
    has_working_save = False
    for source in sources:
        source = unwrap_beginner_source(source)
        if isinstance(source, WorkingSaveModel):
            has_working_save = True
    return has_working_save and not explicit_advanced_surface_unlock_requested(*sources)


def beginner_advanced_surfaces_unlocked(*sources: Any) -> bool:
    if not beginner_surface_active(*sources):
        return True
    if explicit_advanced_surface_unlock_requested(*sources):
        return True
    return explicit_beginner_first_success_achieved(*sources)


def beginner_language_enabled(*sources: Any) -> bool:
    return beginner_surface_active(*sources) and not beginner_advanced_surfaces_unlocked(*sources)


def return_use_ready(source: Any) -> bool:
    source = unwrap_beginner_source(source)
    if isinstance(source, ExecutionRecordModel):
        return True
    return explicit_beginner_first_success_achieved(source)


def terminal_execution_record_view(source: Any) -> bool:
    source = unwrap_beginner_source(source)
    return isinstance(source, ExecutionRecordModel) and source.meta.status in {"completed", "partial"}


__all__ = [
    "unwrap_beginner_source",
    "beginner_ui_metadata",
    "build_beginner_first_success_completion_metadata_patch",
    "apply_beginner_first_success_completion",
    "explicit_beginner_first_success_achieved",
    "explicit_advanced_surface_unlock_requested",
    "beginner_surface_active",
    "beginner_advanced_surfaces_unlocked",
    "beginner_language_enabled",
    "return_use_ready",
    "terminal_execution_record_view",
]
