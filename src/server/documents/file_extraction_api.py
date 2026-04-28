from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from uuid import uuid4

from src.server.documents.file_extraction_models import (
    FileExtractionCompleteRequest,
    FileExtractionEventRecord,
    FileExtractionRecord,
    FileExtractionRejectedResponse,
    FileExtractionRequest,
    FileExtractionStatusResponse,
)
from src.server.documents.file_extraction_store import InMemoryFileExtractionStore
from src.server.documents.file_ingestion_models import FileIngestionSafetyPolicy, FileUploadRecord
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upload_state(upload: Any | None) -> str | None:
    if upload is None:
        return None
    if isinstance(upload, FileUploadRecord):
        return upload.upload_state
    if isinstance(upload, Mapping):
        return str(upload.get("upload_state") or upload.get("state") or "").strip().lower() or None
    return str(getattr(upload, "upload_state", "") or getattr(upload, "state", "")).strip().lower() or None


def _upload_document_type(upload: Any | None) -> str | None:
    if upload is None:
        return None
    if isinstance(upload, FileUploadRecord):
        return upload.document_type
    if isinstance(upload, Mapping):
        return str(upload.get("document_type") or "").strip() or None
    return str(getattr(upload, "document_type", "") or "").strip() or None


def _upload_object_ref(upload: Any | None) -> str | None:
    if upload is None:
        return None
    if isinstance(upload, FileUploadRecord):
        return upload.object_ref
    if isinstance(upload, Mapping):
        return str(upload.get("object_ref") or "").strip() or None
    return str(getattr(upload, "object_ref", "") or "").strip() or None


def _upload_requested_by(upload: Any | None) -> str | None:
    if upload is None:
        return None
    if isinstance(upload, FileUploadRecord):
        return upload.requested_by_user_ref
    if isinstance(upload, Mapping):
        return str(upload.get("requested_by_user_ref") or "").strip() or None
    return str(getattr(upload, "requested_by_user_ref", "") or "").strip() or None


