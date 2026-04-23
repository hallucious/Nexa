from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.provider_health_models import (
    ProductProviderBindingHealthView,
    ProductProviderHealthFindingView,
    ProductProviderHealthLinks,
    ProductProviderHealthRejectedResponse,
    ProductWorkspaceProviderHealthResponse,
    ProductProviderHealthDetailResponse,
    ProviderHealthDetailOutcome,
    ProviderHealthListOutcome,
)

from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace

SecretMetadataReader = Callable[[str], Optional[Mapping[str, Any]]]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise TypeError("Expected mapping row")


def _catalog_by_key(rows: Sequence[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for raw_row in rows or ():
        row = _as_mapping(raw_row)
        provider_key = str(row.get("provider_key") or "").strip().lower()
        if provider_key:
            result[provider_key] = row
    return result


def _binding_by_key(workspace_id: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for raw_row in rows:
        row = _as_mapping(raw_row)
        if str(row.get("workspace_id") or "").strip() != workspace_id:
            continue
        provider_key = str(row.get("provider_key") or "").strip().lower()
        if provider_key:
            result[provider_key] = row
    return result


def _infer_secret_authority(secret_ref: Optional[str], binding_row: Mapping[str, Any] | None) -> Optional[str]:
    explicit = str((binding_row or {}).get("secret_authority") or "").strip()
    if explicit:
        return explicit
    normalized = str(secret_ref or "").strip()
    if normalized.startswith("aws-secretsmanager://"):
        return "aws_secrets_manager"
    if normalized.startswith("secret://"):
        return "managed"
    return None


def _health_links(workspace_id: str, provider_key: str) -> ProductProviderHealthLinks:
    base = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"
    return ProductProviderHealthLinks(
        binding=base,
        upsert=base,
        catalog="/api/providers/catalog",
    )


class ProviderHealthService:
    @classmethod
    def _authorize(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> Optional[ProductProviderHealthRejectedResponse]:
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id=workspace_context.workspace_id if workspace_context is not None else None,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            provider_binding_rows=provider_binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated:
            return ProductProviderHealthRejectedResponse(
                failure_family="product_read_failure",
                reason_code="provider_health.authentication_required",
                message="Provider health requires an authenticated session.",
                workspace_id=workspace_context.workspace_id if workspace_context else None,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        if workspace_context is None:
            return ProductProviderHealthRejectedResponse(
                failure_family="workspace_not_found",
                reason_code="provider_health.workspace_not_found",
                message="Requested workspace was not found.",
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="manage",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if decision.allowed:
            return None
        return ProductProviderHealthRejectedResponse(
            failure_family="product_read_failure",
            reason_code=f"provider_health.{decision.reason_code}",
            message="Current user is not allowed to read provider health for this workspace.",
            workspace_id=workspace_context.workspace_id,
            workspace_title=workspace_title,
            provider_continuity=provider_continuity,
            activity_continuity=activity_continuity,
        )

    @classmethod
    def _build_view(
        cls,
        *,
        workspace_id: str,
        provider_key: str,
        catalog_row: Optional[Mapping[str, Any]],
        binding_row: Optional[Mapping[str, Any]],
        secret_metadata_reader: Optional[SecretMetadataReader],
    ) -> ProductProviderBindingHealthView:
        display_name = str((catalog_row or {}).get("display_name") or (binding_row or {}).get("display_name") or provider_key).strip()
        provider_family = str((catalog_row or {}).get("provider_family") or (binding_row or {}).get("provider_family") or provider_key).strip()
        enabled = bool((binding_row or {}).get("enabled", True)) if binding_row is not None else False
        credential_source = str((binding_row or {}).get("credential_source") or "").strip() or None
        default_model_ref = str((binding_row or {}).get("default_model_ref") or "").strip() or None
        allowed_model_refs = tuple(str(item).strip() for item in ((binding_row or {}).get("allowed_model_refs") or ()) if str(item).strip())
        secret_ref = str((binding_row or {}).get("secret_ref") or "").strip() or None
        findings: list[ProductProviderHealthFindingView] = []
        secret_resolution_status = "not_checked"

        if catalog_row is None:
            findings.append(ProductProviderHealthFindingView(
                severity="blocked",
                reason_code="provider_health.provider_not_supported",
                message="Provider is not part of the managed provider catalog.",
                field_name="provider_key",
            ))
        if binding_row is None:
            findings.append(ProductProviderHealthFindingView(
                severity="blocked",
                reason_code="provider_health.binding_missing",
                message="Provider has no workspace binding yet.",
                field_name="binding",
            ))
            health_status = "missing"
        elif not enabled:
            findings.append(ProductProviderHealthFindingView(
                severity="info",
                reason_code="provider_health.binding_disabled",
                message="Provider binding exists but is currently disabled.",
                field_name="enabled",
            ))
            health_status = "disabled"
        else:
            if credential_source != "managed":
                findings.append(ProductProviderHealthFindingView(
                    severity="blocked",
                    reason_code="provider_health.credential_source_unsupported",
                    message="Provider binding uses an unsupported credential source.",
                    field_name="credential_source",
                ))
            if not secret_ref:
                findings.append(ProductProviderHealthFindingView(
                    severity="blocked",
                    reason_code="provider_health.secret_ref_missing",
                    message="Provider binding is missing a managed secret reference.",
                    field_name="secret_ref",
                ))
                secret_resolution_status = "missing"
            elif secret_metadata_reader is not None:
                try:
                    secret_metadata = secret_metadata_reader(secret_ref)
                except Exception:
                    secret_metadata = None
                    secret_resolution_status = "error"
                    findings.append(ProductProviderHealthFindingView(
                        severity="warning",
                        reason_code="provider_health.secret_metadata_read_failed",
                        message="Secret authority metadata could not be read for this binding.",
                        field_name="secret_ref",
                    ))
                else:
                    if secret_metadata is None:
                        secret_resolution_status = "missing"
                        findings.append(ProductProviderHealthFindingView(
                            severity="blocked",
                            reason_code="provider_health.secret_unresolved",
                            message="Managed secret reference could not be resolved.",
                            field_name="secret_ref",
                        ))
                    else:
                        secret_resolution_status = "resolved"
            if not default_model_ref and not allowed_model_refs:
                findings.append(ProductProviderHealthFindingView(
                    severity="warning",
                    reason_code="provider_health.model_not_selected",
                    message="No default or allowed model has been configured yet.",
                    field_name="default_model_ref",
                ))
            elif default_model_ref and allowed_model_refs and default_model_ref not in allowed_model_refs:
                findings.append(ProductProviderHealthFindingView(
                    severity="blocked",
                    reason_code="provider_health.default_model_not_allowed",
                    message="Default model is not included in the allowed model set.",
                    field_name="default_model_ref",
                ))
            if any(item.severity == "blocked" for item in findings):
                health_status = "blocked"
            elif any(item.severity == "warning" for item in findings):
                health_status = "warning"
            else:
                health_status = "healthy"

        blocked_count = sum(1 for item in findings if item.severity == "blocked")
        warning_count = sum(1 for item in findings if item.severity == "warning")
        return ProductProviderBindingHealthView(
            workspace_id=workspace_id,
            provider_key=provider_key,
            provider_family=provider_family,
            display_name=display_name,
            health_status=health_status,
            binding_present=binding_row is not None,
            enabled=enabled,
            credential_source=credential_source,
            default_model_ref=default_model_ref,
            allowed_model_ref_count=len(allowed_model_refs),
            secret_ref_present=bool(secret_ref),
            secret_authority=_infer_secret_authority(secret_ref, binding_row),
            secret_resolution_status=secret_resolution_status,
            blocked_count=blocked_count,
            warning_count=warning_count,
            findings=tuple(findings),
            links=_health_links(workspace_id, provider_key),
        )

    @classmethod
    def list_workspace_provider_health(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> ProviderHealthListOutcome:
        rejected = cls._authorize(request_auth=request_auth, workspace_context=workspace_context, workspace_row=workspace_row, recent_run_rows=recent_run_rows, provider_binding_rows=binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, onboarding_rows=onboarding_rows)
        if rejected is not None:
            return ProviderHealthListOutcome(rejected=rejected)
        assert workspace_context is not None
        catalog = _catalog_by_key(provider_catalog_rows)
        bindings = _binding_by_key(workspace_context.workspace_id, binding_rows)
        provider_keys = sorted(set(catalog) | set(bindings))
        views = tuple(
            cls._build_view(
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
                catalog_row=catalog.get(provider_key),
                binding_row=bindings.get(provider_key),
                secret_metadata_reader=secret_metadata_reader,
            )
            for provider_key in provider_keys
        )
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
        return ProviderHealthListOutcome(
            response=ProductWorkspaceProviderHealthResponse(
                workspace_id=workspace_context.workspace_id,
                returned_count=len(views),
                providers=views,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def read_workspace_provider_health(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> ProviderHealthDetailOutcome:
        normalized_provider_key = str(provider_key or "").strip().lower()
        rejected = cls._authorize(request_auth=request_auth, workspace_context=workspace_context, workspace_row=workspace_row, recent_run_rows=recent_run_rows, provider_binding_rows=binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, onboarding_rows=onboarding_rows)
        if rejected is not None:
            return ProviderHealthDetailOutcome(rejected=rejected)
        assert workspace_context is not None
        catalog = _catalog_by_key(provider_catalog_rows)
        bindings = _binding_by_key(workspace_context.workspace_id, binding_rows)
        if normalized_provider_key not in catalog and normalized_provider_key not in bindings:
            return ProviderHealthDetailOutcome(
                rejected=ProductProviderHealthRejectedResponse(
                    failure_family="provider_not_supported",
                    reason_code="provider_health.provider_not_supported",
                    message="Requested provider is not known for this workspace.",
                    workspace_id=workspace_context.workspace_id,
                    provider_key=normalized_provider_key or None,
                    workspace_title=str((workspace_row or {}).get("title") or "").strip() or None,
                    provider_continuity=_provider_continuity_summary_for_workspace(
                        workspace_context.workspace_id,
                        provider_binding_rows=binding_rows,
                        managed_secret_rows=managed_secret_rows,
                        provider_probe_rows=provider_probe_rows,
                    ),
                    activity_continuity=_activity_continuity_summary_for_workspace(
                        workspace_context.workspace_id,
                        user_id=request_auth.requested_by_user_ref or "",
                        recent_run_rows=recent_run_rows,
                        provider_binding_rows=binding_rows,
                        managed_secret_rows=managed_secret_rows,
                        provider_probe_rows=provider_probe_rows,
                        onboarding_rows=onboarding_rows,
                    ),
                )
            )
        health_view = cls._build_view(
            workspace_id=workspace_context.workspace_id,
            provider_key=normalized_provider_key,
            catalog_row=catalog.get(normalized_provider_key),
            binding_row=bindings.get(normalized_provider_key),
            secret_metadata_reader=secret_metadata_reader,
        )
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
        return ProviderHealthDetailOutcome(
            response=ProductProviderHealthDetailResponse(
                workspace_id=workspace_context.workspace_id,
                workspace_title=workspace_title,
                provider_key=normalized_provider_key,
                health=health_view,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )
