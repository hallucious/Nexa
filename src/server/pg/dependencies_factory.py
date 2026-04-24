from __future__ import annotations

from dataclasses import replace
from typing import Any

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.provider_secret_api import default_provider_catalog_rows
from src.server.run_admission_models import ExecutionTargetCatalogEntry
from src.storage.nex_api import resolve_nex_execution_target
from src.server.feedback_store import bind_feedback_store
from src.server.managed_secret_metadata_store import bind_managed_secret_metadata_store
from src.server.onboarding_state_store import bind_onboarding_state_store
from src.server.pg.engine import get_postgres_sync_engine
from src.server.pg.row_stores import (
    PostgresFeedbackStore,
    PostgresManagedSecretMetadataStore,
    PostgresAppendOnlyProjectionStore,
    PostgresRunProjectionStore,
    PostgresWorkspaceArtifactSourceStore,
    PostgresOnboardingStateStore,
    PostgresProviderBindingStore,
    PostgresProviderCatalogStore,
    PostgresProviderProbeHistoryStore,
    PostgresPublicShareActionReportStore,
    PostgresPublicSharePayloadStore,
    PostgresSavedPublicShareStore,
    PostgresWorkspaceRegistryStore,
)
from src.server.provider_binding_store import bind_provider_binding_store
from src.server.provider_probe_history_store import bind_probe_history_store
from src.server.workspace_registry_store import bind_workspace_registry_store


# ``async_engine`` is intentionally typed as ``Any`` here so importing this module does
# not force optional SQLAlchemy async availability in non-Postgres environments.
def build_postgres_dependencies(async_engine: Any, *, sync_engine: Any | None = None) -> FastApiRouteDependencies:
    """Return the initial Postgres-backed dependency bundle.

    This batch wires the first persistence-backed continuity stores into the
    existing FastAPI dependency surface while keeping route/service semantics
    stable. Higher-level run/result persistence can attach in later batches.
    """

    _ = async_engine
    resolved_sync_engine = sync_engine if sync_engine is not None else get_postgres_sync_engine()

    dependencies = FastApiRouteDependencies()
    workspace_registry_store = PostgresWorkspaceRegistryStore(resolved_sync_engine)
    workspace_artifact_source_store = PostgresWorkspaceArtifactSourceStore(resolved_sync_engine)
    provider_catalog_store = PostgresProviderCatalogStore(resolved_sync_engine)
    provider_catalog_store.seed_defaults(default_provider_catalog_rows())
    public_share_payload_store = PostgresPublicSharePayloadStore(resolved_sync_engine)
    public_share_action_report_store = PostgresPublicShareActionReportStore(resolved_sync_engine)
    saved_public_share_store = PostgresSavedPublicShareStore(resolved_sync_engine)
    dependencies = bind_workspace_registry_store(
        dependencies=dependencies,
        store=workspace_registry_store,
    )
    dependencies = bind_onboarding_state_store(
        dependencies=dependencies,
        store=PostgresOnboardingStateStore(resolved_sync_engine),
    )
    dependencies = bind_provider_binding_store(
        dependencies=dependencies,
        store=PostgresProviderBindingStore(resolved_sync_engine),
    )
    dependencies = bind_probe_history_store(
        dependencies=dependencies,
        store=PostgresProviderProbeHistoryStore(resolved_sync_engine),
    )
    dependencies = bind_managed_secret_metadata_store(
        dependencies=dependencies,
        store=PostgresManagedSecretMetadataStore(resolved_sync_engine),
    )
    dependencies = bind_feedback_store(
        dependencies=dependencies,
        store=PostgresFeedbackStore(resolved_sync_engine),
    )
    run_projection_store = PostgresRunProjectionStore(resolved_sync_engine, workspace_registry_store=workspace_registry_store)
    append_only_projection_store = PostgresAppendOnlyProjectionStore(resolved_sync_engine)
    def _target_catalog_provider(workspace_id: str) -> dict[str, ExecutionTargetCatalogEntry]:
        source = workspace_artifact_source_store.get(workspace_id)
        if source is None:
            return {}
        try:
            descriptor = resolve_nex_execution_target(source)
        except ValueError:
            return {}
        return {
            descriptor.target_ref: ExecutionTargetCatalogEntry(
                workspace_id=str(workspace_id or "").strip(),
                target_ref=descriptor.target_ref,
                target_type=descriptor.target_type,
                source=source,
            )
        }

    dependencies = replace(
        dependencies,
        target_catalog_provider=_target_catalog_provider,
        provider_catalog_rows_provider=provider_catalog_store.list_rows,
        workspace_artifact_source_provider=workspace_artifact_source_store.get,
        workspace_artifact_source_writer=workspace_artifact_source_store.write,
        run_context_provider=run_projection_store.get_run_context,
        run_record_provider=run_projection_store.get_run_record,
        result_row_provider=run_projection_store.get_result_row,
        workspace_run_rows_provider=run_projection_store.list_workspace_run_rows,
        workspace_result_rows_provider=run_projection_store.get_workspace_result_rows,
        recent_run_rows_provider=run_projection_store.list_recent_run_rows,
        artifact_rows_provider=append_only_projection_store.list_artifact_rows,
        artifact_row_provider=append_only_projection_store.get_artifact_row,
        trace_rows_provider=append_only_projection_store.list_trace_rows,
        run_record_writer=run_projection_store.write_run_record,
        public_share_payload_provider=public_share_payload_store.get,
        public_share_payload_rows_provider=public_share_payload_store.list_rows,
        public_share_payload_writer=public_share_payload_store.write,
        public_share_payload_deleter=public_share_payload_store.delete,
        public_share_action_report_rows_provider=public_share_action_report_store.list_rows,
        public_share_action_report_writer=public_share_action_report_store.write,
        saved_public_share_rows_provider=saved_public_share_store.list_rows,
        saved_public_share_writer=saved_public_share_store.write,
        saved_public_share_deleter=saved_public_share_store.delete,
    )
    return dependencies
