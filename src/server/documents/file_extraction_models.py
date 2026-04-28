from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

FileExtractionState = str
FileExtractionRejectionReason = str

FILE_EXTRACTION_STATES: set[str] = {"queued", "extracting", "extracted", "failed", "rejected"}
TERMINAL_FILE_EXTRACTION_STATES: set[str] = {"extracted", "failed", "rejected"}

_ALLOWED_EVENT_TYPES = {
    "extraction.requested",
    "extraction.started",
    "extraction.completed",
    "extraction.failed",
    "extraction.rejected",
}


@dataclass(frozen=True)
class FileExtractionRequest:
    workspace_id: str
    upload_id: str
    requested_by_user_ref: Optional[str] = None
    request_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        workspace_id = str(self.workspace_id or "").strip()
        upload_id = str(self.upload_id or "").strip()
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "upload_id", upload_id)
        if not workspace_id:
            raise ValueError("file_extraction.workspace_id_required")
        if not upload_id:
            raise ValueError("file_extraction.upload_id_required")


@dataclass(frozen=True)
class FileExtractionCompleteRequest:
    workspace_id: str
    extraction_id: str
    extracted_text_char_count: int
    text_artifact_ref: Optional[str] = None
    text_preview: Optional[str] = None
    content_hash: Optional[str] = None
    extractor_ref: Optional[str] = None
    completion_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        workspace_id = str(self.workspace_id or "").strip()
        extraction_id = str(self.extraction_id or "").strip()
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "extraction_id", extraction_id)
        if not workspace_id:
            raise ValueError("file_extraction.workspace_id_required")
        if not extraction_id:
            raise ValueError("file_extraction.extraction_id_required")
        if self.extracted_text_char_count < 0:
            raise ValueError("file_extraction.extracted_text_char_count_invalid")


@dataclass(frozen=True)
class FileExtractionRecord:
    extraction_id: str
    workspace_id: str
    upload_id: str
    extraction_state: FileExtractionState
    source_document_type: Optional[str] = None
    source_object_ref: Optional[str] = None
    text_artifact_ref: Optional[str] = None
    extracted_text_char_count: Optional[int] = None
    text_preview: Optional[str] = None
    content_hash: Optional[str] = None
    rejection_reason_code: Optional[FileExtractionRejectionReason] = None
    extractor_ref: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    requested_by_user_ref: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        extraction_id = str(self.extraction_id or "").strip()
        workspace_id = str(self.workspace_id or "").strip()
        upload_id = str(self.upload_id or "").strip()
        state = str(self.extraction_state or "").strip().lower()
        object.__setattr__(self, "extraction_id", extraction_id)
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "upload_id", upload_id)
        object.__setattr__(self, "extraction_state", state)
        if not extraction_id:
            raise ValueError("FileExtractionRecord.extraction_id must be non-empty")
        if not workspace_id:
            raise ValueError("FileExtractionRecord.workspace_id must be non-empty")
        if not upload_id:
            raise ValueError("FileExtractionRecord.upload_id must be non-empty")
        if state not in FILE_EXTRACTION_STATES:
            raise ValueError(f"Unsupported FileExtractionRecord.extraction_state: {state}")
        if self.extracted_text_char_count is not None and self.extracted_text_char_count < 0:
            raise ValueError("FileExtractionRecord.extracted_text_char_count must be >= 0")

    def to_row(self) -> dict[str, Any]:
        return {
            "extraction_id": self.extraction_id,
            "workspace_id": self.workspace_id,
            "upload_id": self.upload_id,
            "extraction_state": self.extraction_state,
            "source_document_type": self.source_document_type,
            "source_object_ref": self.source_object_ref,
            "text_artifact_ref": self.text_artifact_ref,
            "extracted_text_char_count": self.extracted_text_char_count,
            "text_preview": self.text_preview,
            "content_hash": self.content_hash,
            "rejection_reason_code": self.rejection_reason_code,
            "extractor_ref": self.extractor_ref,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "requested_by_user_ref": self.requested_by_user_ref,
            "metadata": dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class FileExtractionEventRecord:
    event_id: str
    extraction_id: str
    workspace_id: str
    upload_id: str
    event_type: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    reason_code: Optional[str] = None
    created_at: Optional[str] = None
    actor_user_ref: Optional[str] = None
    event_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        event_id = str(self.event_id or "").strip()
        extraction_id = str(self.extraction_id or "").strip()
        workspace_id = str(self.workspace_id or "").strip()
        upload_id = str(self.upload_id or "").strip()
        event_type = str(self.event_type or "").strip().lower()
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "extraction_id", extraction_id)
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "upload_id", upload_id)
        object.__setattr__(self, "event_type", event_type)
        if not event_id:
            raise ValueError("FileExtractionEventRecord.event_id must be non-empty")
        if not extraction_id:
            raise ValueError("FileExtractionEventRecord.extraction_id must be non-empty")
        if not workspace_id:
            raise ValueError("FileExtractionEventRecord.workspace_id must be non-empty")
        if not upload_id:
            raise ValueError("FileExtractionEventRecord.upload_id must be non-empty")
        if event_type not in _ALLOWED_EVENT_TYPES:
            raise ValueError(f"Unsupported FileExtractionEventRecord.event_type: {event_type}")

    def to_row(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "extraction_id": self.extraction_id,
            "workspace_id": self.workspace_id,
            "upload_id": self.upload_id,
            "event_type": self.event_type,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason_code": self.reason_code,
            "created_at": self.created_at,
            "actor_user_ref": self.actor_user_ref,
            "event_metadata": dict(self.event_metadata or {}),
        }


@dataclass(frozen=True)
class FileExtractionStatusResponse:
    status: str
    extraction: FileExtractionRecord
    events: tuple[FileExtractionEventRecord, ...] = ()


@dataclass(frozen=True)
class FileExtractionRejectedResponse:
    status: str
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    upload_id: Optional[str] = None
    extraction_id: Optional[str] = None
