from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from src.server.documents.file_ingestion_models import FileUploadEventRecord, FileUploadRecord


def _record_from_row(row: Mapping[str, object]) -> FileUploadRecord:
    return FileUploadRecord(
        upload_id=str(row.get("upload_id") or ""),
        workspace_id=str(row.get("workspace_id") or ""),
        object_ref=str(row.get("object_ref") or ""),
        original_filename=str(row.get("original_filename") or ""),
        declared_mime_type=str(row.get("declared_mime_type") or ""),
        declared_size_bytes=int(row.get("declared_size_bytes") or 0),
        upload_state=str(row.get("upload_state") or ""),
        document_type=str(row.get("document_type") or "").strip() or None,
        rejection_reason_code=str(row.get("rejection_reason_code") or "").strip() or None,
        observed_mime_type=str(row.get("observed_mime_type") or "").strip() or None,
        observed_size_bytes=int(row["observed_size_bytes"]) if row.get("observed_size_bytes") is not None else None,
        extracted_text_char_count=int(row["extracted_text_char_count"]) if row.get("extracted_text_char_count") is not None else None,
        created_at=str(row.get("created_at") or "").strip() or None,
        updated_at=str(row.get("updated_at") or "").strip() or None,
        expires_at=str(row.get("expires_at") or "").strip() or None,
        requested_by_user_ref=str(row.get("requested_by_user_ref") or "").strip() or None,
        metadata=row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {},
    )


def _event_from_row(row: Mapping[str, object]) -> FileUploadEventRecord:
    return FileUploadEventRecord(
        event_id=str(row.get("event_id") or ""),
        upload_id=str(row.get("upload_id") or ""),
        workspace_id=str(row.get("workspace_id") or ""),
        event_type=str(row.get("event_type") or ""),
        from_state=str(row.get("from_state") or "").strip() or None,
        to_state=str(row.get("to_state") or "").strip() or None,
        reason_code=str(row.get("reason_code") or "").strip() or None,
        created_at=str(row.get("created_at") or "").strip() or None,
        actor_user_ref=str(row.get("actor_user_ref") or "").strip() or None,
        event_metadata=row.get("event_metadata") if isinstance(row.get("event_metadata"), Mapping) else {},
    )


class InMemoryFileUploadStore:
    def __init__(self) -> None:
        self._uploads: dict[str, FileUploadRecord] = {}
        self._events: dict[str, list[FileUploadEventRecord]] = {}

    def write_upload(self, record: FileUploadRecord | Mapping[str, object]) -> FileUploadRecord:
        normalized = record if isinstance(record, FileUploadRecord) else _record_from_row(record)
        self._uploads[normalized.upload_id] = normalized
        return normalized

    def get_upload(self, upload_id: str) -> FileUploadRecord | None:
        return self._uploads.get(str(upload_id or "").strip())

    def get_workspace_upload(self, workspace_id: str, upload_id: str) -> FileUploadRecord | None:
        record = self.get_upload(upload_id)
        if record is None or record.workspace_id != str(workspace_id or "").strip():
            return None
        return record

    def list_workspace_uploads(self, workspace_id: str) -> tuple[FileUploadRecord, ...]:
        normalized = str(workspace_id or "").strip()
        return tuple(record for record in self._uploads.values() if record.workspace_id == normalized)

    def update_upload_state(
        self,
        *,
        upload_id: str,
        upload_state: str,
        updated_at: str | None = None,
        rejection_reason_code: str | None = None,
        observed_mime_type: str | None = None,
        observed_size_bytes: int | None = None,
        extracted_text_char_count: int | None = None,
    ) -> FileUploadRecord | None:
        existing = self.get_upload(upload_id)
        if existing is None:
            return None
        updated = replace(
            existing,
            upload_state=str(upload_state or "").strip().lower(),
            updated_at=updated_at or existing.updated_at,
            rejection_reason_code=rejection_reason_code,
            observed_mime_type=observed_mime_type or existing.observed_mime_type,
            observed_size_bytes=observed_size_bytes if observed_size_bytes is not None else existing.observed_size_bytes,
            extracted_text_char_count=extracted_text_char_count if extracted_text_char_count is not None else existing.extracted_text_char_count,
        )
        self._uploads[existing.upload_id] = updated
        return updated

    def append_event(self, event: FileUploadEventRecord | Mapping[str, object]) -> FileUploadEventRecord:
        normalized = event if isinstance(event, FileUploadEventRecord) else _event_from_row(event)
        self._events.setdefault(normalized.upload_id, []).append(normalized)
        return normalized

    def list_events(self, upload_id: str) -> tuple[FileUploadEventRecord, ...]:
        return tuple(self._events.get(str(upload_id or "").strip(), ()))
