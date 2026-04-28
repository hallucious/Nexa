from __future__ import annotations

from src.server.documents.file_ingestion_api import FileIngestionService
from src.server.documents.file_ingestion_models import FileUploadConfirmRequest, FileUploadPresignRequest
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_reference_gate import collect_file_upload_refs, evaluate_input_file_upload_safety
from src.server.http_route_models import HttpRouteRequest
from src.server.http_route_surface import RunHttpRouteSurface


def _auth_headers() -> dict[str, str]:
    return {
        "x-nexa-session-claims": '{"authenticated": true, "user_ref": "user_1", "role_refs": ["admin"]}'
    }


def test_file_upload_presign_accepts_supported_pdf() -> None:
    store = InMemoryFileUploadStore()
    response = FileIngestionService.presign(
        FileUploadPresignRequest(
            workspace_id="ws_1",
            filename="brief.pdf",
            declared_mime_type="application/pdf",
            declared_size_bytes=128,
            requested_by_user_ref="user_1",
        ),
        store=store,
        upload_id_factory=lambda: "upl_1",
        now_iso="2026-04-24T00:00:00+00:00",
    )

    assert response.status == "accepted"
    assert response.upload.upload_id == "upl_1"
    assert response.upload.upload_state == "pending_upload"
    assert store.get_workspace_upload("ws_1", "upl_1") is not None
    assert [event.event_type for event in store.list_events("upl_1")] == ["upload.presigned"]


def test_file_upload_presign_rejects_unsupported_type() -> None:
    store = InMemoryFileUploadStore()
    response = FileIngestionService.presign(
        FileUploadPresignRequest(
            workspace_id="ws_1",
            filename="brief.txt",
            declared_mime_type="text/plain",
            declared_size_bytes=128,
        ),
        store=store,
    )

    assert response.status == "rejected"
    assert response.reason_code == "file_upload.unsupported_mime_type"


def test_file_upload_confirm_promotes_clean_pdf_to_safe() -> None:
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
            malware_scan_status="clean",
            extracted_text_char_count=1200,
        ),
        store=store,
    )

    assert response.status == "safe"
    assert response.upload.upload_state == "safe"
    assert [event.to_state for event in response.events] == ["pending_upload", "quarantine", "scanning", "safe"]


def test_file_upload_confirm_rejects_magic_mismatch() -> None:
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
            magic_bytes_hex="504b0304",
            malware_scan_status="clean",
        ),
        store=store,
    )

    assert response.status == "rejected"
    assert response.upload.upload_state == "rejected"
    assert response.upload.rejection_reason_code == "file_upload.magic_byte_mismatch"


def test_collect_file_upload_refs_finds_nested_document_refs() -> None:
    refs = collect_file_upload_refs(
        {
            "question": "analyze",
            "documents": [
                {"source_type": "file_upload", "upload_id": "upl_a"},
                {"file_upload_id": "upl_b"},
            ],
            "nested": {"file_upload_refs": ["upl_c"]},
        }
    )

    assert refs == ("upl_a", "upl_b", "upl_c")


def test_file_upload_safety_gate_rejects_non_safe_refs() -> None:
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

    decisions = evaluate_input_file_upload_safety(
        workspace_id="ws_1",
        input_payload={"file_upload_id": "upl_1"},
        file_upload_reader=store.get_workspace_upload,
    )

    assert len(decisions) == 1
    assert decisions[0].allowed is False
    assert decisions[0].reason_code == "file_upload.not_safe.pending_upload"


def test_file_upload_http_routes_presign_confirm_and_status() -> None:
    store = InMemoryFileUploadStore()
    presign = RunHttpRouteSurface.handle_presign_file_upload(
        http_request=HttpRouteRequest(
            method="POST",
            path="/api/workspaces/ws_1/uploads/presign",
            headers=_auth_headers(),
            json_body={
                "filename": "brief.pdf",
                "declared_mime_type": "application/pdf",
                "declared_size_bytes": 128,
            },
        ),
        workspace_id="ws_1",
        file_upload_store=store,
    )
    assert presign.status_code == 202
    upload_id = presign.body["upload"]["upload_id"]

    confirm = RunHttpRouteSurface.handle_confirm_file_upload(
        http_request=HttpRouteRequest(
            method="POST",
            path=f"/api/workspaces/ws_1/uploads/{upload_id}/confirm",
            headers=_auth_headers(),
            json_body={
                "observed_size_bytes": 128,
                "observed_mime_type": "application/pdf",
                "magic_bytes_hex": "255044462d312e37",
                "malware_scan_status": "clean",
            },
        ),
        workspace_id="ws_1",
        upload_id=upload_id,
        file_upload_store=store,
    )
    assert confirm.status_code == 200
    assert confirm.body["status"] == "safe"

    status = RunHttpRouteSurface.handle_file_upload_status(
        http_request=HttpRouteRequest(
            method="GET",
            path=f"/api/workspaces/ws_1/uploads/{upload_id}",
            headers=_auth_headers(),
        ),
        workspace_id="ws_1",
        upload_id=upload_id,
        file_upload_store=store,
    )
    assert status.status_code == 200
    assert status.body["upload"]["upload_state"] == "safe"
