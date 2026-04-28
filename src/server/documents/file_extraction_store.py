from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from src.server.documents.file_extraction_models import FileExtractionEventRecord, FileExtractionRecord


def _record_from_row(row: Mapping[str, object]) -> FileExtractionRecord:
    return FileExtractionRecord(
        extraction_id=str(row.get("extraction_id") or ""),
        workspace_id=str(row.get("workspace_id") or ""),
        upload_id=str(row.get("upload_id") or ""),
        extraction_state=str(row.get("extraction_state") or ""),
        source_document_type=str(row.get("source_document_type") or "").strip() or None,
        source_object_ref=str(row.get("source_object_ref") or "").strip() or None,
        text_artifact_ref=str(row.get("text_artifact_ref") or "").strip() or None,
        extracted_text_char_count=int(row["extracted_text_char_count"]) if row.get("extracted_text_char_count") is not None else None,
        text_preview=str(row.get("text_preview") or "").strip() or None,
        content_hash=str(row.get("content_hash") or "").strip() or None,
        rejection_reason_code=str(row.get("rejection_reason_code") or "").strip() or None,
        extractor_ref=str(row.get("extractor_ref") or "").strip() or None,
        created_at=str(row.get("created_at") or "").strip() or None,
        updated_at=str(row.get("updated_at") or "").strip() or None,
        requested_by_user_ref=str(row.get("requested_by_user_ref") or "").strip() or None,
        metadata=row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {},
    )


def _event_from_row(row: Mapping[str, object]) -> FileExtractionEventRecord:
    return FileExtractionEventRecord(
        event_id=str(row.get("event_id") or ""),
        extraction_id=str(row.get("extraction_id") or ""),
        workspace_id=str(row.get("workspace_id") or ""),
        upload_id=str(row.get("upload_id") or ""),
        event_type=str(row.get("event_type") or ""),
        from_state=str(row.get("from_state") or "").strip() or None,
        to_state=str(row.get("to_state") or "").strip() or None,
        reason_code=str(row.get("reason_code") or "").strip() or None,
        created_at=str(row.get("created_at") or "").strip() or None,
        actor_user_ref=str(row.get("actor_user_ref") or "").strip() or None,
        event_metadata=row.get("event_metadata") if isinstance(row.get("event_metadata"), Mapping) else {},
    )


class InMemoryFileExtractionStore:
    def __init__(self) -> None:
        self._extractions: dict[str, FileExtractionRecord] = {}
        self._events: dict[str, list[FileExtractionEventRecord]] = {}

    def write_extraction(self, record: FileExtractionRecord | Mapping[str, object]) -> FileExtractionRecord:
        normalized = record if isinstance(record, FileExtractionRecord) else _record_from_row(record)
        self._extractions[normalized.extraction_id] = normalized
        return normalized

    def get_extraction(self, extraction_id: str) -> FileExtractionRecord | None:
        return self._extractions.get(str(extraction_id or "").strip())

    def get_workspace_extraction(self, workspace_id: str, extraction_id: str) -> FileExtractionRecord | None:
        record = self.get_extraction(extraction_id)
        if record is None or record.workspace_id != str(workspace_id or "").strip():
            return None
        return record

    def list_workspace_extractions(self, workspace_id: str) -> tuple[FileExtractionRecord, ...]:
        normalized = str(workspace_id or "").strip()
        return tuple(record for record in self._extractions.values() if record.workspace_id == normalized)

    def list_upload_extractions(self, workspace_id: str, upload_id: str) -> tuple[FileExtractionRecord, ...]:
        normalized_workspace = str(workspace_id or "").strip()
        normalized_upload = str(upload_id or "").strip()
        return tuple(
            record
            for record in self._extractions.values()
            if record.workspace_id == normalized_workspace and record.upload_id == normalized_upload
        )

    def list_queued_extractions(self, *, workspace_id: str | None = None, limit: int | None = None) -> tuple[FileExtractionRecord, ...]:
        normalized_workspace = str(workspace_id or "").strip() or None
        rows = [
            record for record in self._extractions.values()
            if record.extraction_state == "queued" and (normalized_workspace is None or record.workspace_id == normalized_workspace)
        ]
        rows.sort(key=lambda item: (item.created_at or "", item.extraction_id))
        if limit is not None:
            rows = rows[:max(int(limit), 0)]
        return tuple(rows)

    def list_stale_active_extractions(self, *, older_than_iso: str) -> tuple[FileExtractionRecord, ...]:
        cutoff = str(older_than_iso or "").strip()
        if not cutoff:
            return ()
        rows = [
            record for record in self._extractions.values()
            if record.extraction_state in {"queued", "extracting"} and str(record.updated_at or record.created_at or "") < cutoff
        ]
        rows.sort(key=lambda item: (item.updated_at or item.created_at or "", item.extraction_id))
        return tuple(rows)

    def update_extraction_state(
        self,
        *,
        extraction_id: str,
        extraction_state: str,
        updated_at: str | None = None,
        text_artifact_ref: str | None = None,
        extracted_text_char_count: int | None = None,
        text_preview: str | None = None,
        content_hash: str | None = None,
        rejection_reason_code: str | None = None,
        extractor_ref: str | None = None,
    ) -> FileExtractionRecord | None:
        existing = self.get_extraction(extraction_id)
        if existing is None:
            return None
        updated = replace(
            existing,
            extraction_state=str(extraction_state or "").strip().lower(),
            updated_at=updated_at or existing.updated_at,
            text_artifact_ref=text_artifact_ref if text_artifact_ref is not None else existing.text_artifact_ref,
            extracted_text_char_count=extracted_text_char_count if extracted_text_char_count is not None else existing.extracted_text_char_count,
            text_preview=text_preview if text_preview is not None else existing.text_preview,
            content_hash=content_hash if content_hash is not None else existing.content_hash,
            rejection_reason_code=rejection_reason_code,
            extractor_ref=extractor_ref if extractor_ref is not None else existing.extractor_ref,
        )
        self._extractions[existing.extraction_id] = updated
        return updated

    def append_event(self, event: FileExtractionEventRecord | Mapping[str, object]) -> FileExtractionEventRecord:
        normalized = event if isinstance(event, FileExtractionEventRecord) else _event_from_row(event)
        self._events.setdefault(normalized.extraction_id, []).append(normalized)
        return normalized

    def list_events(self, extraction_id: str) -> tuple[FileExtractionEventRecord, ...]:
        return tuple(self._events.get(str(extraction_id or "").strip(), ()))
