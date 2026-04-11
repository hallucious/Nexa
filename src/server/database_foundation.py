from __future__ import annotations

from collections.abc import Mapping
from typing import Optional
from urllib.parse import quote_plus

from src.server.database_models import ColumnSpec, IndexSpec, PostgresConnectionSettings, SchemaFamily, TableSpec

_DEFAULT_DATABASE_ENV = {
    "NEXA_SERVER_DB_HOST": "localhost",
    "NEXA_SERVER_DB_PORT": "5432",
    "NEXA_SERVER_DB_NAME": "nexa",
    "NEXA_SERVER_DB_USER": "nexa",
    "NEXA_SERVER_DB_PASSWORD_ENV": "NEXA_SERVER_DB_PASSWORD",
    "NEXA_SERVER_DB_SSLMODE": "require",
    "NEXA_SERVER_DB_APP_NAME": "nexa_server",
    "NEXA_SERVER_DB_CONNECT_TIMEOUT": "10",
    "NEXA_SERVER_DB_SCHEMA": "public",
}


def _env_get(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, _DEFAULT_DATABASE_ENV[key])
    return str(value).strip()


def load_postgres_connection_settings_from_env(
    env: Mapping[str, str] | None = None,
) -> PostgresConnectionSettings:
    env_map: Mapping[str, str] = env or {}
    return PostgresConnectionSettings(
        host=_env_get(env_map, "NEXA_SERVER_DB_HOST"),
        port=int(_env_get(env_map, "NEXA_SERVER_DB_PORT")),
        database_name=_env_get(env_map, "NEXA_SERVER_DB_NAME"),
        username=_env_get(env_map, "NEXA_SERVER_DB_USER"),
        password_env_var=_env_get(env_map, "NEXA_SERVER_DB_PASSWORD_ENV"),
        ssl_mode=_env_get(env_map, "NEXA_SERVER_DB_SSLMODE"),
        application_name=_env_get(env_map, "NEXA_SERVER_DB_APP_NAME"),
        connect_timeout_s=int(_env_get(env_map, "NEXA_SERVER_DB_CONNECT_TIMEOUT")),
        schema_name=_env_get(env_map, "NEXA_SERVER_DB_SCHEMA"),
    )


def build_postgres_connection_url(
    settings: PostgresConnectionSettings,
    *,
    password: Optional[str] = None,
    redact_password: bool = False,
) -> str:
    password_value = password
    if redact_password:
        password_value = "***"
    userinfo = quote_plus(settings.username)
    if password_value is not None:
        userinfo = f"{userinfo}:{quote_plus(password_value)}"
    query = (
        f"sslmode={quote_plus(settings.ssl_mode)}"
        f"&application_name={quote_plus(settings.application_name)}"
        f"&connect_timeout={settings.connect_timeout_s}"
    )
    return (
        f"postgresql://{userinfo}@{settings.host}:{settings.port}/{settings.database_name}?{query}"
    )


