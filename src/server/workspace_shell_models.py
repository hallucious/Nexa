from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.server.run_admission_models import ProductRunLaunchAcceptedResponse


@dataclass(frozen=True)
class ProductWorkspaceShellActionAvailabilityView:
    values: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key, value in self.values.items():
            if not key:
                raise ValueError("ProductWorkspaceShellActionAvailabilityView keys must be non-empty")
            if not isinstance(value, dict):
                raise ValueError("ProductWorkspaceShellActionAvailabilityView values must be dict objects")


@dataclass(frozen=True)
class ProductWorkspaceShellRoutesView:
    values: dict[str, str | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key in self.values:
            if not key:
                raise ValueError("ProductWorkspaceShellRoutesView keys must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceShellRuntimeResponse:
    workspace_id: str
    storage_role: str
    action_availability: ProductWorkspaceShellActionAvailabilityView
    shell: dict[str, Any]
    routes: ProductWorkspaceShellRoutesView
    workspace_title: Optional[str] = None
    app_language: Optional[str] = None
    working_save_id: Optional[str] = None
    commit_id: Optional[str] = None
    launch_request_template: Optional[dict[str, Any]] = None
    continuity: dict[str, Any] = field(default_factory=dict)
    template_gallery: Optional[dict[str, Any]] = None
    navigation: Optional[dict[str, Any]] = None
    step_state_banner: Optional[dict[str, Any]] = None
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceShellRuntimeResponse.workspace_id must be non-empty")
        if not self.storage_role:
            raise ValueError("ProductWorkspaceShellRuntimeResponse.storage_role must be non-empty")
        if not isinstance(self.shell, dict):
            raise ValueError("ProductWorkspaceShellRuntimeResponse.shell must be a dict")


@dataclass(frozen=True)
class ProductWorkspaceShellDraftSavedResponse(ProductWorkspaceShellRuntimeResponse):
    persistence_action: str = "put_workspace_shell_draft"


@dataclass(frozen=True)
class ProductWorkspaceShellCommitResponse(ProductWorkspaceShellRuntimeResponse):
    transition: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.transition:
            raise ValueError("ProductWorkspaceShellCommitResponse.transition must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceShellCheckoutResponse(ProductWorkspaceShellRuntimeResponse):
    transition: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.transition:
            raise ValueError("ProductWorkspaceShellCheckoutResponse.transition must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceShellLaunchAcceptedResponse(ProductRunLaunchAcceptedResponse):
    launch_context: dict[str, Any] = field(default_factory=dict)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.launch_context:
            raise ValueError("ProductWorkspaceShellLaunchAcceptedResponse.launch_context must be non-empty")
