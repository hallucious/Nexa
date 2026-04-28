from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest

from src.server.documents.file_extraction_api import FileExtractionService
from src.server.documents.file_extraction_models import FileExtractionRequest
from src.server.documents.file_extraction_store import InMemoryFileExtractionStore
from src.server.documents.file_extraction_worker import run_next_file_extraction
from src.server.documents.file_ingestion_api import FileIngestionService
from src.server.documents.file_ingestion_models import (
    FileUploadConfirmRequest,
    FileUploadPresignRequest,
    FileUploadRecord,
)
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_parser_adapters import extract_text_from_pdf_bytes
from src.server.documents.file_text_artifact_store import InMemoryExtractedTextArtifactStore
from src.server.first_success_blockers import FirstSuccessBlocker, build_first_success_preflight_summary
from src.server.provider_catalog_runtime import default_provider_model_catalog_rows


def _provider_source(provider: str = "openai", model: str = "gpt-4o") -> dict:
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "commit_snapshot", "commit_id": "snap_1"},
        "circuit": {
            "nodes": [
                {
                    "node_id": "n_provider",
                    "kind": "provider",
                    "execution": {
                        "provider": {
                            "provider_id": f"{provider}:default",
                            "model": model,
                            "prompt_ref": "prompt.main",
                        }
                    },
                }
            ],
            "edges": [],
            "entry": "n_provider",
            "outputs": [{"name": "result", "source": "state.working.result"}],
        },
        "resources": {
            "prompts": {"prompt.main": {"template": "Hello"}},
            "providers": {provider: {"provider_family": provider}},
            "plugins": {},
        },
        "state": {"input": {}, "working": {}, "memory": {}},
    }


