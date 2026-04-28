from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Optional

from src.server.documents.file_extraction_api import FileExtractionService
from src.server.documents.file_extraction_models import FileExtractionCompleteRequest, FileExtractionFailureRequest
from src.server.documents.file_extraction_store import InMemoryFileExtractionStore
from src.server.documents.file_ingestion_models import FileIngestionSafetyPolicy
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_parser_adapters import DocumentTextExtractionResult, extract_document_text
from src.server.documents.file_text_artifact_store import InMemoryExtractedTextArtifactStore


ObjectBytesReader = Callable[[str], bytes]
TextArtifactWriter = Callable[..., Any]


@dataclass(frozen=True)
class FileExtractionWorkerResult:
    status: str
    extraction_id: Optional[str] = None
    workspace_id: Optional[str] = None
    upload_id: Optional[str] = None
    text_artifact_ref: Optional[str] = None
    reason_code: Optional[str] = None
    message: Optional[str] = None

    def to_payload(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def _artifact_ref_from_writer_result(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        return str(value.get("artifact_ref") or value.get("text_artifact_ref") or value.get("ref") or "").strip() or None
    return str(getattr(value, "artifact_ref", "") or getattr(value, "text_artifact_ref", "") or "").strip() or None


def _write_text_artifact(
    *,
    artifact_store: InMemoryExtractedTextArtifactStore | None,
    text_artifact_writer: TextArtifactWriter | None,
    workspace_id: str,
    extraction_id: str,
    result: DocumentTextExtractionResult,
    now_iso: str | None,
) -> str:
    metadata = {
        "document_type": result.document_type,
        "parser_ref": result.parser_ref,
        "warnings": list(result.warnings),
        "extracted_text_char_count": result.extracted_text_char_count,
    }
    if text_artifact_writer is not None:
        written = text_artifact_writer(
            workspace_id=workspace_id,
            extraction_id=extraction_id,
            text=result.text,
            content_hash=result.content_hash,
            metadata=metadata,
            created_at=now_iso,
        )
        ref = _artifact_ref_from_writer_result(written)
        if ref:
            return ref
    store = artifact_store or InMemoryExtractedTextArtifactStore()
    artifact = store.write_text_artifact(
        workspace_id=workspace_id,
        extraction_id=extraction_id,
        text=result.text,
        content_hash=result.content_hash,
        metadata=metadata,
        created_at=now_iso,
    )
    return artifact.artifact_ref


def run_file_extraction(
    *,
    workspace_id: str,
    extraction_id: str,
    upload_store: InMemoryFileUploadStore,
    extraction_store: InMemoryFileExtractionStore,
    object_bytes_reader: ObjectBytesReader,
    artifact_store: InMemoryExtractedTextArtifactStore | None = None,
    text_artifact_writer: TextArtifactWriter | None = None,
    policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
    extractor_ref: str = "builtin_document_text_worker_v1",
    now_iso: str | None = None,
) -> FileExtractionWorkerResult:
    _ = upload_store
    started = FileExtractionService.start_extraction(
        workspace_id=workspace_id,
        extraction_id=extraction_id,
        extraction_store=extraction_store,
        now_iso=now_iso,
        extractor_ref=extractor_ref,
    )
    if getattr(started, "status", None) == "rejected":
        return FileExtractionWorkerResult(
            status="skipped",
            extraction_id=extraction_id,
            workspace_id=workspace_id,
            reason_code=getattr(started, "reason_code", "file_extraction.not_startable"),
            message=getattr(started, "message", "Extraction could not be started."),
        )

    record = started.extraction
    try:
        if not record.source_object_ref:
            raise ValueError("file_extraction.source_object_ref_missing")
        document_bytes = object_bytes_reader(record.source_object_ref)
        parse_result = extract_document_text(document_bytes=document_bytes, document_type=record.source_document_type)
        artifact_ref = _write_text_artifact(
            artifact_store=artifact_store,
            text_artifact_writer=text_artifact_writer,
            workspace_id=record.workspace_id,
            extraction_id=record.extraction_id,
            result=parse_result,
            now_iso=now_iso,
        )
        completed = FileExtractionService.complete_extraction(
            FileExtractionCompleteRequest(
                workspace_id=record.workspace_id,
                extraction_id=record.extraction_id,
                extracted_text_char_count=parse_result.extracted_text_char_count,
                text_artifact_ref=artifact_ref,
                text_preview=parse_result.text_preview,
                content_hash=parse_result.content_hash,
                extractor_ref=extractor_ref,
                completion_metadata={"parser_ref": parse_result.parser_ref, "warnings": list(parse_result.warnings)},
            ),
            extraction_store=extraction_store,
            policy=policy,
            now_iso=now_iso,
        )
        return FileExtractionWorkerResult(
            status=completed.status,
            extraction_id=record.extraction_id,
            workspace_id=record.workspace_id,
            upload_id=record.upload_id,
            text_artifact_ref=completed.extraction.text_artifact_ref,
        )
    except Exception as exc:  # noqa: BLE001
        reason = str(exc) if str(exc).startswith("file_extraction.") else "file_extraction.worker_failed"
        failed = FileExtractionService.fail_extraction(
            FileExtractionFailureRequest(
                workspace_id=record.workspace_id,
                extraction_id=record.extraction_id,
                reason_code=reason,
                message=str(exc) or "Document extraction worker failed.",
                extractor_ref=extractor_ref,
            ),
            extraction_store=extraction_store,
            now_iso=now_iso,
        )
        return FileExtractionWorkerResult(
            status="failed",
            extraction_id=record.extraction_id,
            workspace_id=record.workspace_id,
            upload_id=record.upload_id,
            reason_code=getattr(failed.extraction, "rejection_reason_code", reason),
            message=str(exc) or "Document extraction worker failed.",
        )


def run_next_file_extraction(
    *,
    upload_store: InMemoryFileUploadStore,
    extraction_store: InMemoryFileExtractionStore,
    object_bytes_reader: ObjectBytesReader,
    artifact_store: InMemoryExtractedTextArtifactStore | None = None,
    text_artifact_writer: TextArtifactWriter | None = None,
    policy: FileIngestionSafetyPolicy = FileIngestionSafetyPolicy(),
    workspace_id: str | None = None,
    extractor_ref: str = "builtin_document_text_worker_v1",
    now_iso: str | None = None,
) -> FileExtractionWorkerResult:
    queued = extraction_store.list_queued_extractions(workspace_id=workspace_id, limit=1)
    if not queued:
        return FileExtractionWorkerResult(status="idle", reason_code="file_extraction.no_queued_work", message="No queued file extraction work is available.")
    record = queued[0]
    return run_file_extraction(
        workspace_id=record.workspace_id,
        extraction_id=record.extraction_id,
        upload_store=upload_store,
        extraction_store=extraction_store,
        object_bytes_reader=object_bytes_reader,
        artifact_store=artifact_store,
        text_artifact_writer=text_artifact_writer,
        policy=policy,
        extractor_ref=extractor_ref,
        now_iso=now_iso,
    )
