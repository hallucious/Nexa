from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class ArtifactSummaryView:
    total_artifact_count: int = 0
    visible_artifact_count: int = 0
    final_artifact_count: int = 0
    intermediate_artifact_count: int = 0
    warning_count: int = 0
    integrity_issue_count: int = 0
    top_summary_label: str | None = None


@dataclass(frozen=True)
class ArtifactItemView:
    artifact_id: str
    title: str
    artifact_type: str | None = None
    category: str = "unknown"
    producer_node_id: str | None = None
    producer_resource_type: str | None = None
    producer_resource_id: str | None = None
    created_at: str | None = None
    size_label: str | None = None
    preview_text: str | None = None
    is_final: bool = False
    is_partial: bool = False
    integrity_status: str = "unknown"


@dataclass(frozen=True)
class ArtifactMetadataView:
    mime_type: str | None = None
    encoding: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None
    source_label: str | None = None
    artifact_schema_version: str | None = None
    validation_status: str | None = None


@dataclass(frozen=True)
class ArtifactIntegrityView:
    integrity_status: str = "unknown"
    hash_value: str | None = None
    detail_label: str | None = None
    verifier_status: str | None = None


@dataclass(frozen=True)
class ArtifactLineageView:
    producer_node_id: str | None = None
    producer_ref: str | None = None
    lineage_refs: list[str] = field(default_factory=list)
    related_output_names: list[str] = field(default_factory=list)
    related_event_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactDetailView:
    artifact_id: str
    title: str
    artifact_type: str | None = None
    body_mode: str = "unavailable"
    body_preview: str | None = None
    structured_preview: dict | None = None
    metadata: ArtifactMetadataView = field(default_factory=ArtifactMetadataView)
    integrity: ArtifactIntegrityView = field(default_factory=ArtifactIntegrityView)
    lineage: ArtifactLineageView = field(default_factory=ArtifactLineageView)
    related_output_names: list[str] = field(default_factory=list)
    related_event_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactRelatedLinksView:
    related_graph_target_ids: list[str] = field(default_factory=list)
    related_run_ids: list[str] = field(default_factory=list)
    related_output_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactFilterStateView:
    category_filter: str | None = None
    search_query: str | None = None


@dataclass(frozen=True)
class ArtifactDiagnosticsView:
    missing_body_count: int = 0
    hash_unavailable_count: int = 0
    integrity_issue_count: int = 0
    warning_count: int = 0
    last_error_label: str | None = None


@dataclass(frozen=True)
class ArtifactViewerViewModel:
    source_mode: str
    storage_role: str
    viewer_status: str
    artifact_summary: ArtifactSummaryView = field(default_factory=ArtifactSummaryView)
    artifact_list: list[ArtifactItemView] = field(default_factory=list)
    selected_artifact: ArtifactDetailView | None = None
    related_links: ArtifactRelatedLinksView = field(default_factory=ArtifactRelatedLinksView)
    filter_state: ArtifactFilterStateView = field(default_factory=ArtifactFilterStateView)
    diagnostics: ArtifactDiagnosticsView = field(default_factory=ArtifactDiagnosticsView)
    explanation: str | None = None


def _unwrap(source):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _is_final_artifact(record: ExecutionRecordModel, artifact_id: str) -> bool:
    output_refs = {output.value_ref for output in record.outputs.final_outputs if output.value_ref}
    return artifact_id in output_refs or any(ref.artifact_type == "final_output" and ref.artifact_id == artifact_id for ref in record.artifacts.artifact_refs)


def _item_from_record(record: ExecutionRecordModel, artifact: ArtifactRecordCard) -> ArtifactItemView:
    is_final = _is_final_artifact(record, artifact.artifact_id)
    integrity = "ok" if artifact.hash else "hash_unavailable"
    if artifact.artifact_type == "validation_report":
        category = "verification"
    elif is_final or artifact.artifact_type in {"final_output", "decision", "json_object", "text"}:
        category = "output" if is_final else "typed_output"
    elif artifact.artifact_type in {"report", "audit_pack"}:
        category = "report"
    else:
        category = "intermediate"
    return ArtifactItemView(
        artifact_id=artifact.artifact_id,
        title=artifact.summary or artifact.artifact_id,
        artifact_type=artifact.artifact_type,
        category=category,
        producer_node_id=artifact.producer_node,
        created_at=record.meta.finished_at or record.meta.started_at,
        preview_text=artifact.summary,
        is_final=is_final,
        is_partial=artifact.ref is None,
        integrity_status=artifact.validation_status or integrity,
    )


