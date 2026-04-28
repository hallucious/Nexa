from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.managed_secret_metadata_store import InMemoryManagedSecretMetadataStore
from src.server.onboarding_state_store import InMemoryOnboardingStateStore
from src.server.provider_binding_store import InMemoryProviderBindingStore
from src.server.provider_secret_api import default_provider_catalog_rows
from src.server.provider_catalog_runtime import default_provider_model_catalog_rows
from src.server.provider_probe_history_models import ProviderProbeHistoryRecord
from src.server.provider_probe_history_store import InMemoryProviderProbeHistoryStore
from src.server.workspace_registry_store import InMemoryWorkspaceRegistryStore
from src.server.run_admission_models import RunRecordProjection
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.serialization import serialize_nex_artifact, validate_serialized_storage_artifact_for_write
from src.storage.share_api import (
    describe_public_nex_link_share,
    list_issuer_public_share_management_action_reports_for_issuer,
    load_public_nex_link_share,
)

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
class PostgresWorkspaceArtifactSourceStore:
    engine: Engine

    def write(self, workspace_id: str, artifact_source: Any) -> dict[str, Any]:
        normalized_workspace_id = str(workspace_id or "").strip()
        if not normalized_workspace_id:
            raise ValueError("workspace_artifact_source_store.workspace_id_required")
        normalized_source = self._normalize_artifact_source(artifact_source)
        meta = normalized_source.get("meta") if isinstance(normalized_source.get("meta"), dict) else {}
        storage_role = str(meta.get("storage_role") or "").strip()
        canonical_ref = self._canonical_ref_for(storage_role, meta)
        updated_at = str(meta.get("updated_at") or meta.get("created_at") or "").strip() or None
        _execute(
            self.engine,
            f"""
            INSERT INTO workspace_artifact_sources (
                workspace_id,
                storage_role,
                canonical_ref,
                artifact_source,
                updated_at
            ) VALUES (
                :workspace_id,
                :storage_role,
                :canonical_ref,
                {_json_placeholder(self.engine, 'artifact_source')},
                :updated_at
            )
            ON CONFLICT (workspace_id) DO UPDATE SET
                storage_role = EXCLUDED.storage_role,
                canonical_ref = EXCLUDED.canonical_ref,
                artifact_source = EXCLUDED.artifact_source,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "workspace_id": normalized_workspace_id,
                "storage_role": storage_role,
                "canonical_ref": canonical_ref,
                "artifact_source": _serialize_json(normalized_source),
                "updated_at": updated_at,
            },
        )
        return dict(normalized_source)

    def get(self, workspace_id: str) -> dict[str, Any] | None:
        normalized_workspace_id = str(workspace_id or "").strip()
        if not normalized_workspace_id:
            return None
        row = _fetch_one(
            self.engine,
            """
            SELECT artifact_source
            FROM workspace_artifact_sources
            WHERE workspace_id = :workspace_id
            """,
            {"workspace_id": normalized_workspace_id},
        )
        if row is None:
            return None
        artifact_source = _decode_json(row.get("artifact_source"), default=None)
        return dict(artifact_source) if isinstance(artifact_source, dict) else None

    @staticmethod
    def _canonical_ref_for(storage_role: str, meta: Mapping[str, Any]) -> str | None:
        if storage_role == "working_save":
            value = str(meta.get("working_save_id") or "").strip()
            return value or None
        if storage_role == "commit_snapshot":
            value = str(meta.get("commit_id") or "").strip()
            return value or None
        return None

    @staticmethod
    def _normalize_artifact_source(artifact_source: Any) -> dict[str, Any]:
        if isinstance(artifact_source, LoadedNexArtifact):
            if artifact_source.parsed_model is None:
                raise ValueError("workspace_artifact_source_store.artifact_unloadable")
            payload = serialize_nex_artifact(artifact_source.parsed_model)
        else:
            payload = serialize_nex_artifact(artifact_source)
        validated = validate_serialized_storage_artifact_for_write(payload)
        meta = validated.get("meta") if isinstance(validated.get("meta"), dict) else {}
        storage_role = str(meta.get("storage_role") or "").strip()
        if storage_role not in {"working_save", "commit_snapshot"}:
            raise ValueError("workspace_artifact_source_store.unsupported_storage_role")
        return dict(validated)


@dataclass(frozen=True)
class PostgresPublicSharePayloadStore:
    engine: Engine

    def write(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized = load_public_nex_link_share(dict(payload))
        descriptor = describe_public_nex_link_share(normalized)
        lifecycle = normalized.get("share", {}).get("lifecycle", {}) if isinstance(normalized.get("share"), dict) else {}
        management = normalized.get("share", {}).get("management", {}) if isinstance(normalized.get("share"), dict) else {}
        _execute(
            self.engine,
            f"""
            INSERT INTO public_share_payloads (
                share_id,
                issued_by_user_ref,
                storage_role,
                canonical_ref,
                lifecycle_state,
                archived,
                expires_at,
                created_at,
                updated_at,
                share_payload
            ) VALUES (
                :share_id,
                :issued_by_user_ref,
                :storage_role,
                :canonical_ref,
                :lifecycle_state,
                :archived,
                :expires_at,
                :created_at,
                :updated_at,
                {_json_placeholder(self.engine, 'share_payload')}
            )
            ON CONFLICT (share_id) DO UPDATE SET
                issued_by_user_ref = EXCLUDED.issued_by_user_ref,
                storage_role = EXCLUDED.storage_role,
                canonical_ref = EXCLUDED.canonical_ref,
                lifecycle_state = EXCLUDED.lifecycle_state,
                archived = EXCLUDED.archived,
                expires_at = EXCLUDED.expires_at,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                share_payload = EXCLUDED.share_payload
            """,
            {
                "share_id": descriptor.share_id,
                "issued_by_user_ref": descriptor.issued_by_user_ref,
                "storage_role": descriptor.storage_role,
                "canonical_ref": descriptor.canonical_ref,
                "lifecycle_state": descriptor.stored_lifecycle_state,
                "archived": descriptor.archived,
                "expires_at": descriptor.expires_at,
                "created_at": descriptor.created_at,
                "updated_at": descriptor.updated_at,
                "share_payload": _serialize_json(normalized),
            },
        )
        return dict(normalized)

    def get(self, share_id: str) -> dict[str, Any] | None:
        normalized_share_id = str(share_id or "").strip()
        if not normalized_share_id:
            return None
        row = _fetch_one(
            self.engine,
            """
            SELECT share_payload
            FROM public_share_payloads
            WHERE share_id = :share_id
            """,
            {"share_id": normalized_share_id},
        )
        if row is None:
            return None
        payload = _decode_json(row.get("share_payload"), default=None)
        return dict(payload) if isinstance(payload, dict) else None

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT share_payload
            FROM public_share_payloads
            ORDER BY updated_at DESC, share_id DESC
            """,
        )
        payloads: list[dict[str, Any]] = []
        for row in rows:
            payload = _decode_json(row.get("share_payload"), default=None)
            if isinstance(payload, dict):
                payloads.append(dict(payload))
        return tuple(payloads)

    def delete(self, share_id: str) -> bool:
        normalized_share_id = str(share_id or "").strip()
        if not normalized_share_id:
            return False
        _require_sqlalchemy()
        with self.engine.begin() as connection:
            result = connection.execute(text("DELETE FROM public_share_payloads WHERE share_id = :share_id"), {"share_id": normalized_share_id})
        return bool(getattr(result, "rowcount", 0))


@dataclass(frozen=True)
class PostgresPublicShareActionReportStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        issuer_user_ref = str(row.get("issuer_user_ref") or "").strip()
        if not issuer_user_ref:
            raise ValueError("public_share_action_report_store.issuer_user_ref_required")
        normalized_entry = list_issuer_public_share_management_action_reports_for_issuer((dict(row),), issuer_user_ref, limit=1, offset=0)[0]
        normalized = asdict(normalized_entry)
        _execute(
            self.engine,
            f"""
            INSERT INTO public_share_action_reports (
                report_id,
                issuer_user_ref,
                action,
                scope,
                affected_share_count,
                created_at,
                action_report
            ) VALUES (
                :report_id,
                :issuer_user_ref,
                :action,
                :scope,
                :affected_share_count,
                :created_at,
                {_json_placeholder(self.engine, 'action_report')}
            )
            ON CONFLICT (report_id) DO UPDATE SET
                issuer_user_ref = EXCLUDED.issuer_user_ref,
                action = EXCLUDED.action,
                scope = EXCLUDED.scope,
                affected_share_count = EXCLUDED.affected_share_count,
                created_at = EXCLUDED.created_at,
                action_report = EXCLUDED.action_report
            """,
            {
                "report_id": normalized["report_id"],
                "issuer_user_ref": normalized["issuer_user_ref"],
                "action": normalized["action"],
                "scope": normalized["scope"],
                "affected_share_count": normalized["affected_share_count"],
                "created_at": normalized["created_at"],
                "action_report": _serialize_json(normalized),
            },
        )
        return dict(normalized)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT action_report
            FROM public_share_action_reports
            ORDER BY created_at DESC, report_id DESC
            """,
        )
        reports: list[dict[str, Any]] = []
        for row in rows:
            payload = _decode_json(row.get("action_report"), default=None)
            if isinstance(payload, dict):
                reports.append(dict(payload))
        return tuple(reports)


@dataclass(frozen=True)
class PostgresSavedPublicShareStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_row(row)
        _execute(
            self.engine,
            """
            INSERT INTO saved_public_shares (
                saved_row_ref,
                share_id,
                saved_by_user_ref,
                saved_at
            ) VALUES (
                :saved_row_ref,
                :share_id,
                :saved_by_user_ref,
                :saved_at
            )
            ON CONFLICT (saved_by_user_ref, share_id) DO UPDATE SET
                saved_row_ref = EXCLUDED.saved_row_ref,
                saved_at = EXCLUDED.saved_at
            """,
            normalized,
        )
        return {
            "share_id": normalized["share_id"],
            "saved_by_user_ref": normalized["saved_by_user_ref"],
            "saved_at": normalized["saved_at"],
        }

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT share_id, saved_by_user_ref, saved_at
            FROM saved_public_shares
            ORDER BY saved_at DESC, share_id DESC
            """,
        )
        return tuple(dict(row) for row in rows)

    def delete(self, share_id: str) -> bool:
        normalized_share_id = str(share_id or "").strip()
        if not normalized_share_id:
            return False
        _require_sqlalchemy()
        with self.engine.begin() as connection:
            result = connection.execute(text("DELETE FROM saved_public_shares WHERE share_id = :share_id"), {"share_id": normalized_share_id})
        return bool(getattr(result, "rowcount", 0))

    @staticmethod
    def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
        share_id = str(row.get("share_id") or "").strip()
        saved_by_user_ref = str(row.get("saved_by_user_ref") or "").strip()
        saved_at = str(row.get("saved_at") or "").strip()
        if not share_id:
            raise ValueError("saved_public_share_store.share_id_required")
        if not saved_by_user_ref:
            raise ValueError("saved_public_share_store.saved_by_user_ref_required")
        if not saved_at:
            raise ValueError("saved_public_share_store.saved_at_required")
        return {
            "saved_row_ref": f"{saved_by_user_ref}:{share_id}",
            "share_id": share_id,
            "saved_by_user_ref": saved_by_user_ref,
            "saved_at": saved_at,
        }


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
class PostgresProviderCatalogStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_row(row)
        _execute(
            self.engine,
            """
            INSERT INTO provider_catalog_entries (
                provider_key,
                provider_family,
                display_name,
                managed_supported,
                recommended_scope,
                local_env_var_hint,
                default_secret_name_template,
                lifecycle_state,
                updated_at
            ) VALUES (
                :provider_key,
                :provider_family,
                :display_name,
                :managed_supported,
                :recommended_scope,
                :local_env_var_hint,
                :default_secret_name_template,
                :lifecycle_state,
                :updated_at
            )
            ON CONFLICT (provider_key) DO UPDATE SET
                provider_family = EXCLUDED.provider_family,
                display_name = EXCLUDED.display_name,
                managed_supported = EXCLUDED.managed_supported,
                recommended_scope = EXCLUDED.recommended_scope,
                local_env_var_hint = EXCLUDED.local_env_var_hint,
                default_secret_name_template = EXCLUDED.default_secret_name_template,
                lifecycle_state = EXCLUDED.lifecycle_state,
                updated_at = EXCLUDED.updated_at
            """,
            normalized,
        )
        return dict(normalized)

    def seed_defaults(self, rows: Sequence[Mapping[str, Any]] | None = None) -> tuple[dict[str, Any], ...]:
        seeded = rows if rows is not None else default_provider_catalog_rows()
        return tuple(self.write(row) for row in seeded)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT provider_key, provider_family, display_name, managed_supported,
                   recommended_scope, local_env_var_hint, default_secret_name_template,
                   lifecycle_state, updated_at
            FROM provider_catalog_entries
            WHERE lifecycle_state != 'archived'
            ORDER BY provider_key ASC
            """,
        )
        return tuple(self._normalize_row(row) for row in rows)

    @staticmethod
    def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
        provider_key = str(row.get("provider_key") or "").strip().lower()
        if not provider_key:
            raise ValueError("provider_catalog_store.provider_key_required")
        provider_family = str(row.get("provider_family") or provider_key).strip() or provider_key
        display_name = str(row.get("display_name") or provider_key).strip() or provider_key
        recommended_scope = str(row.get("recommended_scope") or "workspace").strip() or "workspace"
        lifecycle_state = str(row.get("lifecycle_state") or "active").strip() or "active"
        updated_at = str(row.get("updated_at") or "").strip() or None
        return {
            "provider_key": provider_key,
            "provider_family": provider_family,
            "display_name": display_name,
            "managed_supported": bool(row.get("managed_supported", True)),
            "recommended_scope": recommended_scope,
            "local_env_var_hint": str(row.get("local_env_var_hint") or "").strip() or None,
            "default_secret_name_template": str(row.get("default_secret_name_template") or "").strip() or None,
            "lifecycle_state": lifecycle_state,
            "updated_at": updated_at,
        }


@dataclass(frozen=True)
class PostgresProviderCostCatalogStore:
    engine: Engine

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_row(row)
        plan_availability = _serialize_json(normalized["plan_availability"])
        default_for_plans = _serialize_json(normalized.get("default_for_plans") or ())
        _execute(
            self.engine,
            f"""
            INSERT INTO provider_cost_catalog (
                provider_model_key,
                provider_key,
                provider_family,
                model_ref,
                model_display_name,
                tier,
                plan_availability,
                default_for_plans,
                cost_ratio,
                pricing_unit,
                lifecycle_state,
                updated_at
            ) VALUES (
                :provider_model_key,
                :provider_key,
                :provider_family,
                :model_ref,
                :model_display_name,
                :tier,
                {_json_placeholder(self.engine, 'plan_availability')},
                {_json_placeholder(self.engine, 'default_for_plans')},
                :cost_ratio,
                :pricing_unit,
                :lifecycle_state,
                :updated_at
            )
            ON CONFLICT (provider_model_key) DO UPDATE SET
                provider_key = EXCLUDED.provider_key,
                provider_family = EXCLUDED.provider_family,
                model_ref = EXCLUDED.model_ref,
                model_display_name = EXCLUDED.model_display_name,
                tier = EXCLUDED.tier,
                plan_availability = EXCLUDED.plan_availability,
                default_for_plans = EXCLUDED.default_for_plans,
                cost_ratio = EXCLUDED.cost_ratio,
                pricing_unit = EXCLUDED.pricing_unit,
                lifecycle_state = EXCLUDED.lifecycle_state,
                updated_at = EXCLUDED.updated_at
            """,
            {
                **normalized,
                "plan_availability": plan_availability,
                "default_for_plans": default_for_plans,
            },
        )
        return dict(normalized)

    def seed_defaults(self, rows: Sequence[Mapping[str, Any]] | None = None) -> tuple[dict[str, Any], ...]:
        seeded = rows if rows is not None else default_provider_model_catalog_rows()
        return tuple(self.write(row) for row in seeded)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = _fetch_all(
            self.engine,
            """
            SELECT provider_model_key, provider_key, provider_family, model_ref,
                   model_display_name, tier, plan_availability, default_for_plans,
                   cost_ratio, pricing_unit, lifecycle_state, updated_at
            FROM provider_cost_catalog
            WHERE lifecycle_state != 'archived'
            ORDER BY provider_key ASC, model_ref ASC
            """,
        )
        return tuple(self._normalize_row(row) for row in rows)

    @staticmethod
    def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
        provider_key = str(row.get("provider_key") or "").strip().lower()
        model_ref = str(row.get("model_ref") or "").strip().lower()
        provider_model_key = str(row.get("provider_model_key") or f"{provider_key}:{model_ref}").strip().lower()
        if not provider_key:
            raise ValueError("provider_cost_catalog_store.provider_key_required")
        if not model_ref:
            raise ValueError("provider_cost_catalog_store.model_ref_required")
        if not provider_model_key:
            raise ValueError("provider_cost_catalog_store.provider_model_key_required")
        return {
            "provider_model_key": provider_model_key,
            "provider_key": provider_key,
            "provider_family": str(row.get("provider_family") or provider_key).strip() or provider_key,
            "model_ref": model_ref,
            "model_display_name": str(row.get("model_display_name") or model_ref).strip() or model_ref,
            "tier": str(row.get("tier") or "economy").strip() or "economy",
            "plan_availability": tuple(str(item).strip().lower() for item in _decode_json(row.get("plan_availability"), default=row.get("plan_availability") or ()) if str(item).strip()),
            "default_for_plans": tuple(str(item).strip().lower() for item in _decode_json(row.get("default_for_plans"), default=row.get("default_for_plans") or ()) if str(item).strip()),
            "cost_ratio": float(row.get("cost_ratio") or 1.0),
            "pricing_unit": str(row.get("pricing_unit") or "relative_unit").strip() or "relative_unit",
            "lifecycle_state": str(row.get("lifecycle_state") or "active").strip() or "active",
            "updated_at": str(row.get("updated_at") or "").strip() or None,
        }


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

@dataclass(frozen=True)
class PostgresFileUploadStore:
    engine: Engine

    def write_upload(self, record) -> Any:
        from src.server.documents.file_ingestion_store import _record_from_row
        from src.server.documents.file_ingestion_models import FileUploadRecord
        normalized = record if isinstance(record, FileUploadRecord) else _record_from_row(record)
        row = normalized.to_row()
        _execute(
            self.engine,
            f"""
            INSERT INTO file_uploads (
                upload_id,
                workspace_id,
                object_ref,
                original_filename,
                declared_mime_type,
                declared_size_bytes,
                upload_state,
                document_type,
                rejection_reason_code,
                observed_mime_type,
                observed_size_bytes,
                extracted_text_char_count,
                created_at,
                updated_at,
                expires_at,
                requested_by_user_ref,
                metadata
            ) VALUES (
                :upload_id,
                :workspace_id,
                :object_ref,
                :original_filename,
                :declared_mime_type,
                :declared_size_bytes,
                :upload_state,
                :document_type,
                :rejection_reason_code,
                :observed_mime_type,
                :observed_size_bytes,
                :extracted_text_char_count,
                :created_at,
                :updated_at,
                :expires_at,
                :requested_by_user_ref,
                {_json_placeholder(self.engine, 'metadata')}
            )
            ON CONFLICT (upload_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                object_ref = EXCLUDED.object_ref,
                original_filename = EXCLUDED.original_filename,
                declared_mime_type = EXCLUDED.declared_mime_type,
                declared_size_bytes = EXCLUDED.declared_size_bytes,
                upload_state = EXCLUDED.upload_state,
                document_type = EXCLUDED.document_type,
                rejection_reason_code = EXCLUDED.rejection_reason_code,
                observed_mime_type = EXCLUDED.observed_mime_type,
                observed_size_bytes = EXCLUDED.observed_size_bytes,
                extracted_text_char_count = EXCLUDED.extracted_text_char_count,
                updated_at = EXCLUDED.updated_at,
                expires_at = EXCLUDED.expires_at,
                requested_by_user_ref = EXCLUDED.requested_by_user_ref,
                metadata = EXCLUDED.metadata
            """,
            {**row, "metadata": _serialize_json(row.get("metadata") or {})},
        )
        return normalized

    def get_upload(self, upload_id: str):
        from src.server.documents.file_ingestion_store import _record_from_row
        normalized = str(upload_id or "").strip()
        if not normalized:
            return None
        row = _fetch_one(
            self.engine,
            """
            SELECT upload_id, workspace_id, object_ref, original_filename,
                   declared_mime_type, declared_size_bytes, upload_state,
                   document_type, rejection_reason_code, observed_mime_type,
                   observed_size_bytes, extracted_text_char_count, created_at,
                   updated_at, expires_at, requested_by_user_ref, metadata
            FROM file_uploads
            WHERE upload_id = :upload_id
            """,
            {"upload_id": normalized},
        )
        if row is None:
            return None
        row["metadata"] = _decode_json(row.get("metadata"), default={})
        return _record_from_row(row)

    def get_workspace_upload(self, workspace_id: str, upload_id: str):
        record = self.get_upload(upload_id)
        if record is None or record.workspace_id != str(workspace_id or "").strip():
            return None
        return record

    def list_workspace_uploads(self, workspace_id: str):
        from src.server.documents.file_ingestion_store import _record_from_row
        normalized = str(workspace_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT upload_id, workspace_id, object_ref, original_filename,
                   declared_mime_type, declared_size_bytes, upload_state,
                   document_type, rejection_reason_code, observed_mime_type,
                   observed_size_bytes, extracted_text_char_count, created_at,
                   updated_at, expires_at, requested_by_user_ref, metadata
            FROM file_uploads
            WHERE workspace_id = :workspace_id
            ORDER BY updated_at DESC, upload_id DESC
            """,
            {"workspace_id": normalized},
        )
        normalized_rows = []
        for row in rows:
            row["metadata"] = _decode_json(row.get("metadata"), default={})
            normalized_rows.append(_record_from_row(row))
        return tuple(normalized_rows)

    def update_upload_state(
        self,
        *,
        upload_id: str,
        upload_state: str,
        updated_at: str | None = None,
        rejection_reason_code: str | None = None,
        observed_mime_type: str | None = None,
        observed_size_bytes: int | None = None,
        extracted_text_char_count: int | None = None,
    ):
        existing = self.get_upload(upload_id)
        if existing is None:
            return None
        from dataclasses import replace as _replace
        updated = _replace(
            existing,
            upload_state=str(upload_state or "").strip().lower(),
            updated_at=updated_at or existing.updated_at,
            rejection_reason_code=rejection_reason_code,
            observed_mime_type=observed_mime_type or existing.observed_mime_type,
            observed_size_bytes=observed_size_bytes if observed_size_bytes is not None else existing.observed_size_bytes,
            extracted_text_char_count=extracted_text_char_count if extracted_text_char_count is not None else existing.extracted_text_char_count,
        )
        return self.write_upload(updated)

    def append_event(self, event) -> Any:
        from src.server.documents.file_ingestion_store import _event_from_row
        from src.server.documents.file_ingestion_models import FileUploadEventRecord
        normalized = event if isinstance(event, FileUploadEventRecord) else _event_from_row(event)
        row = normalized.to_row()
        _execute(
            self.engine,
            f"""
            INSERT INTO file_upload_events (
                event_id,
                upload_id,
                workspace_id,
                event_type,
                from_state,
                to_state,
                reason_code,
                created_at,
                actor_user_ref,
                event_metadata
            ) VALUES (
                :event_id,
                :upload_id,
                :workspace_id,
                :event_type,
                :from_state,
                :to_state,
                :reason_code,
                :created_at,
                :actor_user_ref,
                {_json_placeholder(self.engine, 'event_metadata')}
            )
            """,
            {**row, "event_metadata": _serialize_json(row.get("event_metadata") or {})},
        )
        return normalized

    def list_events(self, upload_id: str):
        from src.server.documents.file_ingestion_store import _event_from_row
        normalized = str(upload_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT event_id, upload_id, workspace_id, event_type, from_state,
                   to_state, reason_code, created_at, actor_user_ref, event_metadata
            FROM file_upload_events
            WHERE upload_id = :upload_id
            ORDER BY created_at ASC, event_id ASC
            """,
            {"upload_id": normalized},
        )
        normalized_rows = []
        for row in rows:
            row["event_metadata"] = _decode_json(row.get("event_metadata"), default={})
            normalized_rows.append(_event_from_row(row))
        return tuple(normalized_rows)


@dataclass(frozen=True)
class PostgresFileExtractionStore:
    engine: Engine

    def write_extraction(self, record) -> Any:
        from src.server.documents.file_extraction_store import _record_from_row
        from src.server.documents.file_extraction_models import FileExtractionRecord
        normalized = record if isinstance(record, FileExtractionRecord) else _record_from_row(record)
        row = normalized.to_row()
        _execute(
            self.engine,
            f"""
            INSERT INTO file_extractions (
                extraction_id,
                workspace_id,
                upload_id,
                extraction_state,
                source_document_type,
                source_object_ref,
                text_artifact_ref,
                extracted_text_char_count,
                text_preview,
                content_hash,
                rejection_reason_code,
                extractor_ref,
                created_at,
                updated_at,
                requested_by_user_ref,
                metadata
            ) VALUES (
                :extraction_id,
                :workspace_id,
                :upload_id,
                :extraction_state,
                :source_document_type,
                :source_object_ref,
                :text_artifact_ref,
                :extracted_text_char_count,
                :text_preview,
                :content_hash,
                :rejection_reason_code,
                :extractor_ref,
                :created_at,
                :updated_at,
                :requested_by_user_ref,
                {_json_placeholder(self.engine, 'metadata')}
            )
            ON CONFLICT (extraction_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                upload_id = EXCLUDED.upload_id,
                extraction_state = EXCLUDED.extraction_state,
                source_document_type = EXCLUDED.source_document_type,
                source_object_ref = EXCLUDED.source_object_ref,
                text_artifact_ref = EXCLUDED.text_artifact_ref,
                extracted_text_char_count = EXCLUDED.extracted_text_char_count,
                text_preview = EXCLUDED.text_preview,
                content_hash = EXCLUDED.content_hash,
                rejection_reason_code = EXCLUDED.rejection_reason_code,
                extractor_ref = EXCLUDED.extractor_ref,
                updated_at = EXCLUDED.updated_at,
                requested_by_user_ref = EXCLUDED.requested_by_user_ref,
                metadata = EXCLUDED.metadata
            """,
            {**row, "metadata": _serialize_json(row.get("metadata") or {})},
        )
        return normalized

    def get_extraction(self, extraction_id: str):
        from src.server.documents.file_extraction_store import _record_from_row
        normalized = str(extraction_id or "").strip()
        if not normalized:
            return None
        row = _fetch_one(
            self.engine,
            """
            SELECT extraction_id, workspace_id, upload_id, extraction_state,
                   source_document_type, source_object_ref, text_artifact_ref,
                   extracted_text_char_count, text_preview, content_hash,
                   rejection_reason_code, extractor_ref, created_at, updated_at,
                   requested_by_user_ref, metadata
            FROM file_extractions
            WHERE extraction_id = :extraction_id
            """,
            {"extraction_id": normalized},
        )
        if row is None:
            return None
        row["metadata"] = _decode_json(row.get("metadata"), default={})
        return _record_from_row(row)

    def get_workspace_extraction(self, workspace_id: str, extraction_id: str):
        record = self.get_extraction(extraction_id)
        if record is None or record.workspace_id != str(workspace_id or "").strip():
            return None
        return record

    def list_workspace_extractions(self, workspace_id: str):
        from src.server.documents.file_extraction_store import _record_from_row
        normalized = str(workspace_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT extraction_id, workspace_id, upload_id, extraction_state,
                   source_document_type, source_object_ref, text_artifact_ref,
                   extracted_text_char_count, text_preview, content_hash,
                   rejection_reason_code, extractor_ref, created_at, updated_at,
                   requested_by_user_ref, metadata
            FROM file_extractions
            WHERE workspace_id = :workspace_id
            ORDER BY updated_at DESC, extraction_id DESC
            """,
            {"workspace_id": normalized},
        )
        normalized_rows = []
        for row in rows:
            row["metadata"] = _decode_json(row.get("metadata"), default={})
            normalized_rows.append(_record_from_row(row))
        return tuple(normalized_rows)

    def list_upload_extractions(self, workspace_id: str, upload_id: str):
        from src.server.documents.file_extraction_store import _record_from_row
        normalized_workspace = str(workspace_id or "").strip()
        normalized_upload = str(upload_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT extraction_id, workspace_id, upload_id, extraction_state,
                   source_document_type, source_object_ref, text_artifact_ref,
                   extracted_text_char_count, text_preview, content_hash,
                   rejection_reason_code, extractor_ref, created_at, updated_at,
                   requested_by_user_ref, metadata
            FROM file_extractions
            WHERE workspace_id = :workspace_id AND upload_id = :upload_id
            ORDER BY created_at DESC, extraction_id DESC
            """,
            {"workspace_id": normalized_workspace, "upload_id": normalized_upload},
        )
        normalized_rows = []
        for row in rows:
            row["metadata"] = _decode_json(row.get("metadata"), default={})
            normalized_rows.append(_record_from_row(row))
        return tuple(normalized_rows)

    def list_queued_extractions(self, *, workspace_id: str | None = None, limit: int | None = None):
        from src.server.documents.file_extraction_store import _record_from_row
        params: dict[str, Any] = {}
        where = "WHERE extraction_state = 'queued'"
        if workspace_id is not None and str(workspace_id or "").strip():
            where += " AND workspace_id = :workspace_id"
            params["workspace_id"] = str(workspace_id or "").strip()
        sql = f"""
            SELECT extraction_id, workspace_id, upload_id, extraction_state,
                   source_document_type, source_object_ref, text_artifact_ref,
                   extracted_text_char_count, text_preview, content_hash,
                   rejection_reason_code, extractor_ref, created_at, updated_at,
                   requested_by_user_ref, metadata
            FROM file_extractions
            {where}
            ORDER BY created_at ASC, extraction_id ASC
        """
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = max(int(limit), 0)
        rows = _fetch_all(self.engine, sql, params)
        normalized_rows = []
        for row in rows:
            row["metadata"] = _decode_json(row.get("metadata"), default={})
            normalized_rows.append(_record_from_row(row))
        return tuple(normalized_rows)

    def list_stale_active_extractions(self, *, older_than_iso: str):
        from src.server.documents.file_extraction_store import _record_from_row
        cutoff = str(older_than_iso or "").strip()
        if not cutoff:
            return ()
        rows = _fetch_all(
            self.engine,
            """
            SELECT extraction_id, workspace_id, upload_id, extraction_state,
                   source_document_type, source_object_ref, text_artifact_ref,
                   extracted_text_char_count, text_preview, content_hash,
                   rejection_reason_code, extractor_ref, created_at, updated_at,
                   requested_by_user_ref, metadata
            FROM file_extractions
            WHERE extraction_state IN ('queued', 'extracting')
              AND COALESCE(updated_at, created_at, '') < :older_than_iso
            ORDER BY COALESCE(updated_at, created_at, '') ASC, extraction_id ASC
            """,
            {"older_than_iso": cutoff},
        )
        normalized_rows = []
        for row in rows:
            row["metadata"] = _decode_json(row.get("metadata"), default={})
            normalized_rows.append(_record_from_row(row))
        return tuple(normalized_rows)

    def update_extraction_state(
        self,
        *,
        extraction_id: str,
        extraction_state: str,
        updated_at: str | None = None,
        text_artifact_ref: str | None = None,
        extracted_text_char_count: int | None = None,
        text_preview: str | None = None,
        content_hash: str | None = None,
        rejection_reason_code: str | None = None,
        extractor_ref: str | None = None,
    ):
        existing = self.get_extraction(extraction_id)
        if existing is None:
            return None
        from dataclasses import replace as _replace
        updated = _replace(
            existing,
            extraction_state=str(extraction_state or "").strip().lower(),
            updated_at=updated_at or existing.updated_at,
            text_artifact_ref=text_artifact_ref if text_artifact_ref is not None else existing.text_artifact_ref,
            extracted_text_char_count=extracted_text_char_count if extracted_text_char_count is not None else existing.extracted_text_char_count,
            text_preview=text_preview if text_preview is not None else existing.text_preview,
            content_hash=content_hash if content_hash is not None else existing.content_hash,
            rejection_reason_code=rejection_reason_code,
            extractor_ref=extractor_ref if extractor_ref is not None else existing.extractor_ref,
        )
        return self.write_extraction(updated)

    def append_event(self, event) -> Any:
        from src.server.documents.file_extraction_store import _event_from_row
        from src.server.documents.file_extraction_models import FileExtractionEventRecord
        normalized = event if isinstance(event, FileExtractionEventRecord) else _event_from_row(event)
        row = normalized.to_row()
        _execute(
            self.engine,
            f"""
            INSERT INTO file_extraction_events (
                event_id,
                extraction_id,
                workspace_id,
                upload_id,
                event_type,
                from_state,
                to_state,
                reason_code,
                created_at,
                actor_user_ref,
                event_metadata
            ) VALUES (
                :event_id,
                :extraction_id,
                :workspace_id,
                :upload_id,
                :event_type,
                :from_state,
                :to_state,
                :reason_code,
                :created_at,
                :actor_user_ref,
                {_json_placeholder(self.engine, 'event_metadata')}
            )
            """,
            {**row, "event_metadata": _serialize_json(row.get("event_metadata") or {})},
        )
        return normalized

    def list_events(self, extraction_id: str):
        from src.server.documents.file_extraction_store import _event_from_row
        normalized = str(extraction_id or "").strip()
        rows = _fetch_all(
            self.engine,
            """
            SELECT event_id, extraction_id, workspace_id, upload_id, event_type,
                   from_state, to_state, reason_code, created_at, actor_user_ref,
                   event_metadata
            FROM file_extraction_events
            WHERE extraction_id = :extraction_id
            ORDER BY created_at ASC, event_id ASC
            """,
            {"extraction_id": normalized},
        )
        normalized_rows = []
        for row in rows:
            row["event_metadata"] = _decode_json(row.get("event_metadata"), default={})
            normalized_rows.append(_event_from_row(row))
        return tuple(normalized_rows)
