from __future__ import annotations

from src.server import (
    PostgresConnectionSettings,
    build_initial_server_migration,
    build_migration_file_text,
    build_postgres_connection_url,
    build_server_schema_summary,
    get_server_schema_families,
    load_postgres_connection_settings_from_env,
    render_postgres_schema_statements,
)


def test_load_postgres_connection_settings_from_env_uses_postgres_defaults_and_overrides() -> None:
    settings = load_postgres_connection_settings_from_env(
        {
            "NEXA_SERVER_DB_HOST": "db.internal",
            "NEXA_SERVER_DB_PORT": "6432",
            "NEXA_SERVER_DB_NAME": "nexa_prod",
            "NEXA_SERVER_DB_USER": "nexa_service",
            "NEXA_SERVER_DB_PASSWORD_ENV": "SERVER_DB_PASSWORD",
            "NEXA_SERVER_DB_SSLMODE": "verify-full",
            "NEXA_SERVER_DB_APP_NAME": "nexa_api",
            "NEXA_SERVER_DB_CONNECT_TIMEOUT": "15",
            "NEXA_SERVER_DB_SCHEMA": "nexa_server",
        }
    )

    assert settings == PostgresConnectionSettings(
        host="db.internal",
        port=6432,
        database_name="nexa_prod",
        username="nexa_service",
        password_env_var="SERVER_DB_PASSWORD",
        ssl_mode="verify-full",
        application_name="nexa_api",
        connect_timeout_s=15,
        schema_name="nexa_server",
    )


def test_build_postgres_connection_url_supports_password_redaction() -> None:
    settings = PostgresConnectionSettings(
        host="db.internal",
        port=5432,
        database_name="nexa_prod",
        username="nexa_service",
    )

    full_url = build_postgres_connection_url(settings, password="super-secret")
    redacted_url = build_postgres_connection_url(settings, password="super-secret", redact_password=True)

    assert full_url.startswith("postgresql://nexa_service:super-secret@db.internal:5432/nexa_prod?")
    assert "sslmode=require" in full_url
    assert "application_name=nexa_server" in full_url
    assert redacted_url.startswith("postgresql://nexa_service:%2A%2A%2A@db.internal:5432/nexa_prod?")


def test_server_schema_families_keep_mutable_and_append_only_concerns_separate() -> None:
    families = get_server_schema_families()
    summary = build_server_schema_summary()

    assert [family.family_name for family in families] == [
        "workspace_registry",
        "run_history",
        "provider_credentials",
        "provider_probe_history",
        "append_only_outputs",
    ]
    assert summary["family_count"] == 5

    workspace_family, run_family, provider_family, probe_family, append_only_family = families
    assert workspace_family.persistence_mode == "mutable_projection"
    assert run_family.persistence_mode == "mutable_projection"
    assert provider_family.persistence_mode == "mutable_projection"
    assert probe_family.persistence_mode == "mutable_projection"
    assert append_only_family.persistence_mode == "append_only"

    provider_tables = {table.name for table in provider_family.tables}
    assert provider_tables == {"managed_provider_bindings"}

    probe_tables = {table.name for table in probe_family.tables}
    assert probe_tables == {"provider_probe_events"}

    append_only_tables = {table.name for table in append_only_family.tables}
    assert append_only_tables == {"artifact_index", "trace_event_index", "artifact_lineage_links"}


def test_initial_server_migration_contains_workspace_run_artifact_trace_and_lineage_tables() -> None:
    migration = build_initial_server_migration()
    statements = render_postgres_schema_statements(migration.schema_families)
    migration_text = build_migration_file_text(migration)

    assert migration.migration_id == "server_foundation_0001"
    assert migration.dialect == "postgresql"
    assert migration.steps[0].step_id == "server_foundation_0001_create_tables_and_indexes"

    assert any("CREATE TABLE IF NOT EXISTS workspace_registry" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS run_records" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS onboarding_state" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS managed_provider_bindings" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS provider_probe_events" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS artifact_index" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS trace_event_index" in statement for statement in statements)
    assert any("CREATE TABLE IF NOT EXISTS artifact_lineage_links" in statement for statement in statements)
    assert any("CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_memberships_workspace_user" in statement for statement in statements)
    assert any("CREATE UNIQUE INDEX IF NOT EXISTS uq_onboarding_state_user_workspace" in statement for statement in statements)

    assert "-- migration_id: server_foundation_0001" in migration_text
    assert "workspace continuity" in migration_text.lower()
    assert "provider probe history" in migration_text.lower()
    assert "artifact lineage links" in migration_text.lower()


def test_run_artifact_trace_probe_and_workspace_linkage_are_queryable_in_schema_spec() -> None:
    families = get_server_schema_families()
    tables = {
        table.name: table
        for family in families
        for table in family.tables
    }

    run_records = tables["run_records"]
    artifact_index = tables["artifact_index"]
    trace_event_index = tables["trace_event_index"]
    provider_probe_events = tables["provider_probe_events"]

    run_workspace_column = next(column for column in run_records.columns if column.name == "workspace_id")
    artifact_workspace_column = next(column for column in artifact_index.columns if column.name == "workspace_id")
    artifact_run_column = next(column for column in artifact_index.columns if column.name == "run_id")
    trace_workspace_column = next(column for column in trace_event_index.columns if column.name == "workspace_id")
    trace_run_column = next(column for column in trace_event_index.columns if column.name == "run_id")
    probe_workspace_column = next(column for column in provider_probe_events.columns if column.name == "workspace_id")
    probe_binding_column = next(column for column in provider_probe_events.columns if column.name == "binding_id")

    assert run_workspace_column.reference_table == "workspace_registry"
    assert artifact_workspace_column.reference_table == "workspace_registry"
    assert artifact_run_column.reference_table == "run_records"
    assert trace_workspace_column.reference_table == "workspace_registry"
    assert trace_run_column.reference_table == "run_records"
    assert probe_workspace_column.reference_table == "workspace_registry"
    assert probe_binding_column.reference_table == "managed_provider_bindings"
