from __future__ import annotations

from src.server.documents.file_ingestion_models import FileIngestionSafetyPolicy, FileUploadConfirmRequest, FileUploadPresignRequest
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_ingestion_api import FileIngestionService


def test_file_upload_rejects_oversized_presign_request() -> None:
    response = FileIngestionService.presign(
        FileUploadPresignRequest(
            workspace_id="ws_1",
            filename="huge.pdf",
            declared_mime_type="application/pdf",
            declared_size_bytes=1024,
        ),
        store=InMemoryFileUploadStore(),
        policy=FileIngestionSafetyPolicy(max_upload_bytes=100),
    )

    assert response.status == "rejected"
    assert response.reason_code == "file_upload.file_too_large"


def test_docx_confirm_accepts_zip_magic_prefix() -> None:
    store = InMemoryFileUploadStore()
    FileIngestionService.presign(
        FileUploadPresignRequest(
            workspace_id="ws_1",
            filename="brief.docx",
            declared_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            declared_size_bytes=128,
        ),
        store=store,
        upload_id_factory=lambda: "upl_docx",
    )

    response = FileIngestionService.confirm(
        FileUploadConfirmRequest(
            workspace_id="ws_1",
            upload_id="upl_docx",
            observed_size_bytes=128,
            observed_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            magic_bytes_hex="504b030414000600",
            extracted_text_char_count=100,
        ),
        store=store,
    )

    assert response.status == "safe"


def test_confirm_rejects_extraction_over_limit() -> None:
    store = InMemoryFileUploadStore()
    FileIngestionService.presign(
        FileUploadPresignRequest(
            workspace_id="ws_1",
            filename="brief.pdf",
            declared_mime_type="application/pdf",
            declared_size_bytes=128,
        ),
        store=store,
        upload_id_factory=lambda: "upl_pdf",
    )

    response = FileIngestionService.confirm(
        FileUploadConfirmRequest(
            workspace_id="ws_1",
            upload_id="upl_pdf",
            observed_size_bytes=128,
            observed_mime_type="application/pdf",
            magic_bytes_hex="255044462d",
            extracted_text_char_count=101,
        ),
        store=store,
        policy=FileIngestionSafetyPolicy(max_extracted_chars=100),
    )

    assert response.status == "rejected"
    assert response.upload.rejection_reason_code == "file_upload.extraction_over_limit"