class FileExtractionService:
    @staticmethod
    def _event(
        *,
        extraction_id: str,
        workspace_id: str,
        upload_id: str,
        event_type: str,
        from_state: str | None,
        to_state: str | None,
        reason_code: str | None = None,
        now_iso: str | None = None,
        actor_user_ref: str | None = None,
        metadata: Mapping[str, object] | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ) -> FileExtractionEventRecord:
        factory = event_id_factory or (lambda: f"fexevt_{uuid4().hex}")
        return FileExtractionEventRecord(
            event_id=factory(),
            extraction_id=extraction_id,
            workspace_id=workspace_id,
            upload_id=upload_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            reason_code=reason_code,
            created_at=now_iso or _iso_now(),
            actor_user_ref=actor_user_ref,
            event_metadata=dict(metadata or {}),
        )

    @classmethod
    def request_extraction(
        cls,
        request: FileExtractionRequest,
        *,
        upload_store: InMemoryFileUploadStore,
        extraction_store: InMemoryFileExtractionStore,
        extraction_id_factory: Callable[[], str] | None = None,
        now_iso: str | None = None,
    ) -> FileExtractionStatusResponse | FileExtractionRejectedResponse:
        upload = upload_store.get_workspace_upload(request.workspace_id, request.upload_id)
        if upload is None:
            return FileExtractionRejectedResponse(
                status="rejected",
                reason_code="file_extraction.upload_not_found",
                message="Upload was not found for this workspace.",
                workspace_id=request.workspace_id,
                upload_id=request.upload_id,
            )
        state = _upload_state(upload)
        if state != "safe":
            return FileExtractionRejectedResponse(
                status="rejected",
                reason_code=f"file_extraction.upload_not_safe.{state or 'unknown'}",
                message="Only safe uploads may enter document text extraction.",
                workspace_id=request.workspace_id,
                upload_id=request.upload_id,
            )
        existing = extraction_store.list_upload_extractions(request.workspace_id, request.upload_id)
        if existing:
            preferred = sorted(existing, key=lambda item: (item.created_at or "", item.extraction_id), reverse=True)[0]
            return FileExtractionStatusResponse(status=preferred.extraction_state, extraction=preferred, events=extraction_store.list_events(preferred.extraction_id))
        factory = extraction_id_factory or (lambda: f"fex_{uuid4().hex}")
        extraction_id = factory()
        now_value = now_iso or _iso_now()
        record = FileExtractionRecord(
            extraction_id=extraction_id,
            workspace_id=request.workspace_id,
            upload_id=request.upload_id,
            extraction_state="queued",
            source_document_type=_upload_document_type(upload),
            source_object_ref=_upload_object_ref(upload),
            created_at=now_value,
            updated_at=now_value,
            requested_by_user_ref=request.requested_by_user_ref or _upload_requested_by(upload),
            metadata={"request_metadata": dict(request.request_metadata or {})},
        )
        extraction_store.write_extraction(record)
        extraction_store.append_event(cls._event(
            extraction_id=extraction_id,
            workspace_id=request.workspace_id,
            upload_id=request.upload_id,
            event_type="extraction.requested",
            from_state=None,
            to_state="queued",
            now_iso=now_value,
            actor_user_ref=record.requested_by_user_ref,
        ))
        return FileExtractionStatusResponse(status="queued", extraction=record, events=extraction_store.list_events(extraction_id))

    @classmethod
    def start_extraction(
        cls,
        *,
        workspace_id: str,
        extraction_id: str,
        extraction_store: InMemoryFileExtractionStore,
        now_iso: str | None = None,
        extractor_ref: str | None = None,
    ) -> FileExtractionStatusResponse | FileExtractionRejectedResponse:
        record = extraction_store.get_workspace_extraction(workspace_id, extraction_id)
        if record is None:
            return FileExtractionRejectedResponse(status="rejected", reason_code="file_extraction.not_found", message="Extraction was not found for this workspace.", workspace_id=workspace_id, extraction_id=extraction_id)
        if record.extraction_state != "queued":
            return FileExtractionRejectedResponse(status="rejected", reason_code="file_extraction.state_not_startable", message="Extraction is not in a startable state.", workspace_id=workspace_id, upload_id=record.upload_id, extraction_id=extraction_id)
        now_value = now_iso or _iso_now()
        updated = extraction_store.update_extraction_state(extraction_id=record.extraction_id, extraction_state="extracting", updated_at=now_value, extractor_ref=extractor_ref) or record
        extraction_store.append_event(cls._event(
            extraction_id=record.extraction_id,
            workspace_id=record.workspace_id,
            upload_id=record.upload_id,
            event_type="extraction.started",
            from_state="queued",
            to_state="extracting",
            now_iso=now_value,
            actor_user_ref=record.requested_by_user_ref,
            metadata={"extractor_ref": extractor_ref} if extractor_ref else None,
        ))
        return FileExtractionStatusResponse(status="extracting", extraction=updated, events=extraction_store.list_events(record.extraction_id))

    @classmethod
    def complete_extraction(
        cls,
        request: FileExtractionCompleteRequest,
        *,
        extraction_store: InMemoryFileExtractionStore,
        policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
        now_iso: str | None = None,
    ) -> FileExtractionStatusResponse | FileExtractionRejectedResponse:
        record = extraction_store.get_workspace_extraction(request.workspace_id, request.extraction_id)
        if record is None:
            return FileExtractionRejectedResponse(status="rejected", reason_code="file_extraction.not_found", message="Extraction was not found for this workspace.", workspace_id=request.workspace_id, extraction_id=request.extraction_id)
        if record.extraction_state not in {"queued", "extracting"}:
            return FileExtractionRejectedResponse(status="rejected", reason_code="file_extraction.state_not_completable", message="Extraction is not in a completable state.", workspace_id=request.workspace_id, upload_id=record.upload_id, extraction_id=request.extraction_id)
        now_value = now_iso or _iso_now()
        if request.extracted_text_char_count > policy.max_extracted_chars:
            updated = extraction_store.update_extraction_state(
                extraction_id=record.extraction_id,
                extraction_state="rejected",
                updated_at=now_value,
                rejection_reason_code="file_extraction.extraction_over_limit",
                extracted_text_char_count=request.extracted_text_char_count,
                extractor_ref=request.extractor_ref,
            ) or record
            extraction_store.append_event(cls._event(
                extraction_id=record.extraction_id,
                workspace_id=record.workspace_id,
                upload_id=record.upload_id,
                event_type="extraction.rejected",
                from_state=record.extraction_state,
                to_state="rejected",
                reason_code="file_extraction.extraction_over_limit",
                now_iso=now_value,
                actor_user_ref=record.requested_by_user_ref,
                metadata={"extracted_text_char_count": request.extracted_text_char_count},
            ))
            return FileExtractionStatusResponse(status="rejected", extraction=updated, events=extraction_store.list_events(record.extraction_id))
        artifact_ref = request.text_artifact_ref or f"extracted-text://{record.workspace_id}/{record.extraction_id}"
        updated = extraction_store.update_extraction_state(
            extraction_id=record.extraction_id,
            extraction_state="extracted",
            updated_at=now_value,
            text_artifact_ref=artifact_ref,
            extracted_text_char_count=request.extracted_text_char_count,
            text_preview=request.text_preview,
            content_hash=request.content_hash,
            extractor_ref=request.extractor_ref,
        ) or record
        extraction_store.append_event(cls._event(
            extraction_id=record.extraction_id,
            workspace_id=record.workspace_id,
            upload_id=record.upload_id,
            event_type="extraction.completed",
            from_state=record.extraction_state,
            to_state="extracted",
            now_iso=now_value,
            actor_user_ref=record.requested_by_user_ref,
            metadata={"text_artifact_ref": artifact_ref, "extracted_text_char_count": request.extracted_text_char_count},
        ))
        return FileExtractionStatusResponse(status="extracted", extraction=updated, events=extraction_store.list_events(record.extraction_id))

    @staticmethod
    def status(*, workspace_id: str, extraction_id: str, extraction_store: InMemoryFileExtractionStore, include_events: bool = True) -> FileExtractionStatusResponse | FileExtractionRejectedResponse:
        record = extraction_store.get_workspace_extraction(workspace_id, extraction_id)
        if record is None:
            return FileExtractionRejectedResponse(status="rejected", reason_code="file_extraction.not_found", message="Extraction was not found for this workspace.", workspace_id=workspace_id, extraction_id=extraction_id)
        return FileExtractionStatusResponse(status=record.extraction_state, extraction=record, events=extraction_store.list_events(extraction_id) if include_events else ())


def response_to_payload(response: FileExtractionStatusResponse | FileExtractionRejectedResponse) -> dict[str, object]:
    return asdict(response)
