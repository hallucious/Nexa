from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Optional
from uuid import uuid4

from src.server.documents.file_ingestion_models import (
    FileIngestionSafetyPolicy,
    FileUploadConfirmRequest,
    FileUploadEventRecord,
    FileUploadPresignRequest,
    FileUploadPresignResponse,
    FileUploadRecord,
    FileUploadRejectedResponse,
    FileUploadStatusResponse,
)
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_safety import document_type_for_mime, validate_confirm_request, validate_presign_request


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at(now_iso: str, ttl_seconds: int) -> str:
    try:
        base = datetime.fromisoformat(now_iso)
    except ValueError:
        base = datetime.now(timezone.utc)
    return (base + timedelta(seconds=ttl_seconds)).isoformat()


class FileIngestionService:
    @staticmethod
    def _event(
        *,
        upload_id: str,
        workspace_id: str,
        event_type: str,
        from_state: str | None,
        to_state: str | None,
        reason_code: str | None = None,
        now_iso: str | None = None,
        actor_user_ref: str | None = None,
        metadata: Mapping[str, object] | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ) -> FileUploadEventRecord:
        factory = event_id_factory or (lambda: f"fue_{uuid4().hex}")
        return FileUploadEventRecord(
            event_id=factory(),
            upload_id=upload_id,
            workspace_id=workspace_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            reason_code=reason_code,
            created_at=now_iso or _iso_now(),
            actor_user_ref=actor_user_ref,
            event_metadata=dict(metadata or {}),
        )

    @classmethod
    def presign(
        cls,
        request: FileUploadPresignRequest,
        *,
        store: InMemoryFileUploadStore,
        policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
        upload_id_factory: Callable[[], str] | None = None,
        now_iso: str | None = None,
        object_ref_prefix: str = "quarantine://uploads",
    ) -> FileUploadPresignResponse | FileUploadRejectedResponse:
        allowed, reason, message = validate_presign_request(request, policy=policy)
        if not allowed:
            return FileUploadRejectedResponse(
                status="rejected",
                reason_code=reason or "file_upload.rejected",
                message=message or "Upload request was rejected.",
                workspace_id=request.workspace_id,
            )
        factory = upload_id_factory or (lambda: f"upl_{uuid4().hex}")
        upload_id = factory()
        now_value = now_iso or _iso_now()
        object_ref = f"{object_ref_prefix}/{request.workspace_id}/{upload_id}"
        record = FileUploadRecord(
            upload_id=upload_id,
            workspace_id=request.workspace_id,
            object_ref=object_ref,
            original_filename=request.filename,
            declared_mime_type=request.declared_mime_type,
            declared_size_bytes=request.declared_size_bytes,
            upload_state="pending_upload",
            document_type=document_type_for_mime(request.declared_mime_type),
            created_at=now_value,
            updated_at=now_value,
            expires_at=_expires_at(now_value, policy.presign_ttl_seconds),
            requested_by_user_ref=request.requested_by_user_ref,
            metadata={"client_context": dict(request.client_context or {})},
        )
        store.write_upload(record)
        store.append_event(cls._event(
            upload_id=upload_id,
            workspace_id=request.workspace_id,
            event_type="upload.presigned",
            from_state=None,
            to_state="pending_upload",
            now_iso=now_value,
            actor_user_ref=request.requested_by_user_ref,
            metadata={"declared_mime_type": request.declared_mime_type, "declared_size_bytes": request.declared_size_bytes},
        ))
        return FileUploadPresignResponse(
            status="accepted",
            upload=record,
            upload_url=f"/api/workspaces/{request.workspace_id}/uploads/{upload_id}/object",
            upload_method="PUT",
            required_headers={"content-type": request.declared_mime_type},
            max_upload_bytes=policy.max_upload_bytes,
        )

    @classmethod
    def confirm(
        cls,
        request: FileUploadConfirmRequest,
        *,
        store: InMemoryFileUploadStore,
        policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
        now_iso: str | None = None,
    ) -> FileUploadStatusResponse | FileUploadRejectedResponse:
        existing = store.get_workspace_upload(request.workspace_id, request.upload_id)
        if existing is None:
            return FileUploadRejectedResponse(
                status="rejected",
                reason_code="file_upload.not_found",
                message="Upload was not found for this workspace.",
                workspace_id=request.workspace_id,
                upload_id=request.upload_id,
            )
        if existing.upload_state not in {"pending_upload", "quarantine", "scanning"}:
            return FileUploadRejectedResponse(
                status="rejected",
                reason_code="file_upload.state_not_confirmable",
                message="Upload is not in a confirmable state.",
                workspace_id=request.workspace_id,
                upload_id=request.upload_id,
            )
        now_value = now_iso or _iso_now()
        store.append_event(cls._event(
            upload_id=existing.upload_id,
            workspace_id=existing.workspace_id,
            event_type="upload.confirmed",
            from_state=existing.upload_state,
            to_state="quarantine",
            now_iso=now_value,
            actor_user_ref=existing.requested_by_user_ref,
        ))
        store.update_upload_state(upload_id=existing.upload_id, upload_state="quarantine", updated_at=now_value)
        store.append_event(cls._event(
            upload_id=existing.upload_id,
            workspace_id=existing.workspace_id,
            event_type="upload.status_changed",
            from_state="quarantine",
            to_state="scanning",
            now_iso=now_value,
            actor_user_ref=existing.requested_by_user_ref,
        ))
        scanning = store.update_upload_state(upload_id=existing.upload_id, upload_state="scanning", updated_at=now_value) or existing
        allowed, reason, message = validate_confirm_request(request, scanning, policy=policy)
        terminal_state = "safe" if allowed else "rejected"
        final = store.update_upload_state(
            upload_id=existing.upload_id,
            upload_state=terminal_state,
            updated_at=now_value,
            rejection_reason_code=None if allowed else reason,
            observed_mime_type=request.observed_mime_type or existing.declared_mime_type,
            observed_size_bytes=request.observed_size_bytes or existing.declared_size_bytes,
            extracted_text_char_count=request.extracted_text_char_count,
        ) or scanning
        store.append_event(cls._event(
            upload_id=existing.upload_id,
            workspace_id=existing.workspace_id,
            event_type="upload.safe" if allowed else "upload.rejected",
            from_state="scanning",
            to_state=terminal_state,
            reason_code=None if allowed else reason,
            now_iso=now_value,
            actor_user_ref=existing.requested_by_user_ref,
            metadata={"extracted_text_char_count": request.extracted_text_char_count},
        ))
        if not allowed:
            return FileUploadStatusResponse(status="rejected", upload=final, events=store.list_events(existing.upload_id))
        return FileUploadStatusResponse(status="safe", upload=final, events=store.list_events(existing.upload_id))

    @staticmethod
    def status(*, workspace_id: str, upload_id: str, store: InMemoryFileUploadStore, include_events: bool = True) -> FileUploadStatusResponse | FileUploadRejectedResponse:
        record = store.get_workspace_upload(workspace_id, upload_id)
        if record is None:
            return FileUploadRejectedResponse(
                status="rejected",
                reason_code="file_upload.not_found",
                message="Upload was not found for this workspace.",
                workspace_id=workspace_id,
                upload_id=upload_id,
            )
        return FileUploadStatusResponse(
            status=record.upload_state,
            upload=record,
            events=store.list_events(upload_id) if include_events else (),
        )


def response_to_payload(response: FileUploadPresignResponse | FileUploadStatusResponse | FileUploadRejectedResponse) -> dict[str, object]:
    return asdict(response)