def get_server_schema_families() -> tuple[SchemaFamily, ...]:
    workspace_registry = SchemaFamily(
        family_name="workspace_registry",
        purpose="Canonical product continuity registry for workspaces and membership scope.",
        persistence_mode="mutable_projection",
        tables=(
            TableSpec(
                name="workspace_registry",
                persistence_mode="mutable_projection",
                description="Workspace continuity registry and ownership anchor.",
                columns=(
                    ColumnSpec("workspace_id", "TEXT", is_primary_key=True),
                    ColumnSpec("owner_user_id", "TEXT"),
                    ColumnSpec("title", "TEXT", nullable=True),
                    ColumnSpec("created_at", "TIMESTAMPTZ"),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                    ColumnSpec("last_run_id", "TEXT", nullable=True),
                    ColumnSpec("last_result_status", "TEXT", nullable=True),
                    ColumnSpec("continuity_source", "TEXT", default_sql="'server'"),
                    ColumnSpec("archived", "BOOLEAN", default_sql="FALSE"),
                ),
                indexes=(
                    IndexSpec("idx_workspace_registry_owner_user_id", ("owner_user_id",)),
                    IndexSpec("idx_workspace_registry_updated_at", ("updated_at",)),
                ),
            ),
            TableSpec(
                name="workspace_memberships",
                persistence_mode="mutable_projection",
                description="Workspace role bindings for collaborator-ready ownership checks.",
                columns=(
                    ColumnSpec("membership_id", "TEXT", is_primary_key=True),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("user_id", "TEXT"),
                    ColumnSpec("role", "TEXT"),
                    ColumnSpec("created_at", "TIMESTAMPTZ"),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_workspace_memberships_workspace_id", ("workspace_id",)),
                    IndexSpec("idx_workspace_memberships_user_id", ("user_id",)),
                    IndexSpec("uq_workspace_memberships_workspace_user", ("workspace_id", "user_id"), unique=True),
                ),
            ),
        ),
    )
    run_history = SchemaFamily(
        family_name="run_history",
        purpose="Mutable run continuity projections queryable by workspace/account scope.",
        persistence_mode="mutable_projection",
        tables=(
            TableSpec(
                name="run_records",
                persistence_mode="mutable_projection",
                description="Server-side run continuity projection linked to canonical engine run identity.",
                columns=(
                    ColumnSpec("run_id", "TEXT", is_primary_key=True),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("launch_request_id", "TEXT", nullable=True),
                    ColumnSpec("execution_target_type", "TEXT"),
                    ColumnSpec("execution_target_ref", "TEXT"),
                    ColumnSpec("status", "TEXT"),
                    ColumnSpec("status_family", "TEXT", nullable=True),
                    ColumnSpec("result_state", "TEXT", nullable=True),
                    ColumnSpec("latest_error_family", "TEXT", nullable=True),
                    ColumnSpec("requested_by_user_id", "TEXT", nullable=True),
                    ColumnSpec("auth_context_ref", "TEXT", nullable=True),
                    ColumnSpec("trace_available", "BOOLEAN", default_sql="FALSE"),
                    ColumnSpec("artifact_count", "INTEGER", default_sql="0"),
                    ColumnSpec("trace_event_count", "INTEGER", default_sql="0"),
                    ColumnSpec("queue_job_id", "TEXT", nullable=True),
                    ColumnSpec("claimed_by_worker_ref", "TEXT", nullable=True),
                    ColumnSpec("claimed_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("lease_expires_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("last_heartbeat_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("worker_attempt_number", "INTEGER", default_sql="0"),
                    ColumnSpec("orphan_review_required", "BOOLEAN", default_sql="FALSE"),
                    ColumnSpec("created_at", "TIMESTAMPTZ"),
                    ColumnSpec("started_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("finished_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_run_records_workspace_id_created_at", ("workspace_id", "created_at")),
                    IndexSpec("idx_run_records_workspace_id_status", ("workspace_id", "status")),
                    IndexSpec("idx_run_records_execution_target", ("execution_target_type", "execution_target_ref")),
                    IndexSpec("idx_run_records_requested_by_user_id", ("requested_by_user_id",)),
                    IndexSpec("idx_run_records_claimed_by_worker_ref", ("claimed_by_worker_ref",)),
                    IndexSpec("idx_run_records_lease_expires_at", ("lease_expires_at",)),
                    IndexSpec("idx_run_records_orphan_review_required", ("orphan_review_required",)),
                ),
            ),
            TableSpec(
                name="run_result_index",
                persistence_mode="mutable_projection",
                description="Canonical product-facing run result query rows linked to terminal run state.",
                columns=(
                    ColumnSpec("run_id", "TEXT", is_primary_key=True, reference_table="run_records", reference_column="run_id"),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("result_state", "TEXT"),
                    ColumnSpec("final_status", "TEXT", nullable=True),
                    ColumnSpec("result_summary", "TEXT", nullable=True),
                    ColumnSpec("trace_ref", "TEXT", nullable=True),
                    ColumnSpec("artifact_count", "INTEGER", default_sql="0"),
                    ColumnSpec("failure_info", "JSONB", nullable=True),
                    ColumnSpec("final_output", "JSONB", nullable=True),
                    ColumnSpec("metrics", "JSONB", nullable=True),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_run_result_index_workspace_id_updated_at", ("workspace_id", "updated_at")),
                    IndexSpec("idx_run_result_index_result_state", ("result_state",)),
                ),
            ),
            TableSpec(
                name="queue_jobs",
                persistence_mode="mutable_projection",
                description="Queue-backed worker orchestration rows for admitted runs.",
                columns=(
                    ColumnSpec("queue_job_id", "TEXT", is_primary_key=True),
                    ColumnSpec("run_id", "TEXT", reference_table="run_records", reference_column="run_id"),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("run_request_id", "TEXT"),
                    ColumnSpec("queue_state", "TEXT"),
                    ColumnSpec("queue_name", "TEXT"),
                    ColumnSpec("priority", "TEXT"),
                    ColumnSpec("claimed_by_worker_ref", "TEXT", nullable=True),
                    ColumnSpec("claimed_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("lease_expires_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("last_heartbeat_at", "TIMESTAMPTZ", nullable=True),
                    ColumnSpec("worker_attempt_number", "INTEGER", default_sql="0"),
                    ColumnSpec("enqueued_at", "TIMESTAMPTZ"),
                    ColumnSpec("available_at", "TIMESTAMPTZ"),
                    ColumnSpec("created_at", "TIMESTAMPTZ"),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_queue_jobs_run_id", ("run_id",)),
                    IndexSpec("idx_queue_jobs_workspace_id_queue_state", ("workspace_id", "queue_state")),
                    IndexSpec("idx_queue_jobs_lease_expires_at", ("lease_expires_at",)),
                    IndexSpec("idx_queue_jobs_queue_name_available_at", ("queue_name", "available_at")),
                ),
            ),
            TableSpec(
                name="onboarding_state",
                persistence_mode="mutable_projection",
                description="Cross-device onboarding and unlock continuity state.",
                columns=(
                    ColumnSpec("onboarding_state_id", "TEXT", is_primary_key=True),
                    ColumnSpec("user_id", "TEXT"),
                    ColumnSpec("workspace_id", "TEXT", nullable=True, reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("first_success_achieved", "BOOLEAN", default_sql="FALSE"),
                    ColumnSpec("advanced_surfaces_unlocked", "BOOLEAN", default_sql="FALSE"),
                    ColumnSpec("dismissed_guidance_state", "JSONB", nullable=True),
                    ColumnSpec("current_step", "TEXT", nullable=True),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_onboarding_state_user_id", ("user_id",)),
                    IndexSpec("idx_onboarding_state_workspace_id", ("workspace_id",)),
                    IndexSpec("uq_onboarding_state_user_workspace", ("user_id", "workspace_id"), unique=True),
                ),
            ),
        ),
    )
    provider_credentials = SchemaFamily(
        family_name="provider_credentials",
        purpose="Managed provider binding metadata and canonical secret authority references.",
        persistence_mode="mutable_projection",
        tables=(
            TableSpec(
                name="managed_provider_bindings",
                persistence_mode="mutable_projection",
                description="Workspace-scoped managed provider binding metadata without raw secret values.",
                columns=(
                    ColumnSpec("binding_id", "TEXT", is_primary_key=True),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("provider_key", "TEXT"),
                    ColumnSpec("provider_family", "TEXT"),
                    ColumnSpec("display_name", "TEXT", nullable=True),
                    ColumnSpec("credential_source", "TEXT", default_sql="'managed'"),
                    ColumnSpec("secret_ref", "TEXT", nullable=True),
                    ColumnSpec("secret_version_ref", "TEXT", nullable=True),
                    ColumnSpec("enabled", "BOOLEAN", default_sql="TRUE"),
                    ColumnSpec("default_model_ref", "TEXT", nullable=True),
                    ColumnSpec("allowed_model_refs", "JSONB", nullable=True),
                    ColumnSpec("notes", "TEXT", nullable=True),
                    ColumnSpec("created_by_user_id", "TEXT", nullable=True),
                    ColumnSpec("updated_by_user_id", "TEXT", nullable=True),
                    ColumnSpec("created_at", "TIMESTAMPTZ"),
                    ColumnSpec("updated_at", "TIMESTAMPTZ"),
                    ColumnSpec("last_rotated_at", "TIMESTAMPTZ", nullable=True),
                ),
                indexes=(
                    IndexSpec("idx_managed_provider_bindings_workspace_id", ("workspace_id",)),
                    IndexSpec("uq_managed_provider_bindings_workspace_provider", ("workspace_id", "provider_key"), unique=True),
                    IndexSpec("idx_managed_provider_bindings_secret_ref", ("secret_ref",)),
                ),
            ),
        ),
    )
    provider_probe_history = SchemaFamily(
        family_name="provider_probe_history",
        purpose="Workspace-scoped provider connectivity probe projections separate from credential bindings and engine run history.",
        persistence_mode="mutable_projection",
        tables=(
            TableSpec(
                name="provider_probe_events",
                persistence_mode="mutable_projection",
                description="Canonical server-side provider probe history rows for connectivity review, recent activity, and continuity queries.",
                columns=(
                    ColumnSpec("probe_event_id", "TEXT", is_primary_key=True),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("binding_id", "TEXT", nullable=True, reference_table="managed_provider_bindings", reference_column="binding_id"),
                    ColumnSpec("provider_key", "TEXT"),
                    ColumnSpec("provider_family", "TEXT"),
                    ColumnSpec("display_name", "TEXT"),
                    ColumnSpec("probe_status", "TEXT"),
                    ColumnSpec("connectivity_state", "TEXT"),
                    ColumnSpec("secret_resolution_status", "TEXT", nullable=True),
                    ColumnSpec("requested_model_ref", "TEXT", nullable=True),
                    ColumnSpec("effective_model_ref", "TEXT", nullable=True),
                    ColumnSpec("round_trip_latency_ms", "INTEGER", nullable=True),
                    ColumnSpec("requested_by_user_id", "TEXT", nullable=True),
                    ColumnSpec("message", "TEXT", nullable=True),
                    ColumnSpec("occurred_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_provider_probe_events_workspace_provider_occurred_at", ("workspace_id", "provider_key", "occurred_at")),
                    IndexSpec("idx_provider_probe_events_workspace_occurred_at", ("workspace_id", "occurred_at")),
                    IndexSpec("idx_provider_probe_events_binding_id", ("binding_id",)),
                    IndexSpec("idx_provider_probe_events_workspace_probe_status", ("workspace_id", "probe_status")),
                    IndexSpec("idx_provider_probe_events_workspace_connectivity_state", ("workspace_id", "connectivity_state")),
                ),
            ),
        ),
    )
    append_only_outputs = SchemaFamily(
        family_name="append_only_outputs",
        purpose="Append-only output and lineage index tables that preserve artifact and trace meaning.",
        persistence_mode="append_only",
        tables=(
            TableSpec(
                name="artifact_index",
                persistence_mode="append_only",
                description="Append-only artifact index rows and retrieval metadata.",
                columns=(
                    ColumnSpec("artifact_id", "TEXT", is_primary_key=True),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("run_id", "TEXT", reference_table="run_records", reference_column="run_id"),
                    ColumnSpec("artifact_type", "TEXT"),
                    ColumnSpec("producer_node", "TEXT", nullable=True),
                    ColumnSpec("content_hash", "TEXT", nullable=True),
                    ColumnSpec("storage_ref", "TEXT", nullable=True),
                    ColumnSpec("payload_preview", "TEXT", nullable=True),
                    ColumnSpec("trace_ref", "TEXT", nullable=True),
                    ColumnSpec("metadata_json", "JSONB", nullable=True),
                    ColumnSpec("created_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_artifact_index_run_id", ("run_id",)),
                    IndexSpec("idx_artifact_index_workspace_id_created_at", ("workspace_id", "created_at")),
                    IndexSpec("idx_artifact_index_artifact_type", ("artifact_type",)),
                ),
            ),
            TableSpec(
                name="trace_event_index",
                persistence_mode="append_only",
                description="Append-only trace event query rows linked to run/workspace scope.",
                columns=(
                    ColumnSpec("trace_event_ref", "TEXT", is_primary_key=True),
                    ColumnSpec("workspace_id", "TEXT", reference_table="workspace_registry", reference_column="workspace_id"),
                    ColumnSpec("run_id", "TEXT", reference_table="run_records", reference_column="run_id"),
                    ColumnSpec("event_type", "TEXT"),
                    ColumnSpec("sequence_number", "INTEGER", default_sql="0"),
                    ColumnSpec("node_id", "TEXT", nullable=True),
                    ColumnSpec("severity", "TEXT", nullable=True),
                    ColumnSpec("message_preview", "TEXT", nullable=True),
                    ColumnSpec("occurred_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_trace_event_index_run_id_sequence_number", ("run_id", "sequence_number")),
                    IndexSpec("idx_trace_event_index_run_id_occurred_at", ("run_id", "occurred_at")),
                    IndexSpec("idx_trace_event_index_workspace_id", ("workspace_id",)),
                ),
            ),
            TableSpec(
                name="artifact_lineage_links",
                persistence_mode="append_only",
                description="Append-only lineage links between canonical artifact identities.",
                columns=(
                    ColumnSpec("lineage_link_id", "TEXT", is_primary_key=True),
                    ColumnSpec("artifact_id", "TEXT", reference_table="artifact_index", reference_column="artifact_id"),
                    ColumnSpec("parent_artifact_id", "TEXT", nullable=True, reference_table="artifact_index", reference_column="artifact_id"),
                    ColumnSpec("relation_type", "TEXT"),
                    ColumnSpec("recorded_at", "TIMESTAMPTZ"),
                ),
                indexes=(
                    IndexSpec("idx_artifact_lineage_links_artifact_id", ("artifact_id",)),
                    IndexSpec("idx_artifact_lineage_links_parent_artifact_id", ("parent_artifact_id",)),
                ),
            ),
        ),
    )
    return workspace_registry, run_history, provider_credentials, provider_probe_history, append_only_outputs


def build_server_schema_summary() -> dict[str, object]:
    families = get_server_schema_families()
    return {
        "family_count": len(families),
        "families": [
            {
                "family_name": family.family_name,
                "persistence_mode": family.persistence_mode,
                "table_names": [table.name for table in family.tables],
            }
            for family in families
        ],
    }
