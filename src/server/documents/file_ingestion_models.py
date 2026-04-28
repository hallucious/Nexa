from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

FileUploadState = str
FileUploadRejectionReason = str

FILE_UPLOAD_STATES: set[str] = {"pending_upload", "quarantine", "scanning", "safe", "rejected"}
TERMINAL_FILE_UPLOAD_STATES: set[str] = {"safe", "rejected"}
SUPPORTED_DOCUMENT_TYPES: dict[str, dict[str, object]] = {
    "application/pdf": {
        "document_type": "pdf",
        "extensions": (".pdf",),
        "magic_prefixes": (b"%PDF-",),
    },
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
        "document_type": "docx",
        "extensions": (".docx",),
        "magic_prefixes": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    },
}

_ALLOWED_EVENT_TYPES = {
    "upload.presigned",
    "upload.confirmed",
    "upload.status_changed",
    "upload.rejected",
    "upload.safe",
}


@dataclass(frozen=True)
class FileIngestionSafetyPolicy:
    """Minimum safety policy for direct-to-object-store document intake."""

    max_upload_bytes: int = 10 * 1024 * 1024
    max_extracted_chars: int = 200_000
    presign_ttl_seconds: int = 900
    require_magic_bytes_on_confirm: bool = True

    def __post_init__(self) -> None:
        if self.max_upload_bytes <= 0:
            raise ValueError("FileIngestionSafetyPolicy.max_upload_bytes must be > 0")
        if self.max_extracted_chars <= 0:
            raise ValueError("FileIngestionSafetyPolicy.max_extracted_chars must be > 0")
        if self.presign_ttl_seconds <= 0:
            raise ValueError("FileIngestionSafetyPolicy.presign_ttl_seconds must be > 0")


@dataclass(frozen=True)
class FileUploadPresignRequest:
    workspace_id: str
    filename: str
    declared_mime_type: str
    declared_size_bytes: int
    requested_by_user_ref: Optional[str] = None
    client_context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        workspace_id = str(self.workspace_id or "").strip()
        filename = str(self.filename or "").strip()
        declared_mime_type = str(self.declared_mime_type or "").strip().lower()
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "filename", filename)
        object.__setattr__(self, "declared_mime_type", declared_mime_type)
        if not workspace_id:
            raise ValueError("file_upload.workspace_id_required")
        if not filename:
            raise ValueError("file_upload.filename_required")
        if self.declared_size_bytes <= 0:
            raise ValueError("file_upload.size_required")


@dataclass(frozen=True)
class FileUploadConfirmRequest:
    workspace_id: str
    upload_id: str
    observed_size_bytes: Optional[int] = None
    observed_mime_type: Optional[str] = None
    magic_bytes_hex: Optional[str] = None
    malware_scan_status: str = "clean"
    extracted_text_char_count: int = 0

    def __post_init__(self) -> None:
        workspace_id = str(self.workspace_id or "").strip()
        upload_id = str(self.upload_id or "").strip()
        malware_scan_status = str(self.malware_scan_status or "clean").strip().lower()
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "upload_id", upload_id)
        object.__setattr__(self, "malware_scan_status", malware_scan_status)
        if not workspace_id:
            raise ValueError("file_upload.workspace_id_required")
        if not upload_id:
            raise ValueError("file_upload.upload_id_required")
        if self.observed_size_bytes is not None and self.observed_size_bytes <= 0:
            raise ValueError("file_upload.observed_size_invalid")
        if self.extracted_text_char_count < 0:
            raise ValueError("file_upload.extracted_text_char_count_invalid")


@dataclass(frozen=True)
class FileUploadRecord:
    upload_id: str
    workspace_id: str
    object_ref: str
    original_filename: str
    declared_mime_type: str
    declared_size_bytes: int
    upload_state: FileUploadState
    document_type: Optional[str] = None
    rejection_reason_code: Optional[FileUploadRejectionReason] = None
    observed_mime_type: Optional[str] = None
    observed_size_bytes: Optional[int] = None
    extracted_text_char_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    requested_by_user_ref: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        upload_id = str(self.upload_id or "").strip()
        workspace_id = str(self.workspace_id or "").strip()
        object_ref = str(self.object_ref or "").strip()
        state = str(self.upload_state or "").strip().lower()
        mime_type = str(self.declared_mime_type or "").strip().lower()
        object.__setattr__(self, "upload_id", upload_id)
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "object_ref", object_ref)
        object.__setattr__(self, "upload_state", state)
        object.__setattr__(self, "declared_mime_type", mime_type)
        if not upload_id:
            raise ValueError("FileUploadRecord.upload_id must be non-empty")
        if not workspace_id:
            raise ValueError("FileUploadRecord.workspace_id must be non-empty")
        if not object_ref:
            raise ValueError("FileUploadRecord.object_ref must be non-empty")
        if state not in FILE_UPLOAD_STATES:
            raise ValueError(f"Unsupported FileUploadRecord.upload_state: {state}")
        if self.declared_size_bytes <= 0:
            raise ValueError("FileUploadRecord.declared_size_bytes must be > 0")

    def to_row(self) -> dict[str, Any]:
        return {
            "upload_id": self.upload_id,
            "workspace_id": self.workspace_id,
            "object_ref": self.object_ref,
            "original_filename": self.original_filename,
            "declared_mime_type": self.declared_mime_type,
            "declared_size_bytes": self.declared_size_bytes,
            "upload_state": self.upload_state,
            "document_type": self.document_type,
            "rejection_reason_code": self.rejection_reason_code,
            "observed_mime_type": self.observed_mime_type,
            "observed_size_bytes": self.observed_size_bytes,
            "extracted_text_char_count": self.extracted_text_char_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "requested_by_user_ref": self.requested_by_user_ref,
            "metadata": dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class FileUploadEventRecord:
    event_id: str
    upload_id: str
    workspace_id: str
    event_type: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    reason_code: Optional[str] = None
    created_at: Optional[str] = None
    actor_user_ref: Optional[str] = None
    event_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        event_id = str(self.event_id or "").strip()
        upload_id = str(self.upload_id or "").strip()
        workspace_id = str(self.workspace_id or "").strip()
        event_type = str(self.event_type or "").strip().lower()
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "upload_id", upload_id)
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "event_type", event_type)
        if not event_id:
            raise ValueError("FileUploadEventRecord.event_id must be non-empty")
        if not upload_id:
            raise ValueError("FileUploadEventRecord.upload_id must be non-empty")
        if not workspace_id:
            raise ValueError("FileUploadEventRecord.workspace_id must be non-empty")
        if event_type not in _ALLOWED_EVENT_TYPES:
            raise ValueError(f"Unsupported FileUploadEventRecord.event_type: {event_type}")

    def to_row(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "upload_id": self.upload_id,
            "workspace_id": self.workspace_id,
            "event_type": self.event_type,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason_code": self.reason_code,
            "created_at": self.created_at,
            "actor_user_ref": self.actor_user_ref,
            "event_metadata": dict(self.event_metadata or {}),
        }


@dataclass(frozen=True)
class FileUploadPresignResponse:
    status: str
    upload: FileUploadRecord
    upload_url: str
    upload_method: str
    required_headers: Mapping[str, str]
    max_upload_bytes: int


@dataclass(frozen=True)
class FileUploadStatusResponse:
    status: str
    upload: FileUploadRecord
    events: tuple[FileUploadEventRecord, ...] = ()


@dataclass(frozen=True)
class FileUploadRejectedResponse:
    status: str
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    upload_id: Optional[str] = None
