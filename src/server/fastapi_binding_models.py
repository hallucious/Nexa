from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Sequence

if TYPE_CHECKING:
    from fastapi import Request
else:
    Request = Any

from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.boundary_models import EngineResultEnvelope, EngineRunLaunchResponse, EngineRunStatusSnapshot
from src.server.run_admission_models import ExecutionTargetCatalogEntry, ProductAdmissionPolicy
from src.server.aws_secrets_manager_models import AwsSecretsManagerBindingConfig


@dataclass(frozen=True)
class FastApiBindingConfig:
    title: str = "Nexa Server API"
    version: str = "0.1.0"
    session_claims_header: str = "x-nexa-session-claims"

    def __post_init__(self) -> None:
        if not str(self.title).strip():
            raise ValueError("FastApiBindingConfig.title must be non-empty")
        if not str(self.version).strip():
            raise ValueError("FastApiBindingConfig.version must be non-empty")
        if not str(self.session_claims_header).strip():
            raise ValueError("FastApiBindingConfig.session_claims_header must be non-empty")


SessionClaimsResolver = Callable[[Request], Optional[Mapping[str, Any]]]
WorkspaceContextProvider = Callable[[str], Optional[WorkspaceAuthorizationContext]]
RunContextProvider = Callable[[str], Optional[RunAuthorizationContext]]
TargetCatalogProvider = Callable[[str], Mapping[str, ExecutionTargetCatalogEntry]]
RunRecordProvider = Callable[[str], Optional[Mapping[str, Any]]]
ResultRowProvider = Callable[[str], Optional[Mapping[str, Any]]]
ArtifactRowsProvider = Callable[[str], Sequence[Mapping[str, Any]]]
WorkspaceRunRowsProvider = Callable[[str], Sequence[Mapping[str, Any]]]
WorkspaceResultRowsProvider = Callable[[str], Mapping[str, Mapping[str, Any]]]
ArtifactRowProvider = Callable[[str], Optional[Mapping[str, Any]]]
TraceRowsProvider = Callable[[str], Sequence[Mapping[str, Any]]]
WorkspaceRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
WorkspaceMembershipRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
RecentRunRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
OnboardingRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
FeedbackRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
ProviderCatalogRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
WorkspaceProviderBindingRowsProvider = Callable[[str], Sequence[Mapping[str, Any]]]
WorkspaceProviderBindingRowProvider = Callable[[str, str], Optional[Mapping[str, Any]]]
WorkspaceProviderProbeRowsProvider = Callable[[str], Sequence[Mapping[str, Any]]]
RecentProviderProbeRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
RecentProviderBindingRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
RecentManagedSecretRowsProvider = Callable[[], Sequence[Mapping[str, Any]]]
ProviderProbeHistoryWriter = Callable[[Mapping[str, Any]], Any]
ProviderBindingWriter = Callable[[Mapping[str, Any]], Any]
RunRecordWriter = Callable[[Mapping[str, Any]], Any]
WorkspaceRegistryWriter = Callable[[Mapping[str, Any], Mapping[str, Any]], Any]
OnboardingStateWriter = Callable[[Mapping[str, Any]], Any]
FeedbackWriter = Callable[[Mapping[str, Any]], Any]
ManagedSecretWriter = Callable[[str, str, str, Mapping[str, Any]], Mapping[str, Any]]
ManagedSecretMetadataReader = Callable[[str], Optional[Mapping[str, Any]]]
AwsSecretsManagerClientProvider = Callable[[], Any]
WorkspaceRowProvider = Callable[[str], Optional[Mapping[str, Any]]]
WorkspaceArtifactSourceProvider = Callable[[str], Any | None]
WorkspaceArtifactSourceWriter = Callable[[str, Any], Any]
EngineStatusProvider = Callable[[str], Optional[EngineRunStatusSnapshot]]
EngineResultProvider = Callable[[str], Optional[EngineResultEnvelope]]
EngineLaunchDecider = Callable[..., EngineRunLaunchResponse]
IdentifierFactory = Callable[[], str]
NowIsoProvider = Callable[[], str]


def _none_workspace(_: str) -> Optional[WorkspaceAuthorizationContext]:
    return None


def _none_run(_: str) -> Optional[RunAuthorizationContext]:
    return None


def _empty_catalog(_: str) -> Mapping[str, ExecutionTargetCatalogEntry]:
    return {}


def _none_row(_: str) -> Optional[Mapping[str, Any]]:
    return None


def _empty_rows(_: str) -> Sequence[Mapping[str, Any]]:
    return ()


def _empty_noarg_rows() -> Sequence[Mapping[str, Any]]:
    return ()


def _empty_result_rows(_: str) -> Mapping[str, Mapping[str, Any]]:
    return {}


def _empty_provider_binding_rows(_: str) -> Sequence[Mapping[str, Any]]:
    return ()


def _none_provider_binding_row(_: str, __: str) -> Optional[Mapping[str, Any]]:
    return None


def _default_secret_writer(workspace_id: str, provider_key: str, secret_value: str, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "secret_ref": f"secret://{workspace_id}/{provider_key}",
        "secret_version_ref": "v1",
        "last_rotated_at": str(metadata.get("now_iso") or metadata.get("updated_at") or "").strip() or None,
    }


