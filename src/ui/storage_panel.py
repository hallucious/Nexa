from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel

StorageRole = str
PanelMode = str


@dataclass(frozen=True)
class StorageLifecycleSummaryView:
    has_working_save: bool = False
    has_latest_commit_snapshot: bool = False
    has_latest_execution_record: bool = False
    current_stage: str = "unknown"
    uncommitted_changes_present: bool = False
    latest_commit_id: str | None = None
    latest_run_id: str | None = None
    summary_label: str | None = None


@dataclass(frozen=True)
class WorkingSaveCardView:
    working_save_id: str
    status: str
    title: str | None = None
    updated_at: str | None = None
    validation_summary_label: str | None = None
    latest_run_summary_label: str | None = None
    latest_artifact_ref_count: int | None = None
    designer_state_present: bool = False
    can_save: bool = True
    can_submit_for_review: bool = False
    can_compare_to_latest_commit: bool = False


@dataclass(frozen=True)
class CommitSnapshotCardView:
    commit_id: str
    parent_commit_id: str | None = None
    status: str = "unknown"
    created_at: str | None = None
    title: str | None = None
    approval_summary_label: str | None = None
    validation_summary_label: str | None = None
    source_working_save_id: str | None = None
    can_execute: bool = False
    can_compare: bool = False
    can_rollback_to: bool = False


@dataclass(frozen=True)
class ExecutionRecordCardView:
    run_id: str
    commit_id: str
    status: str = "unknown"
    started_at: str | None = None
    finished_at: str | None = None
    output_summary_label: str | None = None
    artifact_count: int | None = None
    trace_available: bool = False
    replay_available: bool = False
    can_open_trace: bool = False
    can_open_artifacts: bool = False
    can_compare_runs: bool = False


@dataclass(frozen=True)
class StorageRelationshipView:
    working_save_ref: str | None = None
    latest_commit_ref: str | None = None
    latest_run_ref: str | None = None
    source_to_commit_label: str | None = None
    commit_to_run_label: str | None = None
    latest_run_matches_latest_commit: bool | None = None
    draft_vs_commit_status: str | None = None


@dataclass(frozen=True)
class StorageRecentEntriesView:
    recent_working_save_refs: list[str] = field(default_factory=list)
    recent_commit_refs: list[str] = field(default_factory=list)
    recent_run_refs: list[str] = field(default_factory=list)
    selected_ref: str | None = None


@dataclass(frozen=True)
class StorageActionHint:
    action_type: str
    label: str
    enabled: bool
    reason_disabled: str | None = None
    target_ref: str | None = None


@dataclass(frozen=True)
class StorageDiagnosticsView:
    stale_reference_count: int = 0
    missing_commit_ref_count: int = 0
    missing_run_ref_count: int = 0
    lifecycle_warning_count: int = 0
    load_error_count: int = 0
    last_error_label: str | None = None


@dataclass(frozen=True)
class StoragePanelViewModel:
    active_storage_role: StorageRole
    panel_mode: PanelMode
    lifecycle_summary: StorageLifecycleSummaryView
    working_save_card: WorkingSaveCardView | None = None
    commit_snapshot_card: CommitSnapshotCardView | None = None
    execution_record_card: ExecutionRecordCardView | None = None
    relationship_graph: StorageRelationshipView = field(default_factory=StorageRelationshipView)
    recent_entries: StorageRecentEntriesView = field(default_factory=StorageRecentEntriesView)
    available_actions: list[StorageActionHint] = field(default_factory=list)
    diagnostics: StorageDiagnosticsView = field(default_factory=StorageDiagnosticsView)
    explanation: str | None = None



def _unwrap_loaded_source(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
) -> WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None:
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source



def _working_save_ref(working_save: WorkingSaveModel | None) -> str | None:
    if working_save is None:
        return None
    return f"working_save:{working_save.meta.working_save_id}"



def _commit_ref(commit_snapshot: CommitSnapshotModel | None) -> str | None:
    if commit_snapshot is None:
        return None
    return f"commit_snapshot:{commit_snapshot.meta.commit_id}"



def _run_ref(execution_record: ExecutionRecordModel | None) -> str | None:
    if execution_record is None:
        return None
    return f"execution_record:{execution_record.meta.run_id}"



def _latest_artifact_ref_count(working_save: WorkingSaveModel) -> int | None:
    last_run = working_save.runtime.last_run or {}
    artifact_ids = last_run.get("artifact_ids")
    if isinstance(artifact_ids, list):
        return len(artifact_ids)
    artifact_count = last_run.get("artifact_count")
    if isinstance(artifact_count, int):
        return artifact_count
    return None



def _working_status(working_save: WorkingSaveModel) -> str:
    runtime_status = str(working_save.runtime.status or "draft")
    validation_summary = working_save.runtime.validation_summary or {}
    blocking_count = validation_summary.get("blocking_count")
    if isinstance(blocking_count, int) and blocking_count > 0:
        return "validation_failed"
    mapping = {
        "draft": "draft",
        "review_ready": "ready_for_review",
        "validated": "validated",
        "execution_failed": "execution_failed",
        "executed": "executed",
    }
    return mapping.get(runtime_status, "unknown")



def _working_validation_summary_label(working_save: WorkingSaveModel) -> str | None:
    summary = working_save.runtime.validation_summary or {}
    blocking_count = summary.get("blocking_count")
    warning_count = summary.get("warning_count")
    parts: list[str] = []
    if isinstance(blocking_count, int):
        parts.append(f"blocking={blocking_count}")
    if isinstance(warning_count, int):
        parts.append(f"warnings={warning_count}")
    return ", ".join(parts) if parts else None



def _working_run_summary_label(working_save: WorkingSaveModel) -> str | None:
    last_run = working_save.runtime.last_run or {}
    run_id = last_run.get("run_id")
    status = last_run.get("status") or last_run.get("semantic_status")
    if run_id and status:
        return f"{run_id} ({status})"
    if run_id:
        return str(run_id)
    return None



def _build_working_save_card(working_save: WorkingSaveModel | None, *, commit_snapshot: CommitSnapshotModel | None) -> WorkingSaveCardView | None:
    if working_save is None:
        return None
    status = _working_status(working_save)
    validation_summary = working_save.runtime.validation_summary or {}
    blocking_count = validation_summary.get("blocking_count")
    can_submit = not (isinstance(blocking_count, int) and blocking_count > 0)
    return WorkingSaveCardView(
        working_save_id=working_save.meta.working_save_id,
        status=status,
        title=working_save.meta.name,
        updated_at=working_save.meta.updated_at,
        validation_summary_label=_working_validation_summary_label(working_save),
        latest_run_summary_label=_working_run_summary_label(working_save),
        latest_artifact_ref_count=_latest_artifact_ref_count(working_save),
        designer_state_present=working_save.designer is not None,
        can_save=True,
        can_submit_for_review=can_submit,
        can_compare_to_latest_commit=commit_snapshot is not None,
    )



def _commit_status(commit_snapshot: CommitSnapshotModel) -> str:
    validation_result = commit_snapshot.validation.validation_result
    if validation_result == "passed_with_warnings":
        return "approved_with_warnings"
    if commit_snapshot.approval.approval_completed:
        return "approved"
    return "unknown"



