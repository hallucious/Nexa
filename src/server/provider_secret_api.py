from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.provider_secret_models import (
    ProviderBindingListOutcome,
    ProviderBindingWriteOutcome,
    ProviderCatalogReadOutcome,
    ProductProviderBindingLinks,
    ProductProviderBindingWriteAcceptedResponse,
    ProductProviderBindingWriteRequest,
    ProductProviderCatalogEntryView,
    ProductProviderCatalogResponse,
    ProductProviderSecretReadRejectedResponse,
    ProductProviderSecretWriteRejectedResponse,
    ProductWorkspaceProviderBindingView,
    ProductWorkspaceProviderBindingsResponse,
)

from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace, _continuity_projection_for_workspace_ids, _visible_workspace_ids_for_user

SecretWriter = Callable[[str, str, str, Mapping[str, Any]], Mapping[str, Any]]

_DEFAULT_PROVIDER_CATALOG_ROWS: tuple[dict[str, Any], ...] = (
    {
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "OPENAI_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
    },
    {
        "provider_key": "anthropic",
        "provider_family": "anthropic",
        "display_name": "Anthropic Claude",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "ANTHROPIC_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/anthropic",
    },
    {
        "provider_key": "gemini",
        "provider_family": "google",
        "display_name": "Google Gemini",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "GEMINI_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/gemini",
    },
    {
        "provider_key": "perplexity",
        "provider_family": "perplexity",
        "display_name": "Perplexity",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "PPLX_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/perplexity",
    },
    {
        "provider_key": "codex",
        "provider_family": "openai",
        "display_name": "OpenAI Codex",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "OPENAI_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/codex",
    },
)


def default_provider_catalog_rows() -> tuple[dict[str, Any], ...]:
    return tuple(dict(row) for row in _DEFAULT_PROVIDER_CATALOG_ROWS)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError("Provider catalog and binding rows must be mapping-like")


def _provider_catalog_rows(catalog_rows: Sequence[Mapping[str, Any]] | None = None) -> tuple[Mapping[str, Any], ...]:
    rows = tuple(catalog_rows or default_provider_catalog_rows())
    return tuple(_as_mapping(row) for row in rows)


def _catalog_by_key(catalog_rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Mapping[str, Any]]:
    resolved: dict[str, Mapping[str, Any]] = {}
    for row in _provider_catalog_rows(catalog_rows):
        provider_key = str(row.get("provider_key") or "").strip().lower()
        if provider_key:
            resolved[provider_key] = row
    return resolved


def _binding_links(workspace_id: str, provider_key: str) -> ProductProviderBindingLinks:
    return ProductProviderBindingLinks(
        workspace=f"/api/workspaces/{workspace_id}",
        upsert=f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}",
        catalog="/api/providers/catalog",
    )


def _binding_status(*, enabled: bool, secret_ref: Optional[str]) -> str:
    if not enabled:
        return "disabled"
    if not str(secret_ref or "").strip():
        return "missing_secret"
    return "configured"


