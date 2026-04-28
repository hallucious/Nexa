from __future__ import annotations

from pathlib import PurePath
from typing import Optional

from src.server.documents.file_ingestion_models import (
    FileIngestionSafetyPolicy,
    FileUploadConfirmRequest,
    FileUploadPresignRequest,
    FileUploadRecord,
    SUPPORTED_DOCUMENT_TYPES,
)


def document_type_for_mime(mime_type: str) -> str | None:
    spec = SUPPORTED_DOCUMENT_TYPES.get(str(mime_type or "").strip().lower())
    if not spec:
        return None
    return str(spec["document_type"])


def _extension(filename: str) -> str:
    return PurePath(str(filename or "")).suffix.lower()


def validate_presign_request(
    request: FileUploadPresignRequest,
    *,
    policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
) -> tuple[bool, str | None, str | None]:
    if request.declared_size_bytes > policy.max_upload_bytes:
        return False, "file_upload.file_too_large", "File exceeds the maximum upload size."
    spec = SUPPORTED_DOCUMENT_TYPES.get(request.declared_mime_type)
    if spec is None:
        return False, "file_upload.unsupported_mime_type", "File type is not supported."
    allowed_extensions = tuple(str(item) for item in spec.get("extensions", ()))
    if _extension(request.filename) not in allowed_extensions:
        return False, "file_upload.extension_mismatch", "Filename extension does not match the declared document type."
    return True, None, None


def _magic_bytes_from_hex(value: str | None) -> bytes:
    if value is None:
        return b""
    stripped = str(value or "").strip().replace(" ", "")
    if not stripped:
        return b""
    try:
        return bytes.fromhex(stripped)
    except ValueError:
        return b""


def validate_confirm_request(
    request: FileUploadConfirmRequest,
    existing: FileUploadRecord,
    *,
    policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
) -> tuple[bool, str | None, str | None]:
    if existing.upload_state not in {"pending_upload", "quarantine", "scanning"}:
        return False, "file_upload.state_not_confirmable", "Upload is not in a confirmable state."
    observed_size = request.observed_size_bytes or existing.declared_size_bytes
    if observed_size > policy.max_upload_bytes:
        return False, "file_upload.file_too_large", "File exceeds the maximum upload size."
    observed_mime = str(request.observed_mime_type or existing.declared_mime_type or "").strip().lower()
    if observed_mime != existing.declared_mime_type:
        return False, "file_upload.mime_mismatch", "Observed MIME type does not match the declared MIME type."
    spec = SUPPORTED_DOCUMENT_TYPES.get(existing.declared_mime_type)
    if spec is None:
        return False, "file_upload.unsupported_mime_type", "File type is not supported."
    if policy.require_magic_bytes_on_confirm:
        magic = _magic_bytes_from_hex(request.magic_bytes_hex)
        if not magic:
            return False, "file_upload.magic_bytes_required", "File signature could not be verified."
        allowed_prefixes = tuple(spec.get("magic_prefixes", ()))
        if not any(magic.startswith(prefix) for prefix in allowed_prefixes):
            return False, "file_upload.magic_byte_mismatch", "File signature does not match the declared document type."
    if request.malware_scan_status in {"infected", "malware", "unsafe"}:
        return False, "file_upload.malware_detected", "File scanner rejected the uploaded file."
    if request.malware_scan_status in {"timeout", "unavailable", "failed", "error"}:
        return False, f"file_upload.scan_{request.malware_scan_status}", "File scanner could not clear the uploaded file."
    if request.extracted_text_char_count > policy.max_extracted_chars:
        return False, "file_upload.extraction_over_limit", "Extracted document text exceeds the configured limit."
    return True, None, None
