from __future__ import annotations

"""Official public server/API SDK boundary for Nexa.

This module exposes the curated request/response models and binding helpers that
external integrations may depend on. Internal server services remain available
under ``src.server.*`` but are not part of this narrower public SDK surface.
"""

from src.server import (
    FastApiRouteBindings,
    FrameworkRouteBindings,
    RunHttpRouteSurface,
    create_fastapi_app,
)
from src.server.artifact_trace_read_models import (
    ProductArtifactDetailResponse,
    ProductRunArtifactsResponse,
    ProductRunTraceResponse,
)
from src.server.circuit_library_models import ProductCircuitLibraryResponse
from src.server.starter_template_models import (
    ProductStarterTemplateApplyAcceptedResponse,
    ProductStarterTemplateCatalogResponse,
    ProductStarterTemplateDetailResponse,
)
from src.server.public_nex_models import ProductPublicNexFormatResponse
from src.server.public_mcp_models import ProductPublicMcpHostBridgeResponse, ProductPublicMcpManifestResponse
from src.server.recent_activity_models import ProductHistorySummaryResponse, ProductRecentActivityResponse
from src.server.provider_health_models import (
    ProductProviderHealthDetailResponse,
    ProductWorkspaceProviderHealthResponse,
)
from src.server.provider_probe_history_models import ProductProviderProbeHistoryResponse
from src.server.provider_probe_models import (
    ProductProviderProbeRequest,
    ProductProviderProbeResponse,
)
from src.server.provider_secret_models import (
    ProductProviderBindingWriteAcceptedResponse,
    ProductProviderBindingWriteRequest,
    ProductProviderCatalogResponse,
    ProductWorkspaceProviderBindingsResponse,
)
from src.server.public_share_models import (
    ProductIssuerPublicShareActionReportEntryView,
    ProductIssuerPublicShareActionReportListResponse,
    ProductIssuerPublicShareActionReportSummaryResponse,
    ProductIssuerPublicShareActionReportSummaryView,
    ProductIssuerPublicShareBulkMutationResponse,
    ProductIssuerPublicShareListResponse,
    ProductIssuerPublicShareSummaryResponse,
    ProductPublicShareActionAvailabilityView,
    ProductPublicShareArtifactResponse,
    ProductPublicShareCapabilitySummaryView,
    ProductPublicShareCatalogResponse,
    ProductPublicShareCatalogSummaryResponse,
    ProductPublicShareIssuerCatalogResponse,
    ProductPublicShareIssuerCatalogSummaryResponse,
    ProductPublicShareCompareSummaryResponse,
    ProductPublicShareCheckoutAcceptedResponse,
    ProductPublicShareCreateWorkspaceAcceptedResponse,
    ProductPublicShareDetailResponse,
    ProductPublicShareHistoryResponse,
    ProductPublicShareImportAcceptedResponse,
    ProductPublicShareMutationResponse,
    ProductPublicShareRunAcceptedResponse,
    ProductRelatedPublicShareResponse,
    ProductSavedPublicShareCollectionResponse,
    ProductSavedPublicShareMutationResponse,
    ProductWorkspaceShellShareCreatedResponse,
)
from src.server.run_action_log_models import ProductRunActionLogResponse
from src.server.run_admission_models import (
    ProductClientContext,
    ProductExecutionTarget,
    ProductLaunchOptions,
    ProductRunLaunchAcceptedResponse,
    ProductRunLaunchRejectedResponse,
    ProductRunLaunchRequest,
)
from src.server.run_control_models import (
    ProductRunControlAcceptedResponse,
    ProductRunControlRejectedResponse,
)
from src.server.run_list_models import ProductWorkspaceRunListResponse
from src.server.run_read_models import (
    ProductRunResultResponse,
    ProductRunStatusResponse,
    ProductSourceArtifactView,
)
from src.server.workspace_feedback_models import (
    ProductWorkspaceFeedbackReadResponse,
    ProductWorkspaceFeedbackWriteAcceptedResponse,
    ProductWorkspaceFeedbackWriteRequest,
)
from src.server.workspace_result_history_models import ProductWorkspaceResultHistoryResponse
from src.server.workspace_onboarding_models import (
    ProductOnboardingReadResponse,
    ProductOnboardingWriteAcceptedResponse,
    ProductOnboardingWriteRequest,
    ProductWorkspaceCreateRequest,
    ProductWorkspaceDetailResponse,
    ProductWorkspaceListResponse,
    ProductWorkspaceWriteAcceptedResponse,
)
from src.server.workspace_shell_models import (
    ProductWorkspaceShellCheckoutResponse,
    ProductWorkspaceShellCommitResponse,
    ProductWorkspaceShellDraftSavedResponse,
    ProductWorkspaceShellLaunchAcceptedResponse,
    ProductWorkspaceShellRuntimeResponse,
)

