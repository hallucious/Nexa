from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.server.run_read_models import ProductSourceArtifactView


def project_source_artifact_view(
    run_record_row: Mapping[str, Any] | None,
    *,
    metrics: Mapping[str, Any] | None = None,
) -> ProductSourceArtifactView | None:
    source_payload = metrics.get("source_artifact") if isinstance(metrics, Mapping) else None
    storage_role = None
    canonical_ref = None
    working_save_id = None
    commit_id = None
    source_working_save_id = None
    if isinstance(source_payload, Mapping):
        storage_role = str(source_payload.get("storage_role") or "").strip() or None
        canonical_ref = str(source_payload.get("canonical_ref") or "").strip() or None
        working_save_id = str(source_payload.get("working_save_id") or "").strip() or None
        commit_id = str(source_payload.get("commit_id") or "").strip() or None
        source_working_save_id = str(source_payload.get("source_working_save_id") or "").strip() or None
    if isinstance(run_record_row, Mapping):
        target_type = str(run_record_row.get("execution_target_type") or "").strip() or None
        target_ref = str(run_record_row.get("execution_target_ref") or "").strip() or None
        if storage_role is None and target_type in {"working_save", "commit_snapshot"}:
            storage_role = target_type
        if canonical_ref is None and target_ref:
            canonical_ref = target_ref
        if working_save_id is None and storage_role == "working_save" and target_ref:
            working_save_id = target_ref
        if commit_id is None and storage_role == "commit_snapshot" and target_ref:
            commit_id = target_ref
        row_source_ws = str(run_record_row.get("source_working_save_id") or "").strip() or None
        if source_working_save_id is None and row_source_ws:
            source_working_save_id = row_source_ws
    if storage_role not in {"working_save", "commit_snapshot"} or not canonical_ref:
        return None
    return ProductSourceArtifactView(
        storage_role=storage_role,
        canonical_ref=canonical_ref,
        working_save_id=working_save_id,
        commit_id=commit_id,
        source_working_save_id=source_working_save_id,
    )


def project_source_artifact_payload(
    run_record_row: Mapping[str, Any] | None,
    *,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, object] | None:
    view = project_source_artifact_view(run_record_row, metrics=metrics)
    if view is None:
        return None
    payload: dict[str, object] = {
        "storage_role": view.storage_role,
        "canonical_ref": view.canonical_ref,
    }
    if view.working_save_id is not None:
        payload["working_save_id"] = view.working_save_id
    if view.commit_id is not None:
        payload["commit_id"] = view.commit_id
    if view.source_working_save_id is not None:
        payload["source_working_save_id"] = view.source_working_save_id
    return payload
