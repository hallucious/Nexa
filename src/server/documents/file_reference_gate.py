from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.server.documents.file_ingestion_models import FileUploadRecord

FileUploadReader = Callable[[str, str], Any | None]
FileExtractionReader = Callable[[str, str], Any | None]

_FILE_REF_KEYS = {"file_upload_id"}
_FILE_REF_LIST_KEYS = {"file_upload_ids", "file_upload_refs", "document_refs", "document_uploads"}
_FILE_EXTRACTION_REF_KEYS = {"file_extraction_id", "document_extraction_id"}
_FILE_EXTRACTION_REF_LIST_KEYS = {"file_extraction_ids", "file_extraction_refs", "document_text_refs", "extracted_document_refs"}


@dataclass(frozen=True)
class FileUploadSafetyDecision:
    upload_id: str
    allowed: bool
    reason_code: str
    message: str
    upload_state: Optional[str] = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "upload_id": self.upload_id,
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "message": self.message,
        }
        if self.upload_state is not None:
            payload["upload_state"] = self.upload_state
        return payload


@dataclass(frozen=True)
class FileExtractionSafetyDecision:
    extraction_id: str
    allowed: bool
    reason_code: str
    message: str
    extraction_state: Optional[str] = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "extraction_id": self.extraction_id,
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "message": self.message,
        }
        if self.extraction_state is not None:
            payload["extraction_state"] = self.extraction_state
        return payload


def _upload_id_from_candidate(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        source_type = str(value.get("source_type") or value.get("ref_type") or "").strip().lower()
        if source_type and source_type not in {"file_upload", "document_upload", "document"}:
            return None
        for key in ("file_upload_id", "upload_id", "id"):
            candidate = str(value.get(key) or "").strip()
            if candidate:
                return candidate
    return None


def _extraction_id_from_candidate(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        source_type = str(value.get("source_type") or value.get("ref_type") or "").strip().lower()
        if source_type and source_type not in {"file_extraction", "document_extraction", "extracted_document", "document_text"}:
            return None
        for key in ("file_extraction_id", "extraction_id", "id"):
            candidate = str(value.get(key) or "").strip()
            if candidate:
                return candidate
    return None


def collect_file_extraction_refs(payload: Any) -> tuple[str, ...]:
    refs: list[str] = []

    def visit(value: Any, *, key_hint: str | None = None) -> None:
        if key_hint in _FILE_EXTRACTION_REF_KEYS:
            ref = _extraction_id_from_candidate(value)
            if ref:
                refs.append(ref)
            return
        if key_hint in _FILE_EXTRACTION_REF_LIST_KEYS:
            if isinstance(value, (list, tuple)):
                for item in value:
                    ref = _extraction_id_from_candidate(item)
                    if ref:
                        refs.append(ref)
            else:
                ref = _extraction_id_from_candidate(value)
                if ref:
                    refs.append(ref)
            return
        if isinstance(value, Mapping):
            direct = _extraction_id_from_candidate(value)
            if direct and str(value.get("source_type") or value.get("ref_type") or "").strip().lower() in {"file_extraction", "document_extraction", "extracted_document", "document_text"}:
                refs.append(direct)
            for child_key, child_value in value.items():
                visit(child_value, key_hint=str(child_key))
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item, key_hint=None)

    visit(payload)
    return tuple(dict.fromkeys(refs))


def collect_file_upload_refs(payload: Any) -> tuple[str, ...]:
    refs: list[str] = []

    def visit(value: Any, *, key_hint: str | None = None) -> None:
        if key_hint in _FILE_REF_KEYS:
            ref = _upload_id_from_candidate(value)
            if ref:
                refs.append(ref)
            return
        if key_hint in _FILE_REF_LIST_KEYS:
            if isinstance(value, (list, tuple)):
                for item in value:
                    ref = _upload_id_from_candidate(item)
                    if ref:
                        refs.append(ref)
            else:
                ref = _upload_id_from_candidate(value)
                if ref:
                    refs.append(ref)
            return
        if isinstance(value, Mapping):
            direct = _upload_id_from_candidate(value)
            if direct and str(value.get("source_type") or value.get("ref_type") or "").strip().lower() in {"file_upload", "document_upload", "document"}:
                refs.append(direct)
            for child_key, child_value in value.items():
                visit(child_value, key_hint=str(child_key))
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item, key_hint=None)

    visit(payload)
    return tuple(dict.fromkeys(refs))


