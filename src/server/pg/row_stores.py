from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.managed_secret_metadata_store import InMemoryManagedSecretMetadataStore
from src.server.onboarding_state_store import InMemoryOnboardingStateStore
from src.server.provider_binding_store import InMemoryProviderBindingStore
from src.server.provider_probe_history_models import ProviderProbeHistoryRecord
from src.server.provider_probe_history_store import InMemoryProviderProbeHistoryStore
from src.server.workspace_registry_store import InMemoryWorkspaceRegistryStore
from src.server.run_admission_models import RunRecordProjection

try:  # pragma: no cover - availability varies by environment
    from sqlalchemy import text
    from sqlalchemy.engine import Engine
except ModuleNotFoundError:  # pragma: no cover
    Engine = Any  # type: ignore[misc,assignment]
    text = None  # type: ignore[assignment]

_ALLOWED_COLLABORATOR_ROLES = {"admin", "editor", "collaborator", "reviewer"}
_ALLOWED_VIEWER_ROLES = {"viewer"}


def _require_sqlalchemy() -> None:
    if text is None:
        raise ModuleNotFoundError("sqlalchemy is required for postgres row stores")


def _dialect_name(engine: Engine) -> str:
    return str(getattr(getattr(engine, "dialect", None), "name", "")).strip().lower()


def _json_placeholder(engine: Engine, name: str) -> str:
    return f"CAST(:{name} AS JSONB)" if _dialect_name(engine).startswith("postgres") else f":{name}"


