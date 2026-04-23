from __future__ import annotations

from sqlalchemy import create_engine, text

from src.server.pg.dependencies_factory import build_postgres_dependencies
from src.server.pg.row_stores import (
    PostgresFeedbackStore,
    PostgresManagedSecretMetadataStore,
    PostgresOnboardingStateStore,
    PostgresProviderBindingStore,
    PostgresProviderProbeHistoryStore,
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
    assert deps.onboarding_rows_provider()[0]["onboarding_state_id"] == "onb-9"
    assert deps.workspace_provider_binding_row_provider("ws-9", "openai") is not None
    assert deps.managed_secret_metadata_reader(str(receipt["secret_ref"])) is not None
    assert deps.feedback_rows_provider()[0]["feedback_id"] == "fb-9"