def _noop_probe_history_writer(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return dict(row)


def _noop_provider_binding_writer(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return dict(row)


def _noop_workspace_registry_writer(workspace_row: Mapping[str, Any], membership_row: Mapping[str, Any]) -> Mapping[str, Any]:
    return {"workspace": dict(workspace_row), "membership": dict(membership_row)}


def _noop_onboarding_state_writer(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return dict(row)


def _noop_feedback_writer(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return dict(row)


def _noop_run_record_writer(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return dict(row)


def _none_workspace_row(_: str) -> Optional[Mapping[str, Any]]:
    return None


def _none_workspace_artifact(_: str) -> Any | None:
    return None


def _noop_workspace_artifact_writer(_: str, artifact_source: Any) -> Any:
    return artifact_source


def _none_status(_: str) -> Optional[EngineRunStatusSnapshot]:
    return None


def _none_result(_: str) -> Optional[EngineResultEnvelope]:
    return None


@dataclass(frozen=True)
class FastApiRouteDependencies:
    workspace_context_provider: WorkspaceContextProvider = _none_workspace
    run_context_provider: RunContextProvider = _none_run
    target_catalog_provider: TargetCatalogProvider = _empty_catalog
    run_record_provider: RunRecordProvider = _none_row
    result_row_provider: ResultRowProvider = _none_row
    artifact_rows_provider: ArtifactRowsProvider = _empty_rows
    workspace_run_rows_provider: WorkspaceRunRowsProvider = _empty_rows
    workspace_result_rows_provider: WorkspaceResultRowsProvider = _empty_result_rows
    artifact_row_provider: ArtifactRowProvider = _none_row
    trace_rows_provider: TraceRowsProvider = _empty_rows
    workspace_rows_provider: WorkspaceRowsProvider = _empty_noarg_rows
    workspace_membership_rows_provider: WorkspaceMembershipRowsProvider = _empty_noarg_rows
    recent_run_rows_provider: RecentRunRowsProvider = _empty_noarg_rows
    onboarding_rows_provider: OnboardingRowsProvider = _empty_noarg_rows
    feedback_rows_provider: FeedbackRowsProvider = _empty_noarg_rows
    provider_catalog_rows_provider: ProviderCatalogRowsProvider = _empty_noarg_rows
    workspace_provider_binding_rows_provider: WorkspaceProviderBindingRowsProvider = _empty_provider_binding_rows
    workspace_provider_binding_row_provider: WorkspaceProviderBindingRowProvider = _none_provider_binding_row
    workspace_provider_probe_rows_provider: WorkspaceProviderProbeRowsProvider = _empty_provider_binding_rows
    recent_provider_probe_rows_provider: RecentProviderProbeRowsProvider = _empty_noarg_rows
    recent_provider_binding_rows_provider: RecentProviderBindingRowsProvider = _empty_noarg_rows
    recent_managed_secret_rows_provider: RecentManagedSecretRowsProvider = _empty_noarg_rows
    provider_binding_writer: ProviderBindingWriter = _noop_provider_binding_writer
    workspace_registry_writer: WorkspaceRegistryWriter = _noop_workspace_registry_writer
    onboarding_state_writer: OnboardingStateWriter = _noop_onboarding_state_writer
    feedback_writer: FeedbackWriter = _noop_feedback_writer
    run_record_writer: RunRecordWriter = _noop_run_record_writer
    provider_probe_history_writer: ProviderProbeHistoryWriter = _noop_probe_history_writer
    managed_secret_writer: ManagedSecretWriter = _default_secret_writer
    managed_secret_metadata_reader: Optional[ManagedSecretMetadataReader] = None
    aws_secrets_manager_client_provider: Optional[AwsSecretsManagerClientProvider] = None
    aws_secrets_manager_config: Optional[AwsSecretsManagerBindingConfig] = None
    provider_probe_runner: Optional[Callable[..., Any]] = None
    workspace_row_provider: WorkspaceRowProvider = _none_workspace_row
    workspace_artifact_source_provider: WorkspaceArtifactSourceProvider = _none_workspace_artifact
    workspace_artifact_source_writer: WorkspaceArtifactSourceWriter = _noop_workspace_artifact_writer
    engine_status_provider: EngineStatusProvider = _none_status
    engine_result_provider: EngineResultProvider = _none_result
    admission_policy: ProductAdmissionPolicy = field(default_factory=ProductAdmissionPolicy)
    engine_launch_decider: Optional[EngineLaunchDecider] = None
    run_id_factory: Optional[IdentifierFactory] = None
    run_request_id_factory: Optional[IdentifierFactory] = None
    workspace_id_factory: Optional[IdentifierFactory] = None
    membership_id_factory: Optional[IdentifierFactory] = None
    binding_id_factory: Optional[IdentifierFactory] = None
    probe_event_id_factory: Optional[IdentifierFactory] = None
    onboarding_state_id_factory: Optional[IdentifierFactory] = None
    feedback_id_factory: Optional[IdentifierFactory] = None
    now_iso_provider: Optional[NowIsoProvider] = None
    session_claims_resolver: Optional[SessionClaimsResolver] = None
