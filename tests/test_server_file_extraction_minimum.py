from __future__ import annotations

from sqlalchemy import create_engine, text

from src.server.documents.file_extraction_api import FileExtractionService
from src.server.documents.file_extraction_models import FileExtractionCompleteRequest, FileExtractionRequest
from src.server.documents.file_extraction_store import InMemoryFileExtractionStore
from src.server.documents.file_ingestion_api import FileIngestionService
from src.server.documents.file_ingestion_models import FileIngestionSafetyPolicy, FileUploadConfirmRequest, FileUploadPresignRequest
from src.server.documents.file_ingestion_store import InMemoryFileUploadStore
from src.server.documents.file_reference_gate import collect_file_extraction_refs, evaluate_input_file_extraction_safety
from src.server.pg.row_stores import PostgresFileExtractionStore


def _safe_upload_store() -> InMemoryFileUploadStore:
    store = InMemoryFileUploadStore()
    FileIngestionService.presign(
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
    FileIngestionService.confirm(
        FileUploadConfirmRequest(
            workspace_id="ws_1",
            upload_id="upl_1",
            observed_size_bytes=128,
            observed_mime_type="application/pdf",
            magic_bytes_hex="255044462d312e37",
            malware_scan_status="clean",
            extracted_text_char_count=100,
        ),
        store=store,
        now_iso="2026-04-24T00:00:01+00:00",
    )
    return store


def test_file_extraction_request_requires_safe_upload() -> None:
    upload_store = InMemoryFileUploadStore()
    extraction_store = InMemoryFileExtractionStore()
    FileIngestionService.presign(
        FileUploadPresignRequest(
            workspace_id="ws_1",
            filename="brief.pdf",
            declared_mime_type="application/pdf",
            declared_size_bytes=128,
        ),
        store=upload_store,
        upload_id_factory=lambda: "upl_pending",
    )

    response = FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_pending"),
        upload_store=upload_store,
        extraction_store=extraction_store,
    )

    assert response.status == "rejected"
    assert response.reason_code == "file_extraction.upload_not_safe.pending_upload"


def test_file_extraction_lifecycle_promotes_safe_upload_to_extracted_text_artifact() -> None:
    upload_store = _safe_upload_store()
    extraction_store = InMemoryFileExtractionStore()

    requested = FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_1", requested_by_user_ref="user_1"),
        upload_store=upload_store,
        extraction_store=extraction_store,
        extraction_id_factory=lambda: "fex_1",
        now_iso="2026-04-24T00:01:00+00:00",
    )
    assert requested.status == "queued"
    assert requested.extraction.extraction_id == "fex_1"
    assert requested.extraction.source_document_type == "pdf"
    assert requested.extraction.source_object_ref == "quarantine://uploads/ws_1/upl_1"

    started = FileExtractionService.start_extraction(
        workspace_id="ws_1",
        extraction_id="fex_1",
        extraction_store=extraction_store,
        extractor_ref="extractor:unit",
        now_iso="2026-04-24T00:01:01+00:00",
    )
    assert started.status == "extracting"

    completed = FileExtractionService.complete_extraction(
        FileExtractionCompleteRequest(
            workspace_id="ws_1",
            extraction_id="fex_1",
            extracted_text_char_count=42,
            text_preview="hello world",
            content_hash="sha256:abc",
            extractor_ref="extractor:unit",
        ),
        extraction_store=extraction_store,
        now_iso="2026-04-24T00:01:02+00:00",
    )

    assert completed.status == "extracted"
    assert completed.extraction.extraction_state == "extracted"
    assert completed.extraction.text_artifact_ref == "extracted-text://ws_1/fex_1"
    assert completed.extraction.extracted_text_char_count == 42
    assert [event.event_type for event in completed.events] == [
        "extraction.requested",
        "extraction.started",
        "extraction.completed",
    ]