def _build_commit_snapshot_card(commit_snapshot: CommitSnapshotModel | None) -> CommitSnapshotCardView | None:
    if commit_snapshot is None:
        return None
    approval_summary = commit_snapshot.approval.summary or {}
    validation_summary = commit_snapshot.validation.summary or {}
    return CommitSnapshotCardView(
        commit_id=commit_snapshot.meta.commit_id,
        parent_commit_id=commit_snapshot.lineage.parent_commit_id,
        status=_commit_status(commit_snapshot),
        created_at=commit_snapshot.meta.updated_at or commit_snapshot.meta.created_at,
        title=commit_snapshot.meta.name,
        approval_summary_label=str(approval_summary.get("approved_at") or commit_snapshot.approval.approval_status or "approved"),
        validation_summary_label=(
            f"result={commit_snapshot.validation.validation_result}"
            if not validation_summary
            else f"result={commit_snapshot.validation.validation_result}, warnings={validation_summary.get('warning_count', 0)}"
        ),
        source_working_save_id=commit_snapshot.meta.source_working_save_id,
        can_execute=commit_snapshot.approval.approval_completed,
        can_compare=True,
        can_rollback_to=commit_snapshot.approval.approval_completed,
    )



def _build_execution_record_card(execution_record: ExecutionRecordModel | None, *, compare_runs_enabled: bool) -> ExecutionRecordCardView | None:
    if execution_record is None:
        return None
    trace_available = bool(execution_record.timeline.trace_ref or execution_record.timeline.event_stream_ref)
    replay_available = bool(execution_record.timeline.trace_ref or execution_record.timeline.event_stream_ref)
    artifact_count = execution_record.artifacts.artifact_count or len(execution_record.artifacts.artifact_refs)
    output_summary_label = execution_record.outputs.output_summary
    if output_summary_label is None and execution_record.outputs.final_outputs:
        output_summary_label = ", ".join(output.output_ref for output in execution_record.outputs.final_outputs)
    return ExecutionRecordCardView(
        run_id=execution_record.meta.run_id,
        commit_id=execution_record.source.commit_id,
        status=execution_record.meta.status,
        started_at=execution_record.meta.started_at,
        finished_at=execution_record.meta.finished_at,
        output_summary_label=output_summary_label,
        artifact_count=artifact_count,
        trace_available=trace_available,
        replay_available=replay_available,
        can_open_trace=trace_available,
        can_open_artifacts=artifact_count > 0,
        can_compare_runs=compare_runs_enabled,
    )



def _relationship_view(
    working_save: WorkingSaveModel | None,
    commit_snapshot: CommitSnapshotModel | None,
    execution_record: ExecutionRecordModel | None,
) -> StorageRelationshipView:
    latest_run_matches_latest_commit: bool | None = None
    if commit_snapshot is not None and execution_record is not None:
        latest_run_matches_latest_commit = execution_record.source.commit_id == commit_snapshot.meta.commit_id

    draft_vs_commit_status: str | None
    if working_save is None:
        draft_vs_commit_status = None
    elif commit_snapshot is None:
        draft_vs_commit_status = "no_commit"
    elif commit_snapshot.meta.source_working_save_id == working_save.meta.working_save_id:
        draft_vs_commit_status = "in_sync"
    else:
        draft_vs_commit_status = "has_uncommitted_changes"

    return StorageRelationshipView(
        working_save_ref=_working_save_ref(working_save),
        latest_commit_ref=_commit_ref(commit_snapshot),
        latest_run_ref=_run_ref(execution_record),
        source_to_commit_label=(
            f"{working_save.meta.working_save_id} → {commit_snapshot.meta.commit_id}"
            if working_save is not None and commit_snapshot is not None
            else None
        ),
        commit_to_run_label=(
            f"{commit_snapshot.meta.commit_id} → {execution_record.meta.run_id}"
            if commit_snapshot is not None and execution_record is not None
            else None
        ),
        latest_run_matches_latest_commit=latest_run_matches_latest_commit,
        draft_vs_commit_status=draft_vs_commit_status,
    )



def _current_stage(
    active_role: str,
    *,
    working_save: WorkingSaveModel | None,
    execution_record: ExecutionRecordModel | None,
    commit_snapshot: CommitSnapshotModel | None,
) -> str:
    if active_role == "execution_record" and execution_record is not None:
        status = execution_record.meta.status
        if status == "running":
            return "executing"
        if status == "completed":
            return "executed"
        if status in {"failed", "cancelled", "partial"}:
            return "failed_execution"
    if active_role == "commit_snapshot" and commit_snapshot is not None:
        return "approved"
    if working_save is not None:
        status = _working_status(working_save)
        if status == "ready_for_review":
            return "review_ready"
        if status == "validated":
            return "review_ready"
        if status == "executed":
            return "executed"
        if status == "execution_failed":
            return "failed_execution"
        return "editing"
    return "unknown"



def _summary_label(stage: str) -> str:
    return {
        "editing": "Draft currently being edited",
        "review_ready": "Draft is ready for review",
        "approved": "Approved commit snapshot available",
        "executing": "Execution is currently running",
        "executed": "Latest run completed",
        "failed_execution": "Latest run did not complete successfully",
        "unknown": "Storage lifecycle state is incomplete",
    }.get(stage, "Storage lifecycle state is incomplete")



def _lifecycle_summary(
    *,
    active_role: str,
    working_save: WorkingSaveModel | None,
    commit_snapshot: CommitSnapshotModel | None,
    execution_record: ExecutionRecordModel | None,
) -> StorageLifecycleSummaryView:
    relationship = _relationship_view(working_save, commit_snapshot, execution_record)
    stage = _current_stage(
        active_role,
        working_save=working_save,
        execution_record=execution_record,
        commit_snapshot=commit_snapshot,
    )
    return StorageLifecycleSummaryView(
        has_working_save=working_save is not None,
        has_latest_commit_snapshot=commit_snapshot is not None,
        has_latest_execution_record=execution_record is not None,
        current_stage=stage,
        uncommitted_changes_present=relationship.draft_vs_commit_status == "has_uncommitted_changes",
        latest_commit_id=commit_snapshot.meta.commit_id if commit_snapshot is not None else None,
        latest_run_id=execution_record.meta.run_id if execution_record is not None else None,
        summary_label=_summary_label(stage),
    )



def _panel_mode(active_role: str) -> str:
    return {
        "working_save": "draft_focus",
        "commit_snapshot": "commit_focus",
        "execution_record": "execution_focus",
        "none": "lifecycle_overview",
    }.get(active_role, "unknown")



def _recent_entries(
    *,
    working_save: WorkingSaveModel | None,
    commit_snapshot: CommitSnapshotModel | None,
    execution_record: ExecutionRecordModel | None,
    recent_working_save_refs: Iterable[str] | None,
    recent_commit_refs: Iterable[str] | None,
    recent_run_refs: Iterable[str] | None,
) -> StorageRecentEntriesView:
    working_refs = [str(ref) for ref in (recent_working_save_refs or [])]
    commit_refs = [str(ref) for ref in (recent_commit_refs or [])]
    run_refs = [str(ref) for ref in (recent_run_refs or [])]

    current_working_ref = _working_save_ref(working_save)
    current_commit_ref = _commit_ref(commit_snapshot)
    current_run_ref = _run_ref(execution_record)
    if current_working_ref and current_working_ref not in working_refs:
        working_refs.insert(0, current_working_ref)
    if current_commit_ref and current_commit_ref not in commit_refs:
        commit_refs.insert(0, current_commit_ref)
    if current_run_ref and current_run_ref not in run_refs:
        run_refs.insert(0, current_run_ref)

    selected_ref = current_run_ref or current_commit_ref or current_working_ref
    return StorageRecentEntriesView(
        recent_working_save_refs=working_refs,
        recent_commit_refs=commit_refs,
        recent_run_refs=run_refs,
        selected_ref=selected_ref,
    )



