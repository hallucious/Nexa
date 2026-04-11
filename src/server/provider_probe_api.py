from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.provider_probe_models import (
    ProductProviderProbeFindingView,
    ProductProviderProbeLinks,
    ProductProviderProbeRejectedResponse,
    ProductProviderProbeRequest,
    ProductProviderProbeResponse,
    ProviderConnectivityState,
    ProviderProbeExecutionInput,
    ProviderProbeExecutionResult,
    ProviderProbeOutcome,
)

SecretMetadataReader = Callable[[str], Optional[Mapping[str, Any]]]
ProviderProbeRunner = Callable[[ProviderProbeExecutionInput], ProviderProbeExecutionResult | Mapping[str, Any]]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError("Expected mapping-like value")


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


def _probe_links(workspace_id: str, provider_key: str) -> ProductProviderProbeLinks:
    base = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"
    return ProductProviderProbeLinks(
        binding=base,
        health=f"{base}/health",
        catalog="/api/providers/catalog",
    )


def _normalize_execution_result(value: ProviderProbeExecutionResult | Mapping[str, Any]) -> ProviderProbeExecutionResult:
    if isinstance(value, ProviderProbeExecutionResult):
        return value
    row = _as_mapping(value)
    findings: list[ProductProviderProbeFindingView] = []
    for raw_item in row.get("findings") or ():
        if isinstance(raw_item, ProductProviderProbeFindingView):
            findings.append(raw_item)
        else:
            mapping = _as_mapping(raw_item)
            findings.append(ProductProviderProbeFindingView(
                severity=str(mapping.get("severity") or "info"),
                reason_code=str(mapping.get("reason_code") or "provider_probe.finding"),
                message=str(mapping.get("message") or "Provider probe finding."),
                field_name=str(mapping.get("field_name") or "").strip() or None,
            ))
    return ProviderProbeExecutionResult(
        probe_status=str(row.get("probe_status") or "failed"),
        connectivity_state=str(row.get("connectivity_state") or "unknown"),
        message=str(row.get("message") or "").strip() or None,
        reason_code=str(row.get("reason_code") or "").strip() or None,
        effective_model_ref=str(row.get("effective_model_ref") or "").strip() or None,
        round_trip_latency_ms=int(row.get("round_trip_latency_ms")) if row.get("round_trip_latency_ms") is not None else None,
        provider_account_ref=str(row.get("provider_account_ref") or "").strip() or None,
        findings=tuple(findings),
    )