class ProviderSecretIntegrationService:
    @classmethod
    def list_provider_catalog(
        cls,
        *,
        request_auth: RequestAuthContext,
        provider_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> ProviderCatalogReadOutcome:
        if not request_auth.is_authenticated:
            return ProviderCatalogReadOutcome(
                rejected=ProductProviderSecretReadRejectedResponse(
                    failure_family="product_read_failure",
                    reason_code="provider_catalog.authentication_required",
                    message="Provider catalog requires an authenticated session.",
                )
            )
        providers = tuple(
            ProductProviderCatalogEntryView(
                provider_key=str(row.get("provider_key") or "").strip(),
                provider_family=str(row.get("provider_family") or "").strip(),
                display_name=str(row.get("display_name") or "").strip(),
                managed_supported=bool(row.get("managed_supported", True)),
                recommended_scope=str(row.get("recommended_scope") or "workspace").strip() or "workspace",
                local_env_var_hint=str(row.get("local_env_var_hint") or "").strip() or None,
                default_secret_name_template=str(row.get("default_secret_name_template") or "").strip() or None,
            )
            for row in _provider_catalog_rows(provider_catalog_rows)
        )
        visible_workspace_ids = _visible_workspace_ids_for_user(
            request_auth.requested_by_user_ref or '',
            workspace_rows,
            membership_rows,
        )
        provider_continuity, activity_continuity = _continuity_projection_for_workspace_ids(
            visible_workspace_ids,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return ProviderCatalogReadOutcome(
            response=ProductProviderCatalogResponse(
                returned_count=len(providers),
                providers=providers,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def list_workspace_provider_bindings(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> ProviderBindingListOutcome:
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id=workspace_context.workspace_id if workspace_context is not None else None,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            provider_binding_rows=binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated:
            return ProviderBindingListOutcome(
                rejected=ProductProviderSecretReadRejectedResponse(
                    failure_family="product_read_failure",
                    reason_code="provider_bindings.authentication_required",
                    message="Provider bindings require an authenticated session.",
                    workspace_id=workspace_context.workspace_id if workspace_context else None,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        if workspace_context is None:
            return ProviderBindingListOutcome(
                rejected=ProductProviderSecretReadRejectedResponse(
                    failure_family="workspace_not_found",
                    reason_code="provider_bindings.workspace_not_found",
                    message="Requested workspace was not found.",
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="manage",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return ProviderBindingListOutcome(
                rejected=ProductProviderSecretReadRejectedResponse(
                    failure_family="product_read_failure",
                    reason_code=f"provider_bindings.{decision.reason_code}",
                    message="Current user is not allowed to read workspace provider bindings.",
                    workspace_id=workspace_context.workspace_id,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        catalog = _catalog_by_key(provider_catalog_rows)
        views: list[ProductWorkspaceProviderBindingView] = []
        for raw_row in binding_rows:
            row = _as_mapping(raw_row)
            if str(row.get("workspace_id") or "").strip() != workspace_context.workspace_id:
                continue
            provider_key = str(row.get("provider_key") or "").strip().lower()
            catalog_row = catalog.get(provider_key, {})
            secret_ref = str(row.get("secret_ref") or "").strip() or None
            view = ProductWorkspaceProviderBindingView(
                binding_id=str(row.get("binding_id") or "").strip() or f"binding:{workspace_context.workspace_id}:{provider_key}",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
                provider_family=str(row.get("provider_family") or catalog_row.get("provider_family") or provider_key).strip(),
                display_name=str(row.get("display_name") or catalog_row.get("display_name") or provider_key).strip(),
                status=_binding_status(enabled=bool(row.get("enabled", True)), secret_ref=secret_ref),
                enabled=bool(row.get("enabled", True)),
                credential_source=str(row.get("credential_source") or "managed").strip() or "managed",
                secret_ref=secret_ref,
                secret_version_ref=str(row.get("secret_version_ref") or "").strip() or None,
                default_model_ref=str(row.get("default_model_ref") or "").strip() or None,
                allowed_model_refs=tuple(str(item).strip() for item in row.get("allowed_model_refs") or () if str(item).strip()),
                created_at=str(row.get("created_at") or "").strip() or None,
                updated_at=str(row.get("updated_at") or "").strip() or None,
                last_rotated_at=str(row.get("last_rotated_at") or "").strip() or None,
                updated_by_user_id=str(row.get("updated_by_user_id") or "").strip() or None,
                links=_binding_links(workspace_context.workspace_id, provider_key),
            )
            views.append(view)
        views.sort(key=lambda item: ((item.updated_at or ""), item.provider_key), reverse=True)
        workspace_title = str((workspace_row or {}).get("title") or "").strip() or None
        provider_continuity = _provider_continuity_summary_for_workspace(
            workspace_context.workspace_id,
            provider_binding_rows=binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        activity_continuity = _activity_continuity_summary_for_workspace(
            workspace_context.workspace_id,
            user_id=request_auth.requested_by_user_ref or "",
            recent_run_rows=recent_run_rows,
            provider_binding_rows=binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return ProviderBindingListOutcome(
            response=ProductWorkspaceProviderBindingsResponse(
                workspace_id=workspace_context.workspace_id,
                returned_count=len(views),
                bindings=tuple(views),
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def upsert_workspace_provider_binding(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        request: ProductProviderBindingWriteRequest,
        existing_binding_row: Optional[Mapping[str, Any]],
        provider_catalog_rows: Sequence[Mapping[str, Any]] | None,
        binding_id_factory: Callable[[], str],
        secret_writer: SecretWriter,
        now_iso: str,
        workspace_row: Optional[Mapping[str, Any]] = None,
        binding_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> ProviderBindingWriteOutcome:
        provider_key = str(provider_key or "").strip().lower()
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id=workspace_context.workspace_id if workspace_context is not None else None,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            provider_binding_rows=binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated:
            return ProviderBindingWriteOutcome(
                rejected=ProductProviderSecretWriteRejectedResponse(
                    failure_family="product_write_failure",
                    reason_code="provider_binding_write.authentication_required",
                    message="Provider binding write requires an authenticated session.",
                    workspace_id=workspace_context.workspace_id if workspace_context else None,
                    provider_key=provider_key or None,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        if workspace_context is None:
            return ProviderBindingWriteOutcome(
                rejected=ProductProviderSecretWriteRejectedResponse(
                    failure_family="workspace_not_found",
                    reason_code="provider_binding_write.workspace_not_found",
                    message="Requested workspace was not found.",
                    provider_key=provider_key or None,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="manage",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return ProviderBindingWriteOutcome(
                rejected=ProductProviderSecretWriteRejectedResponse(
                    failure_family="product_write_failure",
                    reason_code=f"provider_binding_write.{decision.reason_code}",
                    message="Current user is not allowed to manage workspace provider bindings.",
                    workspace_id=workspace_context.workspace_id,
                    provider_key=provider_key or None,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        catalog = _catalog_by_key(provider_catalog_rows)
        catalog_row = catalog.get(provider_key)
        if catalog_row is None or not bool(catalog_row.get("managed_supported", True)):
            return ProviderBindingWriteOutcome(
                rejected=ProductProviderSecretWriteRejectedResponse(
                    failure_family="provider_not_supported",
                    reason_code="provider_binding_write.provider_not_supported",
                    message="Requested provider is not supported for managed server-side credentials.",
                    workspace_id=workspace_context.workspace_id,
                    provider_key=provider_key or None,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        existing = _as_mapping(existing_binding_row) if existing_binding_row is not None else {}
        secret_ref = str(existing.get("secret_ref") or "").strip() or None
        secret_version_ref = str(existing.get("secret_version_ref") or "").strip() or None
        last_rotated_at = str(existing.get("last_rotated_at") or "").strip() or None
        secret_rotated = False
        secret_receipt = None
        if request.secret_value is not None:
            secret_receipt = secret_writer(
                workspace_context.workspace_id,
                provider_key,
                str(request.secret_value),
                {
                    "workspace_id": workspace_context.workspace_id,
                    "provider_key": provider_key,
                    "requested_by_user_id": request_auth.requested_by_user_ref,
                },
            )
            secret_ref = str(secret_receipt.get("secret_ref") or "").strip() or None
            secret_version_ref = str(secret_receipt.get("secret_version_ref") or "").strip() or None
            last_rotated_at = str(secret_receipt.get("last_rotated_at") or now_iso).strip() or now_iso
            secret_rotated = True
        elif request.secret_ref_hint is not None:
            secret_ref = str(request.secret_ref_hint).strip()
            secret_version_ref = None
            last_rotated_at = now_iso
            secret_rotated = True

        if request.enabled and not secret_ref:
            return ProviderBindingWriteOutcome(
                rejected=ProductProviderSecretWriteRejectedResponse(
                    failure_family="product_write_failure",
                    reason_code="provider_binding_write.secret_required",
                    message="Enabled managed provider bindings require a secret reference.",
                    workspace_id=workspace_context.workspace_id,
                    provider_key=provider_key,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        binding_id = str(existing.get("binding_id") or "").strip() or binding_id_factory()
        display_name = str(request.display_name or existing.get("display_name") or catalog_row.get("display_name") or provider_key).strip()
        provider_family = str(existing.get("provider_family") or catalog_row.get("provider_family") or provider_key).strip()
        allowed_model_refs = request.allowed_model_refs or tuple(str(item).strip() for item in existing.get("allowed_model_refs") or () if str(item).strip())
        created_at = str(existing.get("created_at") or "").strip() or now_iso
        binding_row = {
            "binding_id": binding_id,
            "workspace_id": workspace_context.workspace_id,
            "provider_key": provider_key,
            "provider_family": provider_family,
            "display_name": display_name,
            "credential_source": request.credential_source,
            "secret_ref": secret_ref,
            "secret_version_ref": secret_version_ref,
            "enabled": bool(request.enabled),
            "default_model_ref": request.default_model_ref,
            "allowed_model_refs": tuple(allowed_model_refs),
            "notes": request.notes,
            "created_by_user_id": str(existing.get("created_by_user_id") or request_auth.requested_by_user_ref or "").strip() or None,
            "updated_by_user_id": request_auth.requested_by_user_ref,
            "created_at": created_at,
            "updated_at": now_iso,
            "last_rotated_at": last_rotated_at,
        }
        binding_view = ProductWorkspaceProviderBindingView(
            binding_id=binding_id,
            workspace_id=workspace_context.workspace_id,
            provider_key=provider_key,
            provider_family=provider_family,
            display_name=display_name,
            status=_binding_status(enabled=bool(request.enabled), secret_ref=secret_ref),
            enabled=bool(request.enabled),
            credential_source=request.credential_source,
            secret_ref=secret_ref,
            secret_version_ref=secret_version_ref,
            default_model_ref=request.default_model_ref,
            allowed_model_refs=tuple(allowed_model_refs),
            created_at=created_at,
            updated_at=now_iso,
            last_rotated_at=last_rotated_at,
            updated_by_user_id=request_auth.requested_by_user_ref,
            links=_binding_links(workspace_context.workspace_id, provider_key),
        )
        effective_binding_rows = [
            _as_mapping(row) for row in binding_rows
            if str(_as_mapping(row).get("provider_key") or "").strip().lower() != provider_key
            or str(_as_mapping(row).get("workspace_id") or "").strip() != workspace_context.workspace_id
        ]
        effective_binding_rows.append(binding_row)
        effective_secret_rows = [dict(_as_mapping(row)) for row in managed_secret_rows]
        if secret_receipt is not None or secret_rotated:
            effective_secret_rows = [
                row for row in effective_secret_rows
                if not (
                    str(row.get("workspace_id") or "").strip() == workspace_context.workspace_id
                    and str(row.get("provider_key") or "").strip().lower() == provider_key
                )
            ]
            if secret_ref:
                effective_secret_rows.append({
                    "workspace_id": workspace_context.workspace_id,
                    "provider_key": provider_key,
                    "secret_ref": secret_ref,
                    "secret_version_ref": secret_version_ref,
                    "last_rotated_at": last_rotated_at or now_iso,
                })
        workspace_title = str((workspace_row or {}).get("title") or "").strip() or None
        provider_continuity = _provider_continuity_summary_for_workspace(
            workspace_context.workspace_id,
            provider_binding_rows=effective_binding_rows,
            managed_secret_rows=effective_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        activity_continuity = _activity_continuity_summary_for_workspace(
            workspace_context.workspace_id,
            user_id=request_auth.requested_by_user_ref or "",
            recent_run_rows=recent_run_rows,
            provider_binding_rows=effective_binding_rows,
            managed_secret_rows=effective_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return ProviderBindingWriteOutcome(
            accepted=ProductProviderBindingWriteAcceptedResponse(
                status="updated" if existing else "created",
                binding=binding_view,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                was_created=not bool(existing),
                secret_rotated=secret_rotated,
            ),
            created_or_updated_binding_row=binding_row,
        )