def _state_from_record(row: Any | None) -> str | None:
    if row is None:
        return None
    if isinstance(row, FileUploadRecord):
        return row.upload_state
    if isinstance(row, Mapping):
        return str(row.get("upload_state") or row.get("state") or "").strip().lower() or None
    return str(getattr(row, "upload_state", "") or getattr(row, "state", "")).strip().lower() or None


def evaluate_input_file_upload_safety(
    *,
    workspace_id: str,
    input_payload: Any,
    file_upload_reader: FileUploadReader | None,
) -> tuple[FileUploadSafetyDecision, ...]:
    refs = collect_file_upload_refs(input_payload)
    if not refs:
        return ()
    decisions: list[FileUploadSafetyDecision] = []
    if file_upload_reader is None:
        return tuple(
            FileUploadSafetyDecision(
                upload_id=ref,
                allowed=False,
                reason_code="file_upload.safety_lookup_unavailable",
                message="File upload safety state could not be verified.",
            )
            for ref in refs
        )
    for ref in refs:
        row = file_upload_reader(workspace_id, ref)
        state = _state_from_record(row)
        if state == "safe":
            decisions.append(FileUploadSafetyDecision(
                upload_id=ref,
                allowed=True,
                reason_code="file_upload.safe",
                message="File upload is safe for execution.",
                upload_state=state,
            ))
        elif state is None:
            decisions.append(FileUploadSafetyDecision(
                upload_id=ref,
                allowed=False,
                reason_code="file_upload.not_found",
                message="Referenced file upload was not found.",
            ))
        else:
            decisions.append(FileUploadSafetyDecision(
                upload_id=ref,
                allowed=False,
                reason_code=f"file_upload.not_safe.{state}",
                message="Referenced file upload is not safe for execution.",
                upload_state=state,
            ))
    return tuple(decisions)

def _extraction_state_from_record(row: Any | None) -> str | None:
    if row is None:
        return None
    if isinstance(row, Mapping):
        return str(row.get("extraction_state") or row.get("state") or "").strip().lower() or None
    return str(getattr(row, "extraction_state", "") or getattr(row, "state", "")).strip().lower() or None


def evaluate_input_file_extraction_safety(
    *,
    workspace_id: str,
    input_payload: Any,
    file_extraction_reader: FileExtractionReader | None,
) -> tuple[FileExtractionSafetyDecision, ...]:
    refs = collect_file_extraction_refs(input_payload)
    if not refs:
        return ()
    if file_extraction_reader is None:
        return tuple(
            FileExtractionSafetyDecision(
                extraction_id=ref,
                allowed=False,
                reason_code="file_extraction.safety_lookup_unavailable",
                message="File extraction safety state could not be verified.",
            )
            for ref in refs
        )
    decisions: list[FileExtractionSafetyDecision] = []
    for ref in refs:
        row = file_extraction_reader(workspace_id, ref)
        state = _extraction_state_from_record(row)
        if state == "extracted":
            decisions.append(FileExtractionSafetyDecision(
                extraction_id=ref,
                allowed=True,
                reason_code="file_extraction.extracted",
                message="File extraction is ready for execution.",
                extraction_state=state,
            ))
        elif state is None:
            decisions.append(FileExtractionSafetyDecision(
                extraction_id=ref,
                allowed=False,
                reason_code="file_extraction.not_found",
                message="Referenced file extraction was not found.",
            ))
        else:
            decisions.append(FileExtractionSafetyDecision(
                extraction_id=ref,
                allowed=False,
                reason_code=f"file_extraction.not_ready.{state}",
                message="Referenced file extraction is not ready for execution.",
                extraction_state=state,
            ))
    return tuple(decisions)

