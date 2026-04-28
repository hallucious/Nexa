from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from src.server.documents.file_extraction_api import FileExtractionService
from src.server.documents.file_extraction_models import FileExtractionRequest
from src.server.documents.file_extraction_store import InMemoryFileExtractionStore
from src.server.documents.file_extraction_worker import run_next_file_extraction
from src.server.documents.file_ingestion_models import FileUploadRecord
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_parser_adapters import extract_text_from_pdf_bytes
from src.server.documents.file_text_artifact_store import InMemoryExtractedTextArtifactStore
from src.server.queue.cleanup_jobs import reject_stale_file_extractions


def _docx_bytes(text: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as docx:
        docx.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>"
                + text
                + "</w:t></w:r></w:p></w:body></w:document>"
            ),
        )
    return buffer.getvalue()


def _safe_upload(*, upload_id: str = "upl_docx_1", document_type: str = "docx", object_ref: str = "memory://docx/1") -> FileUploadRecord:
    return FileUploadRecord(
        upload_id=upload_id,
        workspace_id="ws_1",
        object_ref=object_ref,
        original_filename="brief.docx" if document_type == "docx" else "brief.pdf",
        declared_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if document_type == "docx" else "application/pdf",
        declared_size_bytes=128,
        upload_state="safe",
        document_type=document_type,
        observed_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if document_type == "docx" else "application/pdf",
        observed_size_bytes=128,
        created_at="2026-04-28T00:00:00+00:00",
        updated_at="2026-04-28T00:00:00+00:00",
        requested_by_user_ref="user_1",
    )


def test_docx_extraction_worker_completes_and_writes_text_artifact() -> None:
    upload_store = InMemoryFileUploadStore()
    extraction_store = InMemoryFileExtractionStore()
    artifact_store = InMemoryExtractedTextArtifactStore()
    upload_store.write_upload(_safe_upload())

    requested = FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_docx_1", requested_by_user_ref="user_1"),
        upload_store=upload_store,
        extraction_store=extraction_store,
        extraction_id_factory=lambda: "fex_docx_1",
        now_iso="2026-04-28T00:01:00+00:00",
    )
    assert requested.status == "queued"

    result = run_next_file_extraction(
        upload_store=upload_store,
        extraction_store=extraction_store,
        object_bytes_reader=lambda object_ref: _docx_bytes("Hello extracted DOCX text") if object_ref == "memory://docx/1" else b"",
        artifact_store=artifact_store,
        now_iso="2026-04-28T00:02:00+00:00",
    )

    assert result.status == "extracted"
    assert result.extraction_id == "fex_docx_1"
    record = extraction_store.get_workspace_extraction("ws_1", "fex_docx_1")
    assert record is not None
    assert record.extraction_state == "extracted"
    assert record.text_artifact_ref == "extracted-text://ws_1/fex_docx_1"
    assert record.extracted_text_char_count == len("Hello extracted DOCX text")
    assert "Hello extracted DOCX text" in (record.text_preview or "")
    artifact = artifact_store.get_text_artifact("extracted-text://ws_1/fex_docx_1")
    assert artifact is not None
    assert artifact.text == "Hello extracted DOCX text"
    event_types = [event.event_type for event in extraction_store.list_events("fex_docx_1")]
    assert event_types == ["extraction.requested", "extraction.started", "extraction.completed"]


def test_pdf_minimum_parser_extracts_literal_text_chunks() -> None:
    result = extract_text_from_pdf_bytes(b"%PDF-1.4\nBT /F1 12 Tf (Hello PDF text) Tj ET\n%%EOF")
    assert result.document_type == "pdf"
    assert result.text == "Hello PDF text"
    assert result.extracted_text_char_count == len("Hello PDF text")
    assert result.parser_ref == "builtin_pdf_text_minimum_v1"


def test_extraction_worker_marks_parser_failure_as_failed() -> None:
    upload_store = InMemoryFileUploadStore()
    extraction_store = InMemoryFileExtractionStore()
    upload_store.write_upload(_safe_upload(upload_id="upl_pdf_bad", document_type="pdf", object_ref="memory://pdf/bad"))

    FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_pdf_bad", requested_by_user_ref="user_1"),
        upload_store=upload_store,
        extraction_store=extraction_store,
        extraction_id_factory=lambda: "fex_pdf_bad",
        now_iso="2026-04-28T00:01:00+00:00",
    )

    result = run_next_file_extraction(
        upload_store=upload_store,
        extraction_store=extraction_store,
        object_bytes_reader=lambda _object_ref: b"not a pdf",
        now_iso="2026-04-28T00:02:00+00:00",
    )

    assert result.status == "failed"
    record = extraction_store.get_workspace_extraction("ws_1", "fex_pdf_bad")
    assert record is not None
    assert record.extraction_state == "failed"
    assert record.rejection_reason_code == "file_extraction.parser.pdf_magic_mismatch"
    assert [event.event_type for event in extraction_store.list_events("fex_pdf_bad")] == [
        "extraction.requested",
        "extraction.started",
        "extraction.failed",
    ]


def test_stale_file_extraction_cleanup_rejects_non_terminal_rows() -> None:
    upload_store = InMemoryFileUploadStore()
    extraction_store = InMemoryFileExtractionStore()
    upload_store.write_upload(_safe_upload(upload_id="upl_stale", object_ref="memory://docx/stale"))

    FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_stale", requested_by_user_ref="user_1"),
        upload_store=upload_store,
        extraction_store=extraction_store,
        extraction_id_factory=lambda: "fex_stale",
        now_iso="2026-04-28T00:00:00+00:00",
    )

    result = reject_stale_file_extractions(
        extraction_store=extraction_store,
        stale_after_s=60,
        now_iso="2026-04-28T00:02:00+00:00",
    )

    assert result.stale_found == 1
    assert result.rejected == 1
    record = extraction_store.get_workspace_extraction("ws_1", "fex_stale")
    assert record is not None
    assert record.extraction_state == "rejected"
    assert record.rejection_reason_code == "file_extraction.stale_worker_timeout"
    assert [event.event_type for event in extraction_store.list_events("fex_stale")] == [
        "extraction.requested",
        "extraction.rejected",
    ]