class ProviderProbeService:
    @classmethod
    def _authorize(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
    ) -> Optional[ProductProviderProbeRejectedResponse]:
        if not request_auth.is_authenticated:
            return ProductProviderProbeRejectedResponse(
                failure_family="product_probe_failure",
                reason_code="provider_probe.authentication_required",
                message="Provider probe requires an authenticated session.",
                workspace_id=workspace_context.workspace_id if workspace_context else None,
            )
        if workspace_context is None:
            return ProductProviderProbeRejectedResponse(
                failure_family="workspace_not_found",
                reason_code="provider_probe.workspace_not_found",
                message="Requested workspace was not found.",
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
        return ProductProviderProbeRejectedResponse(
            failure_family="product_probe_failure",
            reason_code=f"provider_probe.{decision.reason_code}",
            message="Current user is not allowed to probe provider connectivity for this workspace.",
            workspace_id=workspace_context.workspace_id,
        )

    @classmethod
    def probe_workspace_provider(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        request: ProductProviderProbeRequest,
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        probe_runner: Optional[ProviderProbeRunner] = None,
        now_iso: Optional[str] = None,
    ) -> ProviderProbeOutcome:
        provider_key = str(provider_key or "").strip().lower()
        rejected = cls._authorize(request_auth=request_auth, workspace_context=workspace_context)
        if rejected is not None:
            rejected = ProductProviderProbeRejectedResponse(
                failure_family=rejected.failure_family,
                reason_code=rejected.reason_code,
                message=rejected.message,
                workspace_id=rejected.workspace_id,
                provider_key=provider_key or None,
            )
            return ProviderProbeOutcome(rejected=rejected)
        assert workspace_context is not None
        catalog = _catalog_by_key(provider_catalog_rows)
        catalog_row = catalog.get(provider_key)
        if catalog_row is None:
            return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                failure_family="provider_not_supported",
                reason_code="provider_probe.provider_not_supported",
                message="Provider is not part of the managed provider catalog.",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
            ))
        binding_row = _binding_by_key(workspace_context.workspace_id, binding_rows).get(provider_key)
        if binding_row is None:
            return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                failure_family="product_probe_failure",
                reason_code="provider_probe.binding_missing",
                message="Provider binding must exist before connectivity can be probed.",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
            ))
        if not bool(binding_row.get("enabled", True)):
            return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                failure_family="product_probe_failure",
                reason_code="provider_probe.binding_disabled",
                message="Provider binding is disabled and cannot be probed.",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
            ))
        secret_ref = str(binding_row.get("secret_ref") or "").strip()
        if not secret_ref:
            return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                failure_family="product_probe_failure",
                reason_code="provider_probe.secret_ref_missing",
                message="Provider binding does not have a managed secret reference.",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
            ))

        secret_resolution_status = "not_checked"
        if secret_metadata_reader is not None:
            try:
                secret_metadata = secret_metadata_reader(secret_ref)
            except Exception:
                secret_metadata = None
                secret_resolution_status = "error"
            else:
                secret_resolution_status = "resolved" if secret_metadata is not None else "missing"
            if secret_resolution_status == "missing":
                return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                    failure_family="product_probe_failure",
                    reason_code="provider_probe.secret_unresolved",
                    message="Managed secret reference could not be resolved for this provider binding.",
                    workspace_id=workspace_context.workspace_id,
                    provider_key=provider_key,
                ))
        if probe_runner is None:
            return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                failure_family="product_probe_failure",
                reason_code="provider_probe.runner_missing",
                message="Provider connectivity probe is not configured for this server.",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
            ))

        default_model_ref = str(binding_row.get("default_model_ref") or "").strip() or None
        allowed_model_refs = tuple(
            str(item).strip() for item in (binding_row.get("allowed_model_refs") or ()) if str(item).strip()
        )
        requested_model_ref = str(request.model_ref or "").strip() or None
        if requested_model_ref and allowed_model_refs and requested_model_ref not in allowed_model_refs:
            return ProviderProbeOutcome(rejected=ProductProviderProbeRejectedResponse(
                failure_family="product_probe_failure",
                reason_code="provider_probe.model_not_allowed",
                message="Requested probe model is not part of the allowed model set.",
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
            ))

        probe_input = ProviderProbeExecutionInput(
            workspace_id=workspace_context.workspace_id,
            provider_key=provider_key,
            provider_family=str(catalog_row.get("provider_family") or provider_key).strip(),
            display_name=str(catalog_row.get("display_name") or provider_key).strip(),
            secret_ref=secret_ref,
            secret_authority=_infer_secret_authority(secret_ref, binding_row),
            default_model_ref=default_model_ref,
            allowed_model_refs=allowed_model_refs,
            requested_model_ref=requested_model_ref,
            probe_message=str(request.probe_message or "").strip() or None,
            timeout_ms=request.timeout_ms,
            now_iso=str(now_iso or "").strip() or None,
        )
        execution = _normalize_execution_result(probe_runner(probe_input))
        response = ProductProviderProbeResponse(
            workspace_id=workspace_context.workspace_id,
            provider_key=provider_key,
            provider_family=probe_input.provider_family,
            display_name=probe_input.display_name,
            probe_status=execution.probe_status,
            connectivity_state=execution.connectivity_state,
            credential_source=str(binding_row.get("credential_source") or "").strip() or None,
            secret_authority=probe_input.secret_authority,
            secret_resolution_status=secret_resolution_status,
            effective_model_ref=execution.effective_model_ref or requested_model_ref or default_model_ref,
            provider_account_ref=execution.provider_account_ref,
            round_trip_latency_ms=execution.round_trip_latency_ms,
            message=execution.message,
            findings=execution.findings,
            links=_probe_links(workspace_context.workspace_id, provider_key),
        )
        return ProviderProbeOutcome(response=response)