def _detail_from_item(record: ExecutionRecordModel, item: ArtifactItemView, *, app_language: str) -> ArtifactDetailView:
    related_outputs = [output.output_ref for output in record.outputs.final_outputs if output.value_ref == item.artifact_id]
    artifact = next((artifact for artifact in record.artifacts.artifact_refs if artifact.artifact_id == item.artifact_id), None)
    structured_preview = artifact.payload_preview if artifact is not None and isinstance(artifact.payload_preview, dict) else None
    body_preview = None
    body_mode = "unavailable"
    if isinstance(structured_preview, dict):
        body_mode = "structured"
    elif item.preview_text:
        body_mode = "text"
        body_preview = item.preview_text
    return ArtifactDetailView(
        artifact_id=item.artifact_id,
        title=item.title,
        artifact_type=item.artifact_type,
        body_mode=body_mode,
        body_preview=body_preview,
        structured_preview=structured_preview,
        metadata=ArtifactMetadataView(
            created_at=item.created_at,
            source_label=record.meta.run_id,
            artifact_schema_version=(artifact.artifact_schema_version if artifact is not None else None),
            validation_status=(artifact.validation_status if artifact is not None else None),
        ),
        integrity=ArtifactIntegrityView(
            integrity_status=item.integrity_status,
            hash_value=(artifact.hash if artifact is not None else None),
            detail_label=ui_text(f"artifact.integrity.{item.integrity_status}", app_language=app_language, fallback_text=item.integrity_status),
            verifier_status=(structured_preview.get('aggregate_status') if isinstance(structured_preview, dict) else None),
        ),
        lineage=ArtifactLineageView(
            producer_node_id=item.producer_node_id,
            producer_ref=(artifact.producer_ref if artifact is not None else None),
            lineage_refs=(list(artifact.lineage_refs) if artifact is not None else []),
            related_output_names=related_outputs,
            related_event_ids=([record.meta.run_id, *(artifact.trace_refs if artifact is not None else [])]),
        ),
        related_output_names=related_outputs,
        related_event_ids=([record.meta.run_id, *(artifact.trace_refs if artifact is not None else [])]),
    )


def read_artifact_viewer_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    execution_record: ExecutionRecordModel | None = None,
    selected_artifact_id: str | None = None,
    explanation: str | None = None,
) -> ArtifactViewerViewModel:
    """Build a UI-facing artifact projection from engine-owned truth."""

    source = _unwrap(source)
    app_language = ui_language_from_sources(source, execution_record)
    if isinstance(source, ExecutionRecordModel):
        execution_record = source
        app_language = ui_language_from_sources(execution_record)

    if execution_record is None:
        storage_role = "working_save" if isinstance(source, WorkingSaveModel) else ("commit_snapshot" if isinstance(source, CommitSnapshotModel) else "none")
        return ArtifactViewerViewModel(
            source_mode="unknown",
            storage_role=storage_role,
            viewer_status="idle",
            diagnostics=ArtifactDiagnosticsView(last_error_label=ui_text("artifact.error.no_execution_artifacts_loaded", app_language=app_language, fallback_text="No execution artifacts loaded")),
            explanation=explanation,
        )

    items = [_item_from_record(execution_record, artifact) for artifact in execution_record.artifacts.artifact_refs]
    selected = None
    if items:
        selected_item = next((item for item in items if item.artifact_id == selected_artifact_id), items[0])
        selected = _detail_from_item(execution_record, selected_item, app_language=app_language)
    total = len(items)
    final_count = sum(1 for item in items if item.is_final)
    integrity_issue_count = sum(1 for item in items if item.integrity_status != "ok")
    diagnostics = ArtifactDiagnosticsView(
        missing_body_count=sum(1 for item in items if item.is_partial),
        hash_unavailable_count=sum(1 for item in items if item.integrity_status == "hash_unavailable"),
        integrity_issue_count=integrity_issue_count,
        warning_count=len(execution_record.diagnostics.warnings),
        last_error_label=execution_record.diagnostics.errors[-1].message if execution_record.diagnostics.errors else None,
    )
    related_outputs = [output.output_ref for output in execution_record.outputs.final_outputs]
    return ArtifactViewerViewModel(
        source_mode="replay_artifacts" if execution_record.source.trigger_type == "replay_run" else "execution_record_artifacts",
        storage_role="execution_record",
        viewer_status="ready" if items else "partial",
        artifact_summary=ArtifactSummaryView(
            total_artifact_count=total,
            visible_artifact_count=total,
            final_artifact_count=final_count,
            intermediate_artifact_count=total - final_count,
            warning_count=len(execution_record.diagnostics.warnings),
            integrity_issue_count=integrity_issue_count,
            top_summary_label=ui_text("artifact.summary.top", app_language=app_language, fallback_text="{count} artifacts", count=total),
        ),
        artifact_list=items,
        selected_artifact=selected,
        related_links=ArtifactRelatedLinksView(
            related_graph_target_ids=sorted({item.producer_node_id for item in items if item.producer_node_id}),
            related_run_ids=[execution_record.meta.run_id],
            related_output_names=related_outputs,
        ),
        diagnostics=diagnostics,
        explanation=explanation,
    )


__all__ = [
    "ArtifactSummaryView",
    "ArtifactItemView",
    "ArtifactMetadataView",
    "ArtifactIntegrityView",
    "ArtifactLineageView",
    "ArtifactDetailView",
    "ArtifactRelatedLinksView",
    "ArtifactFilterStateView",
    "ArtifactDiagnosticsView",
    "ArtifactViewerViewModel",
    "read_artifact_viewer_view_model",
]