def test_file_extraction_rejects_text_over_safety_limit() -> None:
    upload_store = _safe_upload_store()
    extraction_store = InMemoryFileExtractionStore()
    FileExtractionService.request_extraction(
        FileExtractionRequest(workspace_id="ws_1", upload_id="upl_1"),
        upload_store=upload_store,
        extraction_store=extraction_store,
        extraction_id_factory=lambda: "fex_1",
    )

    response = FileExtractionService.complete_extraction(
        FileExtractionCompleteRequest(
            workspace_id="ws_1",
            extraction_id="fex_1",
            extracted_text_char_count=101,
        ),
        extraction_store=extraction_store,
        policy=FileIngestionSafetyPolicy(max_extracted_chars=100),
    )

    assert response.status == "rejected"
    assert response.extraction.extraction_state == "rejected"
    assert response.extraction.rejection_reason_code == "file_extraction.extraction_over_limit"


def test_collect_file_extraction_refs_and_safety_gate_require_extracted_state() -> None:
    extraction_store = InMemoryFileExtractionStore()
    extraction_store.write_extraction({
        "extraction_id": "fex_ready",
        "workspace_id": "ws_1",
        "upload_id": "upl_1",
        "extraction_state": "extracted",
    })
    extraction_store.write_extraction({
        "extraction_id": "fex_pending",
        "workspace_id": "ws_1",
        "upload_id": "upl_2",
        "extraction_state": "queued",
    })

    payload = {
        "documents": [
            {"source_type": "file_extraction", "extraction_id": "fex_ready"},
            {"file_extraction_id": "fex_pending"},
        ],
        "nested": {"document_text_refs": ["fex_missing"]},
    }
    assert collect_file_extraction_refs(payload) == ("fex_ready", "fex_pending", "fex_missing")

    decisions = evaluate_input_file_extraction_safety(
        workspace_id="ws_1",
        input_payload=payload,
        file_extraction_reader=extraction_store.get_workspace_extraction,
    )

    assert [decision.allowed for decision in decisions] == [True, False, False]
    assert decisions[1].reason_code == "file_extraction.not_ready.queued"
    assert decisions[2].reason_code == "file_extraction.not_found"