PUBLIC_SERVER_SDK_SURFACE_VERSION = "1.0"

__all__ = [
    "PUBLIC_SERVER_SDK_SURFACE_VERSION",
    "RunHttpRouteSurface",
    "FrameworkRouteBindings",
    "FastApiRouteBindings",
    "create_fastapi_app",
    "ProductExecutionTarget",
    "ProductLaunchOptions",
    "ProductClientContext",
    "ProductRunLaunchRequest",
    "ProductRunLaunchAcceptedResponse",
    "ProductRunLaunchRejectedResponse",
    "ProductSourceArtifactView",
    "ProductRunStatusResponse",
    "ProductRunResultResponse",
    "ProductWorkspaceRunListResponse",
    "ProductRunArtifactsResponse",
    "ProductArtifactDetailResponse",
    "ProductRunTraceResponse",
    "ProductRunControlAcceptedResponse",
    "ProductRunControlRejectedResponse",
    "ProductRunActionLogResponse",
    "ProductRecentActivityResponse",
    "ProductHistorySummaryResponse",
    "ProductCircuitLibraryResponse",
    "ProductStarterTemplateCatalogResponse",
    "ProductStarterTemplateDetailResponse",
    "ProductStarterTemplateApplyAcceptedResponse",
    "ProductPublicNexFormatResponse",
    "ProductPublicMcpManifestResponse",
    "ProductPublicMcpHostBridgeResponse",
    "ProductWorkspaceCreateRequest",
    "ProductWorkspaceWriteAcceptedResponse",
    "ProductProviderCatalogResponse",
    "ProductWorkspaceProviderBindingsResponse",
    "ProductProviderBindingWriteRequest",
    "ProductProviderBindingWriteAcceptedResponse",
    "ProductWorkspaceProviderHealthResponse",
    "ProductProviderHealthDetailResponse",
    "ProductProviderProbeRequest",
    "ProductProviderProbeResponse",
    "ProductProviderProbeHistoryResponse",
    "ProductOnboardingReadResponse",
    "ProductOnboardingWriteRequest",
    "ProductOnboardingWriteAcceptedResponse",
    "ProductWorkspaceDetailResponse",
    "ProductWorkspaceListResponse",
    "ProductWorkspaceResultHistoryResponse",
    "ProductWorkspaceFeedbackReadResponse",
    "ProductWorkspaceFeedbackWriteRequest",
    "ProductWorkspaceFeedbackWriteAcceptedResponse",
    "ProductWorkspaceShellRuntimeResponse",
    "ProductWorkspaceShellDraftSavedResponse",
    "ProductWorkspaceShellCommitResponse",
    "ProductWorkspaceShellCheckoutResponse",
    "ProductWorkspaceShellLaunchAcceptedResponse",
    "ProductWorkspaceShellShareCreatedResponse",
    "ProductPublicShareCapabilitySummaryView",
    "ProductPublicShareActionAvailabilityView",
    "ProductPublicShareCatalogResponse",
    "ProductPublicShareCatalogSummaryResponse",
    "ProductPublicShareIssuerCatalogResponse",
    "ProductPublicShareIssuerCatalogSummaryResponse",
    "ProductSavedPublicShareCollectionResponse",
    "ProductSavedPublicShareMutationResponse",
    "ProductRelatedPublicShareResponse",
    "ProductPublicShareCompareSummaryResponse",
    "ProductPublicShareCheckoutAcceptedResponse",
    "ProductPublicShareCreateWorkspaceAcceptedResponse",
    "ProductPublicShareDetailResponse",
    "ProductPublicShareHistoryResponse",
    "ProductPublicShareImportAcceptedResponse",
    "ProductPublicShareArtifactResponse",
    "ProductPublicShareMutationResponse",
    "ProductPublicShareRunAcceptedResponse",
    "ProductIssuerPublicShareListResponse",
    "ProductIssuerPublicShareSummaryResponse",
    "ProductIssuerPublicShareActionReportEntryView",
    "ProductIssuerPublicShareActionReportSummaryView",
    "ProductIssuerPublicShareActionReportListResponse",
    "ProductIssuerPublicShareActionReportSummaryResponse",
    "ProductIssuerPublicShareBulkMutationResponse",
]
