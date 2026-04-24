from __future__ import annotations

from sqlalchemy import create_engine, text

from src.server.pg.dependencies_factory import build_postgres_dependencies
from src.server.pg.row_stores import (
    PostgresFeedbackStore,
    PostgresManagedSecretMetadataStore,
    PostgresProviderCatalogStore,
    PostgresWorkspaceArtifactSourceStore,
    PostgresOnboardingStateStore,
    PostgresAppendOnlyProjectionStore,
    PostgresRunProjectionStore,
    PostgresProviderBindingStore,
    PostgresProviderProbeHistoryStore,
    PostgresPublicShareActionReportStore,
    PostgresPublicSharePayloadStore,
    PostgresSavedPublicShareStore,
    PostgresWorkspaceRegistryStore,
)


def _build_sqlite_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    statements = (
        """
        CREATE TABLE workspace_registry (
            workspace_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_run_id TEXT,
            last_result_status TEXT,
            continuity_source TEXT DEFAULT 'server',
            archived BOOLEAN DEFAULT FALSE
        )
        """,
        """
        CREATE TABLE workspace_memberships (
            membership_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (workspace_id, user_id)
        )
        """,
        """
        CREATE TABLE workspace_artifact_sources (
            workspace_id TEXT PRIMARY KEY,
            storage_role TEXT NOT NULL,
            canonical_ref TEXT,
            artifact_source TEXT NOT NULL,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE provider_catalog_entries (
            provider_key TEXT PRIMARY KEY,
            provider_family TEXT NOT NULL,
            display_name TEXT NOT NULL,
            managed_supported BOOLEAN DEFAULT TRUE,
            recommended_scope TEXT NOT NULL,
            local_env_var_hint TEXT,
            default_secret_name_template TEXT,
            lifecycle_state TEXT DEFAULT 'active',
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE public_share_payloads (
            share_id TEXT PRIMARY KEY,
            issued_by_user_ref TEXT,
            storage_role TEXT NOT NULL,
            canonical_ref TEXT,
            lifecycle_state TEXT NOT NULL,
            archived BOOLEAN DEFAULT FALSE,
            expires_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            share_payload TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE public_share_action_reports (
            report_id TEXT PRIMARY KEY,
            issuer_user_ref TEXT NOT NULL,
            action TEXT NOT NULL,
            scope TEXT NOT NULL,
            affected_share_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            action_report TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE saved_public_shares (
            saved_row_ref TEXT PRIMARY KEY,
            share_id TEXT NOT NULL,
            saved_by_user_ref TEXT NOT NULL,
            saved_at TEXT NOT NULL,
            UNIQUE (saved_by_user_ref, share_id)
        )
        """,
        """
        CREATE TABLE onboarding_state (
            onboarding_state_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            workspace_id TEXT,
            first_success_achieved BOOLEAN DEFAULT FALSE,
            advanced_surfaces_unlocked BOOLEAN DEFAULT FALSE,
            dismissed_guidance_state TEXT,
            current_step TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE (user_id, workspace_id)
        )
        """,
        """
        CREATE TABLE managed_provider_bindings (
            binding_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            provider_key TEXT NOT NULL,
            provider_family TEXT NOT NULL,
            display_name TEXT,
            credential_source TEXT DEFAULT 'managed',
            secret_ref TEXT,
            secret_version_ref TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            default_model_ref TEXT,
            allowed_model_refs TEXT,
            notes TEXT,
            created_by_user_id TEXT,
            updated_by_user_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_rotated_at TEXT,
            UNIQUE (workspace_id, provider_key)
        )
        """,
        """
        CREATE TABLE provider_probe_events (
            probe_event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            binding_id TEXT,
            provider_key TEXT NOT NULL,
            provider_family TEXT NOT NULL,
            display_name TEXT NOT NULL,
            probe_status TEXT NOT NULL,
            connectivity_state TEXT NOT NULL,
            secret_resolution_status TEXT,
            requested_model_ref TEXT,
            effective_model_ref TEXT,
            round_trip_latency_ms INTEGER,
            requested_by_user_id TEXT,
            message TEXT,
            occurred_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE managed_secret_metadata (
            secret_ref TEXT PRIMARY KEY,
            secret_version_ref TEXT,
            last_rotated_at TEXT,
            workspace_id TEXT,
            provider_key TEXT,
            secret_authority TEXT
        )
        """,
        """
        CREATE TABLE run_records (
            run_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            launch_request_id TEXT NOT NULL,
            execution_target_type TEXT NOT NULL,
            execution_target_ref TEXT NOT NULL,
            status TEXT NOT NULL,
            status_family TEXT NOT NULL,
            result_state TEXT,
            latest_error_family TEXT,
            requested_by_user_id TEXT,
            auth_context_ref TEXT,
            trace_available BOOLEAN DEFAULT FALSE,
            artifact_count INTEGER DEFAULT 0,
            trace_event_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE run_result_index (
            run_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            result_state TEXT NOT NULL,
            final_status TEXT,
            result_summary TEXT,
            trace_ref TEXT,
            artifact_count INTEGER DEFAULT 0,
            failure_info TEXT,
            final_output TEXT,
            metrics TEXT,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE artifact_index (
            artifact_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            producer_node TEXT,
            content_hash TEXT,
            storage_ref TEXT,
            payload_preview TEXT,
            trace_ref TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE trace_event_index (
            trace_event_ref TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            sequence_number INTEGER DEFAULT 0,
            node_id TEXT,
            severity TEXT,
            message_preview TEXT,
            occurred_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE workspace_feedback (
            feedback_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            workspace_title TEXT,
            category TEXT NOT NULL,
            surface TEXT NOT NULL,
            message TEXT NOT NULL,
            run_id TEXT,
            template_id TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    return engine


def test_postgres_workspace_registry_store_round_trips_rows_and_context() -> None:
    engine = _build_sqlite_engine()
    store = PostgresWorkspaceRegistryStore(engine)

    store.write_workspace_bundle(
        {
            "workspace_id": "ws-1",
            "owner_user_id": "user-owner",
            "title": "Workspace One",
            "description": "Primary",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        },
        {
            "membership_id": "membership-1",
            "workspace_id": "ws-1",
            "user_id": "user-editor",
            "role": "editor",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        },
    )

    row = store.get_workspace_row("ws-1")
    assert row is not None
    assert row["description"] == "Primary"
    assert store.list_workspace_rows()[0]["workspace_id"] == "ws-1"
    context = store.get_workspace_context("ws-1")
    assert context is not None
    assert context.collaborator_user_refs == ("user-editor",)


def test_postgres_workspace_artifact_source_store_round_trips_current_shell_source() -> None:
    engine = _build_sqlite_engine()
    store = PostgresWorkspaceArtifactSourceStore(engine)

    stored = store.write(
        "ws-1",
        {
            "meta": {
                "format_version": "1.0.0",
                "storage_role": "working_save",
                "working_save_id": "ws-1-draft",
                "name": "Workspace One",
                "updated_at": "2026-04-23T10:00:00+00:00",
            },
            "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
            "resources": {"prompts": {}, "providers": {}, "plugins": {}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
        },
    )

    assert stored["meta"]["working_save_id"] == "ws-1-draft"
    loaded = store.get("ws-1")
    assert loaded is not None
    assert loaded["meta"]["storage_role"] == "working_save"
    assert loaded["meta"]["working_save_id"] == "ws-1-draft"


def test_postgres_provider_catalog_store_round_trips_rows() -> None:
    engine = _build_sqlite_engine()
    store = PostgresProviderCatalogStore(engine)

    store.seed_defaults(({
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "OPENAI_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
    },))
    store.write({
        "provider_key": "anthropic",
        "provider_family": "anthropic",
        "display_name": "Anthropic Claude",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "ANTHROPIC_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/anthropic",
        "updated_at": "2026-04-24T00:00:00+00:00",
    })

    rows = store.list_rows()
    assert [row["provider_key"] for row in rows] == ["anthropic", "openai"]
    assert rows[0]["managed_supported"] is True
    assert rows[0]["local_env_var_hint"] == "ANTHROPIC_API_KEY"


def test_postgres_public_share_payload_store_round_trips_payloads() -> None:
    engine = _build_sqlite_engine()
    store = PostgresPublicSharePayloadStore(engine)

    stored = store.write(
        {
            "share": {
                "share_family": "nex.public-link-share",
                "transport": "link",
                "access_mode": "public_readonly",
                "share_id": "share-1",
                "share_path": "/share/share-1",
                "artifact_format_family": "nex.public-artifact",
                "storage_role": "working_save",
                "canonical_ref": "ws-1-draft",
                "title": "Workspace Share",
                "summary": "Summary",
                "viewer_capabilities": ["inspect_metadata", "download_artifact", "import_copy"],
                "operation_capabilities": ["inspect_metadata", "download_artifact", "import_copy", "run_artifact"],
                "lifecycle": {
                    "state": "active",
                    "created_at": "2026-04-23T10:00:00+00:00",
                    "updated_at": "2026-04-23T10:00:00+00:00",
                    "expires_at": None,
                    "issued_by_user_ref": "user-owner",
                },
                "management": {"archived": False, "archived_at": None},
                "audit": {"history": []},
            },
            "artifact": {
                "meta": {
                    "format_family": "nex.public-artifact",
                    "format_version": "1.0.0",
                    "storage_role": "working_save",
                    "working_save_id": "ws-1-draft",
                    "name": "Workspace One",
                },
                "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
                "resources": {"prompts": {}, "providers": {}, "plugins": {}},
                "state": {"input": {}, "working": {}, "memory": {}},
                "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
                "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
            },
        }
    )

    assert stored["share"]["share_id"] == "share-1"
    assert store.get("share-1")["share"]["title"] == "Workspace Share"
    assert store.list_rows()[0]["share"]["share_id"] == "share-1"
    assert store.delete("share-1") is True
    assert store.get("share-1") is None


def test_postgres_public_share_action_report_store_round_trips_reports() -> None:
    engine = _build_sqlite_engine()
    store = PostgresPublicShareActionReportStore(engine)

    stored = store.write(
        {
            "report_id": "share_report_1",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "issuer_bulk",
            "created_at": "2026-04-23T10:10:00+00:00",
            "requested_share_ids": ("share-1",),
            "affected_share_ids": ("share-1",),
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 1,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": False,
        }
    )

    assert stored["action"] == "revoke"
    assert store.list_rows()[0]["report_id"] == "share_report_1"


def test_postgres_saved_public_share_store_round_trips_rows() -> None:
    engine = _build_sqlite_engine()
    store = PostgresSavedPublicShareStore(engine)

    stored = store.write(
        {
            "share_id": "share-1",
            "saved_by_user_ref": "user-owner",
            "saved_at": "2026-04-23T10:20:00+00:00",
        }
    )

    assert stored["share_id"] == "share-1"
    assert store.list_rows()[0]["saved_by_user_ref"] == "user-owner"
    assert store.delete("share-1") is True
    assert store.list_rows() == ()


def test_postgres_onboarding_state_store_round_trips_json_payload() -> None:
    engine = _build_sqlite_engine()
    store = PostgresOnboardingStateStore(engine)

    store.write(
        {
            "onboarding_state_id": "onb-1",
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "first_success_achieved": True,
            "advanced_surfaces_unlocked": True,
            "dismissed_guidance_state": {"hint_a": True},
            "current_step": "result_seen",
            "updated_at": "2026-04-23T10:00:00+00:00",
        }
    )

    row = store.list_rows()[0]
    assert row["dismissed_guidance_state"] == {"hint_a": True}
    assert row["advanced_surfaces_unlocked"] is True


def test_postgres_provider_binding_store_round_trips_binding_rows() -> None:
    engine = _build_sqlite_engine()
    store = PostgresProviderBindingStore(engine)

    store.write(
        {
            "binding_id": "binding-1",
            "workspace_id": "ws-1",
            "provider_key": "OpenAI",
            "provider_family": "openai",
            "display_name": "OpenAI",
            "enabled": True,
            "allowed_model_refs": ["gpt-4.1", "gpt-4.1-mini"],
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        }
    )

    row = store.get_workspace_provider_row("ws-1", "openai")
    assert row is not None
    assert row["provider_key"] == "openai"
    assert row["allowed_model_refs"] == ("gpt-4.1", "gpt-4.1-mini")
    assert store.list_workspace_rows("ws-1")[0]["binding_id"] == "binding-1"


def test_postgres_provider_probe_history_store_round_trips_recent_rows() -> None:
    engine = _build_sqlite_engine()
    store = PostgresProviderProbeHistoryStore(engine)

    store.write(
        {
            "probe_event_id": "probe-1",
            "workspace_id": "ws-1",
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI",
            "probe_status": "reachable",
            "connectivity_state": "ok",
            "occurred_at": "2026-04-23T10:00:00+00:00",
        }
    )

    assert store.list_workspace_rows("ws-1")[0]["probe_event_id"] == "probe-1"
    assert store.list_recent_rows(limit=1)[0]["probe_event_id"] == "probe-1"


def test_postgres_managed_secret_metadata_store_round_trips_rows() -> None:
    engine = _build_sqlite_engine()
    store = PostgresManagedSecretMetadataStore(engine)

    store.write_receipt(
        {
            "secret_ref": "secret://ws-1/openai",
            "secret_version_ref": "v2",
            "last_rotated_at": "2026-04-23T10:00:00+00:00",
            "workspace_id": "ws-1",
            "provider_key": "openai",
        }
    )

    row = store.read("secret://ws-1/openai")
    assert row is not None
    assert row["secret_version_ref"] == "v2"
    assert store.list_all_rows()[0]["secret_ref"] == "secret://ws-1/openai"


def test_postgres_feedback_store_round_trips_rows() -> None:
    engine = _build_sqlite_engine()
    store = PostgresFeedbackStore(engine)

    store.write(
        {
            "feedback_id": "fb-1",
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "workspace_title": "Workspace One",
            "category": "bug_report",
            "surface": "workspace_shell",
            "message": "This screen failed.",
            "run_id": "run-1",
            "template_id": "tpl-1",
            "status": "received",
            "created_at": "2026-04-23T10:00:00+00:00",
        }
    )

    row = store.list_rows()[0]
    assert row["feedback_id"] == "fb-1"
    assert row["surface"] == "workspace_shell"
    assert row["template_id"] == "tpl-1"



def test_postgres_run_projection_store_round_trips_rows_and_context() -> None:
    engine = _build_sqlite_engine()
    workspace_store = PostgresWorkspaceRegistryStore(engine)
    workspace_store.write_workspace_bundle(
        {
            "workspace_id": "ws-run",
            "owner_user_id": "user-owner",
            "title": "Workspace Run",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        },
        {
            "membership_id": "membership-run",
            "workspace_id": "ws-run",
            "user_id": "user-owner",
            "role": "owner",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        },
    )
    store = PostgresRunProjectionStore(engine, workspace_registry_store=workspace_store)
    store.write_run_record(
        {
            "run_id": "run-1",
            "workspace_id": "ws-run",
            "launch_request_id": "req-1",
            "execution_target_type": "commit_snapshot",
            "execution_target_ref": "snap-1",
            "status": "queued",
            "status_family": "pending",
            "requested_by_user_id": "user-owner",
            "auth_context_ref": "auth-1",
            "trace_available": False,
            "artifact_count": 0,
            "trace_event_count": 0,
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        }
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO run_result_index (run_id, workspace_id, result_state, final_status, result_summary, trace_ref, artifact_count, failure_info, final_output, metrics, updated_at) "
                "VALUES (:run_id, :workspace_id, :result_state, :final_status, :result_summary, :trace_ref, :artifact_count, :failure_info, :final_output, :metrics, :updated_at)"
            ),
            {
                "run_id": "run-1",
                "workspace_id": "ws-run",
                "result_state": "ready_success",
                "final_status": "completed",
                "result_summary": "Success.",
                "trace_ref": "trace-1",
                "artifact_count": 1,
                "failure_info": None,
                "final_output": '{"answer": "ok"}',
                "metrics": '{"latency_ms": 10}',
                "updated_at": "2026-04-23T10:00:05+00:00",
            },
        )
    row = store.get_run_record("run-1")
    assert row is not None
    assert row["workspace_id"] == "ws-run"
    assert store.list_workspace_run_rows("ws-run")[0]["run_id"] == "run-1"
    assert store.list_recent_run_rows()[0]["run_id"] == "run-1"
    assert store.get_result_row("run-1")["result_summary"] == "Success."
    assert store.get_workspace_result_rows("ws-run")["run-1"]["final_output"] == {"answer": "ok"}
    context = store.get_run_context("run-1")
    assert context is not None
    assert context.run_id == "run-1"


def test_postgres_append_only_projection_store_reads_artifacts_and_trace() -> None:
    engine = _build_sqlite_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO artifact_index (artifact_id, workspace_id, run_id, artifact_type, producer_node, content_hash, storage_ref, payload_preview, trace_ref, metadata_json, created_at) "
                "VALUES (:artifact_id, :workspace_id, :run_id, :artifact_type, :producer_node, :content_hash, :storage_ref, :payload_preview, :trace_ref, :metadata_json, :created_at)"
            ),
            {
                "artifact_id": "artifact-1",
                "workspace_id": "ws-run",
                "run_id": "run-1",
                "artifact_type": "text",
                "producer_node": "node-1",
                "content_hash": None,
                "storage_ref": None,
                "payload_preview": "Preview",
                "trace_ref": "trace-1",
                "metadata_json": '{"label": "Artifact"}',
                "created_at": "2026-04-23T10:00:05+00:00",
            },
        )
        connection.execute(
            text(
                "INSERT INTO trace_event_index (trace_event_ref, workspace_id, run_id, event_type, sequence_number, node_id, severity, message_preview, occurred_at) "
                "VALUES (:trace_event_ref, :workspace_id, :run_id, :event_type, :sequence_number, :node_id, :severity, :message_preview, :occurred_at)"
            ),
            {
                "trace_event_ref": "trace-evt-1",
                "workspace_id": "ws-run",
                "run_id": "run-1",
                "event_type": "started",
                "sequence_number": 1,
                "node_id": "node-1",
                "severity": "info",
                "message_preview": "Started",
                "occurred_at": "2026-04-23T10:00:06+00:00",
            },
        )
    store = PostgresAppendOnlyProjectionStore(engine)
    artifacts = store.list_artifact_rows("run-1")
    assert artifacts[0]["artifact_id"] == "artifact-1"
    assert artifacts[0]["metadata_json"] == {"label": "Artifact"}
    assert store.get_artifact_row("artifact-1")["payload_preview"] == "Preview"
    trace_rows = store.list_trace_rows("run-1")
    assert trace_rows[0]["trace_event_ref"] == "trace-evt-1"


def test_build_postgres_dependencies_wires_sql_backed_continuity_stores() -> None:
    sync_engine = _build_sqlite_engine()
    async_engine = object()

    deps = build_postgres_dependencies(async_engine, sync_engine=sync_engine)
    deps.workspace_registry_writer(
        {
            "workspace_id": "ws-9",
            "owner_user_id": "user-owner",
            "title": "Workspace Nine",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        },
        {
            "membership_id": "membership-9",
            "workspace_id": "ws-9",
            "user_id": "user-owner",
            "role": "owner",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        },
    )
    deps.onboarding_state_writer(
        {
            "onboarding_state_id": "onb-9",
            "user_id": "user-owner",
            "workspace_id": "ws-9",
            "updated_at": "2026-04-23T10:00:00+00:00",
        }
    )
    deps.provider_binding_writer(
        {
            "binding_id": "binding-9",
            "workspace_id": "ws-9",
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI",
            "created_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:00+00:00",
        }
    )
    receipt = deps.managed_secret_writer("ws-9", "openai", "secret-value", {"now_iso": "2026-04-23T10:00:00+00:00"})
    deps.feedback_writer(
        {
            "feedback_id": "fb-9",
            "user_id": "user-owner",
            "workspace_id": "ws-9",
            "workspace_title": "Workspace Nine",
            "category": "friction_note",
            "surface": "workspace_shell",
            "message": "Feedback message.",
            "created_at": "2026-04-23T10:01:00+00:00",
        }
    )

    assert deps.workspace_row_provider("ws-9") is not None
    deps.workspace_artifact_source_writer(
        "ws-9",
        {
            "meta": {
                "format_version": "1.0.0",
                "storage_role": "working_save",
                "working_save_id": "ws-9-draft",
                "name": "Workspace Nine",
            },
            "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
            "resources": {"prompts": {}, "providers": {}, "plugins": {}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
        },
    )
    assert deps.workspace_artifact_source_provider("ws-9")["meta"]["working_save_id"] == "ws-9-draft"
    assert any(row["provider_key"] == "openai" for row in deps.provider_catalog_rows_provider())
    assert deps.target_catalog_provider("ws-9")["ws-9-draft"].target_type == "working_save"
    assert deps.onboarding_rows_provider()[0]["onboarding_state_id"] == "onb-9"
    assert deps.workspace_provider_binding_row_provider("ws-9", "openai") is not None
    assert deps.managed_secret_metadata_reader(str(receipt["secret_ref"])) is not None
    assert deps.feedback_rows_provider()[0]["feedback_id"] == "fb-9"
    deps.run_record_writer({
        "run_id": "run-9",
        "workspace_id": "ws-9",
        "launch_request_id": "req-9",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-9",
        "status": "queued",
        "status_family": "pending",
        "requested_by_user_id": "user-owner",
        "auth_context_ref": "auth-9",
        "trace_available": False,
        "artifact_count": 0,
        "trace_event_count": 0,
        "created_at": "2026-04-23T10:02:00+00:00",
        "updated_at": "2026-04-23T10:02:00+00:00",
    })
    deps.public_share_payload_writer({
        "share": {
            "share_family": "nex.public-link-share",
            "transport": "link",
            "access_mode": "public_readonly",
            "share_id": "share-9",
            "share_path": "/share/share-9",
            "artifact_format_family": "nex.public-artifact",
            "storage_role": "working_save",
            "canonical_ref": "ws-9-draft",
            "title": "Workspace Nine Share",
            "summary": "Summary",
            "viewer_capabilities": ["inspect_metadata", "download_artifact", "import_copy"],
            "operation_capabilities": ["inspect_metadata", "download_artifact", "import_copy", "run_artifact"],
            "lifecycle": {
                "state": "active",
                "created_at": "2026-04-23T10:03:00+00:00",
                "updated_at": "2026-04-23T10:03:00+00:00",
                "expires_at": None,
                "issued_by_user_ref": "user-owner",
            },
            "management": {"archived": False, "archived_at": None},
            "audit": {"history": []},
        },
        "artifact": {
            "meta": {
                "format_family": "nex.public-artifact",
                "format_version": "1.0.0",
                "storage_role": "working_save",
                "working_save_id": "ws-9-draft",
                "name": "Workspace Nine",
            },
            "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
            "resources": {"prompts": {}, "providers": {}, "plugins": {}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
        },
    })
    deps.public_share_action_report_writer({
        "report_id": "share_report_9",
        "issuer_user_ref": "user-owner",
        "action": "revoke",
        "scope": "issuer_bulk",
        "created_at": "2026-04-23T10:04:00+00:00",
        "requested_share_ids": ("share-9",),
        "affected_share_ids": ("share-9",),
        "affected_share_count": 1,
        "before_total_share_count": 1,
        "after_total_share_count": 0,
        "actor_user_ref": "user-owner",
        "expires_at": None,
        "archived": False,
    })
    deps.saved_public_share_writer({
        "share_id": "share-9",
        "saved_by_user_ref": "user-owner",
        "saved_at": "2026-04-23T10:05:00+00:00",
    })
    assert deps.run_record_provider("run-9") is not None
    assert deps.recent_run_rows_provider()[0]["run_id"] == "run-9"
    assert deps.run_context_provider("run-9") is not None
    assert deps.public_share_payload_provider("share-9") is not None
    assert deps.public_share_payload_rows_provider()[0]["share"]["share_id"] == "share-9"
    assert deps.public_share_action_report_rows_provider()[0]["report_id"] == "share_report_9"
    assert deps.saved_public_share_rows_provider()[0]["share_id"] == "share-9"