def test_postgres_file_extraction_store_round_trips_extractions_and_events() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE file_extractions (
                extraction_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                upload_id TEXT NOT NULL,
                extraction_state TEXT NOT NULL,
                source_document_type TEXT,
                source_object_ref TEXT,
                text_artifact_ref TEXT,
                extracted_text_char_count INTEGER,
                text_preview TEXT,
                content_hash TEXT,
                rejection_reason_code TEXT,
                extractor_ref TEXT,
                created_at TEXT,
                updated_at TEXT,
                requested_by_user_ref TEXT,
                metadata TEXT
            )
        """))
        connection.execute(text("""
            CREATE TABLE file_extraction_events (
                event_id TEXT PRIMARY KEY,
                extraction_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                upload_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                reason_code TEXT,
                created_at TEXT,
                actor_user_ref TEXT,
                event_metadata TEXT
            )
        """))

    store = PostgresFileExtractionStore(engine)
    store.write_extraction({
        "extraction_id": "fex_pg",
        "workspace_id": "ws_1",
        "upload_id": "upl_1",
        "extraction_state": "queued",
        "source_document_type": "pdf",
        "created_at": "2026-04-24T00:00:00+00:00",
        "updated_at": "2026-04-24T00:00:00+00:00",
        "metadata": {"seed": True},
    })
    store.update_extraction_state(
        extraction_id="fex_pg",
        extraction_state="extracted",
        text_artifact_ref="extracted-text://ws_1/fex_pg",
        extracted_text_char_count=55,
        updated_at="2026-04-24T00:01:00+00:00",
    )
    store.append_event({
        "event_id": "evt_1",
        "extraction_id": "fex_pg",
        "workspace_id": "ws_1",
        "upload_id": "upl_1",
        "event_type": "extraction.completed",
        "from_state": "extracting",
        "to_state": "extracted",
        "created_at": "2026-04-24T00:01:00+00:00",
        "event_metadata": {"ok": True},
    })

    row = store.get_workspace_extraction("ws_1", "fex_pg")
    assert row is not None
    assert row.extraction_state == "extracted"
    assert row.text_artifact_ref == "extracted-text://ws_1/fex_pg"
    assert store.list_upload_extractions("ws_1", "upl_1")[0].extraction_id == "fex_pg"
    assert store.list_events("fex_pg")[0].event_metadata == {"ok": True}


def test_file_extractions_migration_declares_incremental_tables() -> None:
    migration_text = open("alembic/versions/20260424_0008_file_extractions.py", encoding="utf-8").read()
    assert 'revision = "20260424_0008"' in migration_text
    assert 'down_revision = "20260424_0007"' in migration_text
    assert '"file_extractions"' in migration_text
    assert '"file_extraction_events"' in migration_text

from src.server import (
    ExecutionTargetCatalogEntry,
    ProductExecutionTarget,
    ProductRunLaunchRequest,
    RequestAuthResolver,
    RunAdmissionService,
    WorkspaceAuthorizationContext,
)


def _auth_context_for_extraction_gate():
    return RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token"},
        session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 500, "roles": ["editor"]},
        now_epoch_s=100,
    )


def _workspace_for_extraction_gate() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws_1",
        owner_user_ref="user-owner",
        collaborator_user_refs=(),
        viewer_user_refs=(),
    )


def _commit_snapshot_for_extraction_gate(ref: str = "snap-extract-001") -> dict:
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "commit_snapshot", "commit_id": ref},
        "circuit": {"nodes": [], "edges": [], "entry": "n1", "outputs": [{"name": "x", "source": "state.working.x"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "validation": {"validation_result": "passed", "summary": {}},
        "approval": {"approval_completed": True, "approval_status": "approved", "summary": {}},
        "lineage": {"parent_commit_id": None, "metadata": {}},
    }


def test_run_admission_rejects_non_extracted_document_text_refs() -> None:
    extraction_store = InMemoryFileExtractionStore()
    extraction_store.write_extraction({
        "extraction_id": "fex_pending",
        "workspace_id": "ws_1",
        "upload_id": "upl_1",
        "extraction_state": "queued",
    })
    request = ProductRunLaunchRequest(
        workspace_id="ws_1",
        execution_target=ProductExecutionTarget(target_type="commit_snapshot", target_ref="snap-extract-001"),
        input_payload={"document_text_refs": ["fex_pending"]},
    )

    outcome = RunAdmissionService.admit(
        request=request,
        request_auth=_auth_context_for_extraction_gate(),
        workspace_context=_workspace_for_extraction_gate(),
        target_catalog={
            "snap-extract-001": ExecutionTargetCatalogEntry(
                workspace_id="ws_1",
                target_ref="snap-extract-001",
                target_type="commit_snapshot",
                source=_commit_snapshot_for_extraction_gate("snap-extract-001"),
            )
        },
        file_extraction_reader=extraction_store.get_workspace_extraction,
    )

    assert outcome.accepted is False
    assert outcome.rejected_response is not None
    assert outcome.rejected_response.reason_code == "file_extraction.not_ready.queued"
    assert outcome.rejected_response.blocking_findings[0]["extraction_id"] == "fex_pending"


def test_run_admission_allows_extracted_document_text_refs() -> None:
    extraction_store = InMemoryFileExtractionStore()
    extraction_store.write_extraction({
        "extraction_id": "fex_ready",
        "workspace_id": "ws_1",
        "upload_id": "upl_1",
        "extraction_state": "extracted",
    })
    request = ProductRunLaunchRequest(
        workspace_id="ws_1",
        execution_target=ProductExecutionTarget(target_type="commit_snapshot", target_ref="snap-extract-002"),
        input_payload={"document_text_refs": ["fex_ready"]},
    )

    outcome = RunAdmissionService.admit(
        request=request,
        request_auth=_auth_context_for_extraction_gate(),
        workspace_context=_workspace_for_extraction_gate(),
        target_catalog={
            "snap-extract-002": ExecutionTargetCatalogEntry(
                workspace_id="ws_1",
                target_ref="snap-extract-002",
                target_type="commit_snapshot",
                source=_commit_snapshot_for_extraction_gate("snap-extract-002"),
            )
        },
        file_extraction_reader=extraction_store.get_workspace_extraction,
        run_id_factory=lambda: "run-extracted-1",
    )

    assert outcome.accepted is True
    assert outcome.accepted_response is not None
    assert outcome.accepted_response.run_id == "run-extracted-1"