def _safe_upload(*, upload_id: str = "upl_doc_1", document_type: str = "docx") -> FileUploadRecord:
    return FileUploadRecord(
        upload_id=upload_id,
        workspace_id="ws_1",
        object_ref=f"memory://{document_type}/1",
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


def test_first_success_preflight_summary_collects_provider_file_and_extraction_blockers_without_raw_text() -> None:
    input_payload = {
        "document_refs": [{"upload_id": "upl_1", "text_preview": "RAW FILE TEXT SHOULD NOT LEAK"}],
        "document_text_refs": [{"file_extraction_id": "fex_1", "text": "RAW EXTRACTED TEXT SHOULD NOT LEAK"}],
    }

    summary = build_first_success_preflight_summary(
        workspace_id="ws_1",
        source_payload=_provider_source("openai", "gpt-4o"),
        input_payload=input_payload,
        plan_key="free",
        provider_model_catalog_rows=default_provider_model_catalog_rows(),
        file_upload_reader=lambda workspace_id, upload_id: {
            "upload_state": "scanning",
            "text_preview": "RAW FILE TEXT SHOULD NOT LEAK",
        },
        file_extraction_reader=lambda workspace_id, extraction_id: {
            "extraction_state": "failed",
            "text": "RAW EXTRACTED TEXT SHOULD NOT LEAK",
        },
    )

    assert summary.ready is False
    reason_codes = {blocker.reason_code for blocker in summary.blockers}
    assert reason_codes == {
        "provider_model_access.plan_not_allowed",
        "file_upload.not_safe.scanning",
        "file_extraction.not_ready.failed",
    }
    assert summary.estimated_total_cost_ratio == 3.0

    payload_text = str(summary.to_payload())
    assert "RAW FILE TEXT SHOULD NOT LEAK" not in payload_text
    assert "RAW EXTRACTED TEXT SHOULD NOT LEAK" not in payload_text


def test_first_success_preflight_summary_ready_for_allowed_provider_safe_upload_and_extracted_text() -> None:
    summary = build_first_success_preflight_summary(
        workspace_id="ws_1",
        source_payload=_provider_source("anthropic", "claude-haiku-3"),
        input_payload={"file_upload_id": "upl_1", "file_extraction_id": "fex_1"},
        plan_key="free",
        provider_model_catalog_rows=default_provider_model_catalog_rows(),
        file_upload_reader=lambda workspace_id, upload_id: {"upload_state": "safe"},
        file_extraction_reader=lambda workspace_id, extraction_id: {"extraction_state": "extracted"},
    )

    assert summary.ready is True
    assert summary.blockers == ()
    assert summary.estimated_total_cost_ratio == 1.0


def test_first_success_blocker_redacts_sensitive_detail_keys_recursively() -> None:
    blocker = FirstSuccessBlocker(
        family="file_extraction",
        reason_code="example",
        message="Example blocker.",
        next_action="Fix it.",
        details={
            "safe": "kept",
            "text": "do not leak",
            "nested": [{"document_text": "do not leak nested", "state": "failed"}],
        },
    )

    payload = blocker.to_payload()
    assert payload["details"]["safe"] == "kept"
    assert payload["details"]["text"] == "[redacted]"
    assert payload["details"]["nested"][0]["document_text"] == "[redacted]"
    assert payload["details"]["nested"][0]["state"] == "failed"


def test_file_upload_confirm_rejects_scanner_timeout_and_unavailable_as_uncleared() -> None:
    for scan_status, expected_reason in [
        ("timeout", "file_upload.scan_timeout"),
        ("unavailable", "file_upload.scan_unavailable"),
    ]:
        store = InMemoryFileUploadStore()
        FileIngestionService.presign(
            FileUploadPresignRequest(
                workspace_id="ws_1",
                filename="brief.pdf",
                declared_mime_type="application/pdf",
                declared_size_bytes=128,
            ),
            store=store,
            upload_id_factory=lambda: "upl_1",
        )

        response = FileIngestionService.confirm(
            FileUploadConfirmRequest(
                workspace_id="ws_1",
                upload_id="upl_1",
                observed_size_bytes=128,
                observed_mime_type="application/pdf",
                magic_bytes_hex="255044462d312e37",
                malware_scan_status=scan_status,
            ),
            store=store,
        )

        assert response.status == "rejected"
        assert response.upload.upload_state == "rejected"
        assert response.upload.rejection_reason_code == expected_reason


def test_pdf_parser_rejects_protected_or_malformed_pdf_before_text_handoff() -> None:
    with pytest.raises(ValueError, match="file_extraction.parser.pdf_encrypted_or_protected"):
        extract_text_from_pdf_bytes(b"%PDF-1.7\n1 0 obj << /Encrypt 2 0 R >> endobj\n%%EOF")

    with pytest.raises(ValueError, match="file_extraction.parser.pdf_eof_missing"):
        extract_text_from_pdf_bytes(b"%PDF-1.7\nBT (looks plausible but has no EOF) Tj ET")


def test_extraction_worker_events_and_result_payload_do_not_include_raw_text() -> None:
    raw_text = "Sensitive extracted text should live only in the artifact store"
    upload_store = InMemoryFileUploadStore()
    extraction_store = InMemoryFileExtractionStore()
    artifact_store = InMemoryExtractedTextArtifactStore()
    upload_store.write_upload(_safe_upload())

    requested = FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_doc_1", requested_by_user_ref="user_1"),
        upload_store=upload_store,
        extraction_store=extraction_store,
        extraction_id_factory=lambda: "fex_doc_1",
        now_iso="2026-04-28T00:01:00+00:00",
    )
    assert requested.status == "queued"

    result = run_next_file_extraction(
        upload_store=upload_store,
        extraction_store=extraction_store,
        object_bytes_reader=lambda object_ref: _docx_bytes(raw_text),
        artifact_store=artifact_store,
        now_iso="2026-04-28T00:02:00+00:00",
    )

    assert result.status == "extracted"
    assert raw_text not in str(result.to_payload())
    assert raw_text not in str([event.event_metadata for event in extraction_store.list_events("fex_doc_1")])

    artifact = artifact_store.get_text_artifact("extracted-text://ws_1/fex_doc_1")
    assert artifact is not None
    assert artifact.text == raw_text