def _diagnostics(
    *,
    working_save: WorkingSaveModel | None,
    commit_snapshot: CommitSnapshotModel | None,
    execution_record: ExecutionRecordModel | None,
) -> StorageDiagnosticsView:
    missing_commit_ref_count = 0
    missing_run_ref_count = 0
    stale_reference_count = 0
    lifecycle_warning_count = 0
    last_error_label: str | None = None

    if execution_record is not None and not execution_record.source.commit_id:
        missing_commit_ref_count += 1
    if working_save is not None:
        last_run = working_save.runtime.last_run or {}
        if last_run.get("run_id") and execution_record is None:
            missing_run_ref_count += 1
        if last_run.get("commit_id") and commit_snapshot is None:
            missing_commit_ref_count += 1
        if last_run.get("resume_ready") is False:
            lifecycle_warning_count += 1
            last_error_label = "resume anchor requires revalidation"
        if commit_snapshot is not None:
            source_commit_id = (working_save.runtime.validation_summary or {}).get("source_commit_id")
            if source_commit_id and source_commit_id != commit_snapshot.meta.commit_id:
                stale_reference_count += 1
                lifecycle_warning_count += 1
                last_error_label = f"working save references stale commit {source_commit_id}"
    if commit_snapshot is not None and execution_record is not None:
        if execution_record.source.commit_id != commit_snapshot.meta.commit_id:
            stale_reference_count += 1
            lifecycle_warning_count += 1
            last_error_label = "latest execution record is anchored to a different commit snapshot"

    return StorageDiagnosticsView(
        stale_reference_count=stale_reference_count,
        missing_commit_ref_count=missing_commit_ref_count,
        missing_run_ref_count=missing_run_ref_count,
        lifecycle_warning_count=lifecycle_warning_count,
        load_error_count=0,
        last_error_label=last_error_label,
    )



def _available_actions(
    *,
    active_role: str,
    lifecycle_summary: StorageLifecycleSummaryView,
    working_save: WorkingSaveModel | None,
    commit_snapshot: CommitSnapshotModel | None,
    execution_record: ExecutionRecordModel | None,
) -> list[StorageActionHint]:
    actions: list[StorageActionHint] = []
    if working_save is not None:
        actions.append(StorageActionHint("save_working_save", "Save draft", True, target_ref=_working_save_ref(working_save)))
        can_review = _working_status(working_save) != "validation_failed"
        actions.append(
            StorageActionHint(
                "submit_for_review",
                "Submit for review",
                can_review,
                None if can_review else "Draft still has blocking validation findings",
                _working_save_ref(working_save),
            )
        )
        actions.append(
            StorageActionHint(
                "compare_draft_to_commit",
                "Compare draft to latest commit",
                commit_snapshot is not None,
                None if commit_snapshot is not None else "No approved commit snapshot available yet",
                _commit_ref(commit_snapshot),
            )
        )
    if commit_snapshot is not None:
        actions.append(StorageActionHint("open_latest_commit", "Open latest commit", True, target_ref=_commit_ref(commit_snapshot)))
        actions.append(
            StorageActionHint(
                "run_from_commit",
                "Run from commit",
                commit_snapshot.approval.approval_completed,
                None if commit_snapshot.approval.approval_completed else "Commit snapshot is not approved",
                _commit_ref(commit_snapshot),
            )
        )
        actions.append(StorageActionHint("select_rollback_target", "Select rollback target", True, target_ref=_commit_ref(commit_snapshot)))
    if execution_record is not None:
        trace_enabled = bool(execution_record.timeline.trace_ref or execution_record.timeline.event_stream_ref)
        artifact_enabled = (execution_record.artifacts.artifact_count or len(execution_record.artifacts.artifact_refs)) > 0
        actions.append(
            StorageActionHint(
                "open_latest_run",
                "Open latest run",
                True,
                target_ref=_run_ref(execution_record),
            )
        )
        actions.append(
            StorageActionHint(
                "open_trace",
                "Open trace",
                trace_enabled,
                None if trace_enabled else "No trace/event stream reference available",
                target_ref=_run_ref(execution_record),
            )
        )
        actions.append(
            StorageActionHint(
                "open_artifacts",
                "Open artifacts",
                artifact_enabled,
                None if artifact_enabled else "No execution artifacts recorded",
                target_ref=_run_ref(execution_record),
            )
        )
    if active_role == "none" and not actions:
        actions.append(StorageActionHint("none", "No lifecycle action available", False, reason_disabled="No storage artifact loaded"))
    if lifecycle_summary.has_latest_execution_record and execution_record is not None:
        actions.append(StorageActionHint("compare_runs", "Compare runs", False, reason_disabled="A second execution record is required", target_ref=_run_ref(execution_record)))
    return actions