def _serialize_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _decode_json(value: Any, *, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return default
    return default


def _row_dict(row: Any) -> dict[str, Any]:
    mapping = getattr(row, "_mapping", row)
    return {str(key): value for key, value in dict(mapping).items()}


def _fetch_one(engine: Engine, sql: str, params: Mapping[str, Any]) -> dict[str, Any] | None:
    _require_sqlalchemy()
    with engine.connect() as connection:
        row = connection.execute(text(sql), dict(params)).mappings().first()
    return None if row is None else _row_dict(row)


def _fetch_all(engine: Engine, sql: str, params: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    _require_sqlalchemy()
    with engine.connect() as connection:
        rows = connection.execute(text(sql), dict(params or {})).mappings().all()
    return tuple(_row_dict(row) for row in rows)


def _execute(engine: Engine, sql: str, params: Mapping[str, Any]) -> None:
    _require_sqlalchemy()
    with engine.begin() as connection:
        connection.execute(text(sql), dict(params))


@dataclass(frozen=True)
class PostgresWorkspaceRegistryStore:
    engine: Engine

    def write_workspace_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = InMemoryWorkspaceRegistryStore().write_workspace_row(row)
        _execute(
            self.engine,
            """
            INSERT INTO workspace_registry (
                workspace_id,
                owner_user_id,
                title,
                description,
                created_at,
                updated_at,
                last_run_id,
                last_result_status,
                continuity_source,
                archived
            ) VALUES (
                :workspace_id,
                :owner_user_id,
                :title,
                :description,
                :created_at,
                :updated_at,
                :last_run_id,
                :last_result_status,
                :continuity_source,
                :archived
            )
            ON CONFLICT (workspace_id) DO UPDATE SET
                owner_user_id = EXCLUDED.owner_user_id,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                created_at = COALESCE(workspace_registry.created_at, EXCLUDED.created_at),
                updated_at = EXCLUDED.updated_at,
                last_run_id = EXCLUDED.last_run_id,
                last_result_status = EXCLUDED.last_result_status,
                continuity_source = EXCLUDED.continuity_source,
                archived = EXCLUDED.archived
            """,
            normalized,
        )
        return dict(normalized)

    def write_membership_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = InMemoryWorkspaceRegistryStore().write_membership_row(row)
        _execute(
            self.engine,
            """
            INSERT INTO workspace_memberships (
                membership_id,
                workspace_id,
                user_id,
                role,
                created_at,
                updated_at
            ) VALUES (
                :membership_id,
                :workspace_id,
                :user_id,
                :role,
                :created_at,
                :updated_at
            )
            ON CONFLICT (workspace_id, user_id) DO UPDATE SET
                membership_id = EXCLUDED.membership_id,
                role = EXCLUDED.role,
                created_at = COALESCE(workspace_memberships.created_at, EXCLUDED.created_at),
                updated_at = EXCLUDED.updated_at
            """,
            normalized,
        )
        return dict(normalized)

    def write_workspace_bundle(self, workspace_row: Mapping[str, Any], membership_row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "workspace": self.write_workspace_row(workspace_row),
            "membership": self.write_membership_row(membership_row),
        }

    def list_workspace_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT workspace_id, owner_user_id, title, description, created_at, updated_at,
                   last_run_id, last_result_status, continuity_source, archived
            FROM workspace_registry
            ORDER BY updated_at DESC, workspace_id DESC
            """,
        )
        return tuple(dict(row) for row in rows)

    def get_workspace_row(self, workspace_id: str) -> dict[str, Any] | None:
        normalized_workspace_id = str(workspace_id or "").strip()
        if not normalized_workspace_id:
            return None
        return _fetch_one(
            self.engine,
            """
            SELECT workspace_id, owner_user_id, title, description, created_at, updated_at,
                   last_run_id, last_result_status, continuity_source, archived
            FROM workspace_registry
            WHERE workspace_id = :workspace_id
            """,
            {"workspace_id": normalized_workspace_id},
        )

    def list_membership_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT membership_id, workspace_id, user_id, role, created_at, updated_at
            FROM workspace_memberships
            ORDER BY updated_at DESC, workspace_id DESC, user_id DESC
            """,
        )
        return tuple(dict(row) for row in rows)

    def get_workspace_context(self, workspace_id: str) -> WorkspaceAuthorizationContext | None:
        workspace_row = self.get_workspace_row(workspace_id)
        if workspace_row is None:
            return None
        normalized_workspace_id = str(workspace_row.get("workspace_id") or "").strip()
        collaborator_user_refs: list[str] = []
        viewer_user_refs: list[str] = []
        membership_rows = _fetch_all(
            self.engine,
            """
            SELECT membership_id, workspace_id, user_id, role, created_at, updated_at
            FROM workspace_memberships
            WHERE workspace_id = :workspace_id
            ORDER BY updated_at DESC, user_id DESC
            """,
            {"workspace_id": normalized_workspace_id},
        )
        for row in membership_rows:
            user_id = str(row.get("user_id") or "").strip()
            role = str(row.get("role") or "").strip().lower()
            if not user_id:
                continue
            if role in _ALLOWED_COLLABORATOR_ROLES:
                collaborator_user_refs.append(user_id)
            elif role in _ALLOWED_VIEWER_ROLES:
                viewer_user_refs.append(user_id)
        return WorkspaceAuthorizationContext(
            workspace_id=normalized_workspace_id,
            owner_user_ref=str(workspace_row.get("owner_user_id") or "").strip() or None,
            collaborator_user_refs=tuple(sorted(set(collaborator_user_refs))),
            viewer_user_refs=tuple(sorted(set(viewer_user_refs))),
        )


@dataclass(frozen=True)
class PostgresOnboardingStateStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = InMemoryOnboardingStateStore().write(row)
        dismissed_guidance_state = _serialize_json(normalized.get("dismissed_guidance_state") or {})
        _execute(
            self.engine,
            f"""
            INSERT INTO onboarding_state (
                onboarding_state_id,
                user_id,
                workspace_id,
                first_success_achieved,
                advanced_surfaces_unlocked,
                dismissed_guidance_state,
                current_step,
                updated_at
            ) VALUES (
                :onboarding_state_id,
                :user_id,
                :workspace_id,
                :first_success_achieved,
                :advanced_surfaces_unlocked,
                {_json_placeholder(self.engine, 'dismissed_guidance_state')},
                :current_step,
                :updated_at
            )
            ON CONFLICT (user_id, workspace_id) DO UPDATE SET
                onboarding_state_id = EXCLUDED.onboarding_state_id,
                first_success_achieved = EXCLUDED.first_success_achieved,
                advanced_surfaces_unlocked = EXCLUDED.advanced_surfaces_unlocked,
                dismissed_guidance_state = EXCLUDED.dismissed_guidance_state,
                current_step = EXCLUDED.current_step,
                updated_at = EXCLUDED.updated_at
            """,
            {**normalized, "dismissed_guidance_state": dismissed_guidance_state},
        )
        return dict(normalized)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT onboarding_state_id, user_id, workspace_id, first_success_achieved,
                   advanced_surfaces_unlocked, dismissed_guidance_state, current_step, updated_at
            FROM onboarding_state
            ORDER BY updated_at DESC, user_id DESC, workspace_id DESC
            """,
        )
        normalized: list[dict[str, Any]] = []
        for row in rows:
            normalized.append({
                **row,
                "first_success_achieved": bool(row.get("first_success_achieved", False)),
                "advanced_surfaces_unlocked": bool(row.get("advanced_surfaces_unlocked", False)),
                "dismissed_guidance_state": _decode_json(row.get("dismissed_guidance_state"), default={}),
            })
        return tuple(normalized)


@dataclass(frozen=True)
class PostgresProviderBindingStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = InMemoryProviderBindingStore().write(row)
        _execute(
            self.engine,
            f"""
            INSERT INTO managed_provider_bindings (
                binding_id,
                workspace_id,
                provider_key,
                provider_family,
                display_name,
                credential_source,
                secret_ref,
                secret_version_ref,
                enabled,
                default_model_ref,
                allowed_model_refs,
                notes,
                created_by_user_id,
                updated_by_user_id,
                created_at,
                updated_at,
                last_rotated_at
            ) VALUES (
                :binding_id,
                :workspace_id,
                :provider_key,
                :provider_family,
                :display_name,
                :credential_source,
                :secret_ref,
                :secret_version_ref,
                :enabled,
                :default_model_ref,
                {_json_placeholder(self.engine, 'allowed_model_refs')},
                :notes,
                :created_by_user_id,
                :updated_by_user_id,
                :created_at,
                :updated_at,
                :last_rotated_at
            )
            ON CONFLICT (workspace_id, provider_key) DO UPDATE SET
                binding_id = EXCLUDED.binding_id,
                provider_family = EXCLUDED.provider_family,
                display_name = EXCLUDED.display_name,
                credential_source = EXCLUDED.credential_source,
                secret_ref = EXCLUDED.secret_ref,
                secret_version_ref = EXCLUDED.secret_version_ref,
                enabled = EXCLUDED.enabled,
                default_model_ref = EXCLUDED.default_model_ref,
                allowed_model_refs = EXCLUDED.allowed_model_refs,
                notes = EXCLUDED.notes,
                created_by_user_id = COALESCE(managed_provider_bindings.created_by_user_id, EXCLUDED.created_by_user_id),
                updated_by_user_id = EXCLUDED.updated_by_user_id,
                created_at = COALESCE(managed_provider_bindings.created_at, EXCLUDED.created_at),
                updated_at = EXCLUDED.updated_at,
                last_rotated_at = EXCLUDED.last_rotated_at
            """,
            {**normalized, "allowed_model_refs": _serialize_json(list(normalized.get("allowed_model_refs") or ()))},
        )
        return dict(normalized)

    def list_all_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT binding_id, workspace_id, provider_key, provider_family, display_name,
                   credential_source, secret_ref, secret_version_ref, enabled,
                   default_model_ref, allowed_model_refs, notes,
                   created_by_user_id, updated_by_user_id, created_at, updated_at, last_rotated_at
            FROM managed_provider_bindings
            ORDER BY COALESCE(updated_at, created_at) DESC, workspace_id DESC, provider_key DESC
            """,
        )
        return tuple(_normalize_provider_binding_row(row) for row in rows)

    def list_workspace_rows(self, workspace_id: str) -> tuple[dict[str, Any], ...]:
        normalized_workspace_id = str(workspace_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT binding_id, workspace_id, provider_key, provider_family, display_name,
                   credential_source, secret_ref, secret_version_ref, enabled,
                   default_model_ref, allowed_model_refs, notes,
                   created_by_user_id, updated_by_user_id, created_at, updated_at, last_rotated_at
            FROM managed_provider_bindings
            WHERE workspace_id = :workspace_id
            ORDER BY COALESCE(updated_at, created_at) DESC, provider_key DESC
            """,
            {"workspace_id": normalized_workspace_id},
        )
        return tuple(_normalize_provider_binding_row(row) for row in rows)

    def get_workspace_provider_row(self, workspace_id: str, provider_key: str) -> dict[str, Any] | None:
        normalized_workspace_id = str(workspace_id or "").strip()
        normalized_provider_key = str(provider_key or "").strip().lower()
        row = _fetch_one(
            self.engine,
            """
            SELECT binding_id, workspace_id, provider_key, provider_family, display_name,
                   credential_source, secret_ref, secret_version_ref, enabled,
                   default_model_ref, allowed_model_refs, notes,
                   created_by_user_id, updated_by_user_id, created_at, updated_at, last_rotated_at
            FROM managed_provider_bindings
            WHERE workspace_id = :workspace_id AND provider_key = :provider_key
            """,
            {"workspace_id": normalized_workspace_id, "provider_key": normalized_provider_key},
        )
        return None if row is None else _normalize_provider_binding_row(row)


def _normalize_provider_binding_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(row),
        "provider_key": str(row.get("provider_key") or "").strip().lower(),
        "enabled": bool(row.get("enabled", False)),
        "allowed_model_refs": tuple(str(item).strip() for item in _decode_json(row.get("allowed_model_refs"), default=[]) if str(item).strip()),
    }


@dataclass(frozen=True)
class PostgresProviderProbeHistoryStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        record = ProviderProbeHistoryRecord.from_mapping(row)
        if record is None:
            raise ValueError("provider_probe_history_store.row_invalid")
        normalized = record.to_mapping()
        _execute(
            self.engine,
            """
            INSERT INTO provider_probe_events (
                probe_event_id,
                workspace_id,
                binding_id,
                provider_key,
                provider_family,
                display_name,
                probe_status,
                connectivity_state,
                secret_resolution_status,
                requested_model_ref,
                effective_model_ref,
                round_trip_latency_ms,
                requested_by_user_id,
                message,
                occurred_at
            ) VALUES (
                :probe_event_id,
                :workspace_id,
                :binding_id,
                :provider_key,
                :provider_family,
                :display_name,
                :probe_status,
                :connectivity_state,
                :secret_resolution_status,
                :requested_model_ref,
                :effective_model_ref,
                :round_trip_latency_ms,
                :requested_by_user_id,
                :message,
                :occurred_at
            )
            ON CONFLICT (probe_event_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                binding_id = EXCLUDED.binding_id,
                provider_key = EXCLUDED.provider_key,
                provider_family = EXCLUDED.provider_family,
                display_name = EXCLUDED.display_name,
                probe_status = EXCLUDED.probe_status,
                connectivity_state = EXCLUDED.connectivity_state,
                secret_resolution_status = EXCLUDED.secret_resolution_status,
                requested_model_ref = EXCLUDED.requested_model_ref,
                effective_model_ref = EXCLUDED.effective_model_ref,
                round_trip_latency_ms = EXCLUDED.round_trip_latency_ms,
                requested_by_user_id = EXCLUDED.requested_by_user_id,
                message = EXCLUDED.message,
                occurred_at = EXCLUDED.occurred_at
            """,
            normalized,
        )
        return dict(normalized)

    def list_workspace_rows(self, workspace_id: str) -> tuple[dict[str, Any], ...]:
        normalized_workspace_id = str(workspace_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT probe_event_id, workspace_id, binding_id, provider_key, provider_family,
                   display_name, probe_status, connectivity_state, secret_resolution_status,
                   requested_model_ref, effective_model_ref, round_trip_latency_ms,
                   requested_by_user_id, occurred_at, message
            FROM provider_probe_events
            WHERE workspace_id = :workspace_id
            ORDER BY occurred_at DESC, probe_event_id DESC
            """,
            {"workspace_id": normalized_workspace_id},
        )
        return tuple(dict(row) for row in rows)

    def list_recent_rows(self, limit: int | None = None) -> tuple[dict[str, Any], ...]:
        sql = (
            "SELECT probe_event_id, workspace_id, binding_id, provider_key, provider_family, display_name, "
            "probe_status, connectivity_state, secret_resolution_status, requested_model_ref, effective_model_ref, "
            "round_trip_latency_ms, requested_by_user_id, occurred_at, message "
            "FROM provider_probe_events ORDER BY occurred_at DESC, probe_event_id DESC"
        )
        params: dict[str, Any] = {}
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = max(int(limit), 0)
        rows = _fetch_all(self.engine, sql, params)
        return tuple(dict(row) for row in rows)


@dataclass(frozen=True)
class PostgresManagedSecretMetadataStore:
    engine: Engine

    @staticmethod
    def _normalize_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
        return InMemoryManagedSecretMetadataStore().write_receipt(receipt)

    def write_receipt(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_receipt(receipt)
        _execute(
            self.engine,
            """
            INSERT INTO managed_secret_metadata (
                secret_ref,
                secret_version_ref,
                last_rotated_at,
                workspace_id,
                provider_key,
                secret_authority
            ) VALUES (
                :secret_ref,
                :secret_version_ref,
                :last_rotated_at,
                :workspace_id,
                :provider_key,
                :secret_authority
            )
            ON CONFLICT (secret_ref) DO UPDATE SET
                secret_version_ref = EXCLUDED.secret_version_ref,
                last_rotated_at = EXCLUDED.last_rotated_at,
                workspace_id = EXCLUDED.workspace_id,
                provider_key = EXCLUDED.provider_key,
                secret_authority = EXCLUDED.secret_authority
            """,
            normalized,
        )
        return dict(normalized)

    def read(self, secret_ref: str) -> dict[str, Any] | None:
        normalized_secret_ref = str(secret_ref or "").strip()
        if not normalized_secret_ref:
            return None
        return _fetch_one(
            self.engine,
            """
            SELECT secret_ref, secret_version_ref, last_rotated_at, workspace_id, provider_key, secret_authority
            FROM managed_secret_metadata
            WHERE secret_ref = :secret_ref
            """,
            {"secret_ref": normalized_secret_ref},
        )

    def list_all_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT secret_ref, secret_version_ref, last_rotated_at, workspace_id, provider_key, secret_authority
            FROM managed_secret_metadata
            ORDER BY last_rotated_at DESC, secret_ref DESC
            """,
        )
        return tuple(dict(row) for row in rows)


@dataclass(frozen=True)
class PostgresFeedbackStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        from src.server.feedback_store import InMemoryFeedbackStore

        normalized = InMemoryFeedbackStore().write(row)
        _execute(
            self.engine,
            """
            INSERT INTO workspace_feedback (
                feedback_id,
                user_id,
                workspace_id,
                workspace_title,
                category,
                surface,
                message,
                run_id,
                template_id,
                status,
                created_at
            ) VALUES (
                :feedback_id,
                :user_id,
                :workspace_id,
                :workspace_title,
                :category,
                :surface,
                :message,
                :run_id,
                :template_id,
                :status,
                :created_at
            )
            ON CONFLICT (feedback_id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                workspace_id = EXCLUDED.workspace_id,
                workspace_title = EXCLUDED.workspace_title,
                category = EXCLUDED.category,
                surface = EXCLUDED.surface,
                message = EXCLUDED.message,
                run_id = EXCLUDED.run_id,
                template_id = EXCLUDED.template_id,
                status = EXCLUDED.status,
                created_at = EXCLUDED.created_at
            """,
            normalized,
        )
        return dict(normalized)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT feedback_id, user_id, workspace_id, workspace_title, category, surface,
                   message, run_id, template_id, status, created_at
            FROM workspace_feedback
            ORDER BY created_at DESC, feedback_id DESC
            """,
        )
        return tuple(dict(row) for row in rows)


@dataclass(frozen=True)
class PostgresRunProjectionStore:
    engine: Engine
    workspace_registry_store: PostgresWorkspaceRegistryStore

    def write_run_record(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = RunRecordProjection(
            run_id=str(row.get("run_id") or "").strip(),
            workspace_id=str(row.get("workspace_id") or "").strip(),
            launch_request_id=str(row.get("launch_request_id") or "").strip(),
            execution_target_type=str(row.get("execution_target_type") or "").strip(),
            execution_target_ref=str(row.get("execution_target_ref") or "").strip(),
            status=str(row.get("status") or "").strip(),
            status_family=str(row.get("status_family") or "unknown").strip(),
            result_state=str(row.get("result_state") or "").strip() or None,
            latest_error_family=str(row.get("latest_error_family") or "").strip() or None,
            requested_by_user_id=str(row.get("requested_by_user_id") or "").strip() or None,
            auth_context_ref=str(row.get("auth_context_ref") or "").strip() or None,
            trace_available=bool(row.get("trace_available", False)),
            artifact_count=int(row.get("artifact_count", 0) or 0),
            trace_event_count=int(row.get("trace_event_count", 0) or 0),
            created_at=str(row.get("created_at") or "").strip(),
            started_at=str(row.get("started_at") or "").strip() or None,
            finished_at=str(row.get("finished_at") or "").strip() or None,
            updated_at=str(row.get("updated_at") or "").strip(),
        ).to_row()
        _execute(
            self.engine,
            """
            INSERT INTO run_records (
                run_id, workspace_id, launch_request_id, execution_target_type, execution_target_ref,
                status, status_family, result_state, latest_error_family, requested_by_user_id, auth_context_ref,
                trace_available, artifact_count, trace_event_count, created_at, started_at, finished_at, updated_at
            ) VALUES (
                :run_id, :workspace_id, :launch_request_id, :execution_target_type, :execution_target_ref,
                :status, :status_family, :result_state, :latest_error_family, :requested_by_user_id, :auth_context_ref,
                :trace_available, :artifact_count, :trace_event_count, :created_at, :started_at, :finished_at, :updated_at
            )
            ON CONFLICT (run_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                launch_request_id = EXCLUDED.launch_request_id,
                execution_target_type = EXCLUDED.execution_target_type,
                execution_target_ref = EXCLUDED.execution_target_ref,
                status = EXCLUDED.status,
                status_family = EXCLUDED.status_family,
                result_state = EXCLUDED.result_state,
                latest_error_family = EXCLUDED.latest_error_family,
                requested_by_user_id = EXCLUDED.requested_by_user_id,
                auth_context_ref = EXCLUDED.auth_context_ref,
                trace_available = EXCLUDED.trace_available,
                artifact_count = EXCLUDED.artifact_count,
                trace_event_count = EXCLUDED.trace_event_count,
                created_at = COALESCE(run_records.created_at, EXCLUDED.created_at),
                started_at = EXCLUDED.started_at,
                finished_at = EXCLUDED.finished_at,
                updated_at = EXCLUDED.updated_at
            """,
            normalized,
        )
        return dict(normalized)

    def get_run_record(self, run_id: str) -> dict[str, Any] | None:
        normalized_run_id = str(run_id or "").strip()
        if not normalized_run_id:
            return None
        return _fetch_one(
            self.engine,
            """
            SELECT run_id, workspace_id, launch_request_id, execution_target_type, execution_target_ref,
                   status, status_family, result_state, latest_error_family, requested_by_user_id, auth_context_ref,
                   trace_available, artifact_count, trace_event_count, created_at, started_at, finished_at, updated_at
            FROM run_records
            WHERE run_id = :run_id
            """,
            {"run_id": normalized_run_id},
        )

    def list_workspace_run_rows(self, workspace_id: str) -> tuple[dict[str, Any], ...]:
        normalized_workspace_id = str(workspace_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT run_id, workspace_id, launch_request_id, execution_target_type, execution_target_ref,
                   status, status_family, result_state, latest_error_family, requested_by_user_id, auth_context_ref,
                   trace_available, artifact_count, trace_event_count, created_at, started_at, finished_at, updated_at
            FROM run_records
            WHERE workspace_id = :workspace_id
            ORDER BY updated_at DESC, created_at DESC, run_id DESC
            """,
            {"workspace_id": normalized_workspace_id},
        )
        return tuple(dict(row) for row in rows)

    def list_recent_run_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT run_id, workspace_id, launch_request_id, execution_target_type, execution_target_ref,
                   status, status_family, result_state, latest_error_family, requested_by_user_id, auth_context_ref,
                   trace_available, artifact_count, trace_event_count, created_at, started_at, finished_at, updated_at
            FROM run_records
            ORDER BY updated_at DESC, created_at DESC, run_id DESC
            """,
        )
        return tuple(dict(row) for row in rows)

    def get_workspace_result_rows(self, workspace_id: str) -> dict[str, dict[str, Any]]:
        normalized_workspace_id = str(workspace_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT run_id, workspace_id, result_state, final_status, result_summary, trace_ref, artifact_count,
                   failure_info, final_output, metrics, updated_at
            FROM run_result_index
            WHERE workspace_id = :workspace_id
            ORDER BY updated_at DESC, run_id DESC
            """,
            {"workspace_id": normalized_workspace_id},
        )
        return {str(row.get("run_id") or ""): self._normalize_result_row(row) for row in rows if str(row.get("run_id") or "").strip()}

    def get_result_row(self, run_id: str) -> dict[str, Any] | None:
        normalized_run_id = str(run_id or "").strip()
        if not normalized_run_id:
            return None
        row = _fetch_one(
            self.engine,
            """
            SELECT run_id, workspace_id, result_state, final_status, result_summary, trace_ref, artifact_count,
                   failure_info, final_output, metrics, updated_at
            FROM run_result_index
            WHERE run_id = :run_id
            """,
            {"run_id": normalized_run_id},
        )
        return None if row is None else self._normalize_result_row(row)

    def get_run_context(self, run_id: str) -> RunAuthorizationContext | None:
        row = self.get_run_record(run_id)
        if row is None:
            return None
        workspace_context = self.workspace_registry_store.get_workspace_context(str(row.get("workspace_id") or ""))
        if workspace_context is None:
            return None
        owner = str(row.get("requested_by_user_id") or "").strip() or None
        return RunAuthorizationContext(run_id=str(row.get("run_id") or "").strip(), workspace_context=workspace_context, run_owner_user_ref=owner)

    @staticmethod
    def _normalize_result_row(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **dict(row),
            "artifact_count": int(row.get("artifact_count", 0) or 0),
            "failure_info": _decode_json(row.get("failure_info"), default=None),
            "final_output": _decode_json(row.get("final_output"), default=None),
            "metrics": _decode_json(row.get("metrics"), default=None),
        }


@dataclass(frozen=True)
class PostgresAppendOnlyProjectionStore:
    engine: Engine

    def list_artifact_rows(self, run_id: str) -> tuple[dict[str, Any], ...]:
        normalized_run_id = str(run_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT artifact_id, workspace_id, run_id, artifact_type, producer_node, content_hash,
                   storage_ref, payload_preview, trace_ref, metadata_json, created_at
            FROM artifact_index
            WHERE run_id = :run_id
            ORDER BY created_at DESC, artifact_id DESC
            """,
            {"run_id": normalized_run_id},
        )
        return tuple(self._normalize_artifact_row(row) for row in rows)

    def get_artifact_row(self, artifact_id: str) -> dict[str, Any] | None:
        normalized_artifact_id = str(artifact_id or "").strip()
        if not normalized_artifact_id:
            return None
        row = _fetch_one(
            self.engine,
            """
            SELECT artifact_id, workspace_id, run_id, artifact_type, producer_node, content_hash,
                   storage_ref, payload_preview, trace_ref, metadata_json, created_at
            FROM artifact_index
            WHERE artifact_id = :artifact_id
            """,
            {"artifact_id": normalized_artifact_id},
        )
        return None if row is None else self._normalize_artifact_row(row)

    def list_trace_rows(self, run_id: str) -> tuple[dict[str, Any], ...]:
        normalized_run_id = str(run_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT trace_event_ref, workspace_id, run_id, event_type, sequence_number, node_id, severity,
                   message_preview, occurred_at
            FROM trace_event_index
            WHERE run_id = :run_id
            ORDER BY sequence_number ASC, occurred_at ASC, trace_event_ref ASC
            """,
            {"run_id": normalized_run_id},
        )
        return tuple(dict(row) for row in rows)

    @staticmethod
    def _normalize_artifact_row(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **dict(row),
            "metadata_json": _decode_json(row.get("metadata_json"), default=None),
        }