def read_storage_view_model(
    active_source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    latest_working_save: WorkingSaveModel | None = None,
    latest_commit_snapshot: CommitSnapshotModel | None = None,
    latest_execution_record: ExecutionRecordModel | None = None,
    recent_working_save_refs: Iterable[str] | None = None,
    recent_commit_refs: Iterable[str] | None = None,
    recent_run_refs: Iterable[str] | None = None,
    explanation: str | None = None,
) -> StoragePanelViewModel:
    """Build a UI-facing storage lifecycle projection from engine-owned truth."""

    active_source = _unwrap_loaded_source(active_source)

    if isinstance(active_source, WorkingSaveModel):
        working_save = active_source
        commit_snapshot = latest_commit_snapshot
        execution_record = latest_execution_record
        active_role = "working_save"
    elif isinstance(active_source, CommitSnapshotModel):
        working_save = latest_working_save
        commit_snapshot = active_source
        execution_record = latest_execution_record
        active_role = "commit_snapshot"
    elif isinstance(active_source, ExecutionRecordModel):
        working_save = latest_working_save
        commit_snapshot = latest_commit_snapshot
        execution_record = active_source
        active_role = "execution_record"
    else:
        working_save = latest_working_save
        commit_snapshot = latest_commit_snapshot
        execution_record = latest_execution_record
        active_role = "none"

    lifecycle_summary = _lifecycle_summary(
        active_role=active_role,
        working_save=working_save,
        commit_snapshot=commit_snapshot,
        execution_record=execution_record,
    )
    recent_entries = _recent_entries(
        working_save=working_save,
        commit_snapshot=commit_snapshot,
        execution_record=execution_record,
        recent_working_save_refs=recent_working_save_refs,
        recent_commit_refs=recent_commit_refs,
        recent_run_refs=recent_run_refs,
    )
    diagnostics = _diagnostics(
        working_save=working_save,
        commit_snapshot=commit_snapshot,
        execution_record=execution_record,
    )

    return StoragePanelViewModel(
        active_storage_role=active_role,
        panel_mode=_panel_mode(active_role),
        lifecycle_summary=lifecycle_summary,
        working_save_card=_build_working_save_card(working_save, commit_snapshot=commit_snapshot),
        commit_snapshot_card=_build_commit_snapshot_card(commit_snapshot),
        execution_record_card=_build_execution_record_card(execution_record, compare_runs_enabled=False),
        relationship_graph=_relationship_view(working_save, commit_snapshot, execution_record),
        recent_entries=recent_entries,
        available_actions=_available_actions(
            active_role=active_role,
            lifecycle_summary=lifecycle_summary,
            working_save=working_save,
            commit_snapshot=commit_snapshot,
            execution_record=execution_record,
        ),
        diagnostics=diagnostics,
        explanation=explanation,
    )


__all__ = [
    "StoragePanelViewModel",
    "StorageLifecycleSummaryView",
    "WorkingSaveCardView",
    "CommitSnapshotCardView",
    "ExecutionRecordCardView",
    "StorageRelationshipView",
    "StorageRecentEntriesView",
    "StorageActionHint",
    "StorageDiagnosticsView",
    "read_storage_view_model",
]
