from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductStarterTemplateCatalogResponse:
    status: str
    catalog: Mapping[str, Any]
    categories: tuple[Mapping[str, Any], ...] = ()
    templates: tuple[Mapping[str, Any], ...] = ()
    app_language: str = "en"
    routes: Mapping[str, str] = field(default_factory=dict)
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductStarterTemplateCatalogResponse.status: {self.status}")
        if not self.catalog:
            raise ValueError("ProductStarterTemplateCatalogResponse.catalog must be non-empty")
        if not self.app_language:
            raise ValueError("ProductStarterTemplateCatalogResponse.app_language must be non-empty")


@dataclass(frozen=True)
class ProductStarterTemplateDetailResponse:
    status: str
    template: Mapping[str, Any]
    app_language: str = "en"
    routes: Mapping[str, str] = field(default_factory=dict)
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductStarterTemplateDetailResponse.status: {self.status}")
        if not self.template:
            raise ValueError("ProductStarterTemplateDetailResponse.template must be non-empty")
        if not self.app_language:
            raise ValueError("ProductStarterTemplateDetailResponse.app_language must be non-empty")




@dataclass(frozen=True)
class ProductWorkspaceStarterTemplateCatalogResponse:
    status: str
    workspace_id: str
    catalog: Mapping[str, Any]
    categories: tuple[Mapping[str, Any], ...] = ()
    templates: tuple[Mapping[str, Any], ...] = ()
    app_language: str = "en"
    routes: Mapping[str, str] = field(default_factory=dict)
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductWorkspaceStarterTemplateCatalogResponse.status: {self.status}")
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceStarterTemplateCatalogResponse.workspace_id must be non-empty")
        if not self.catalog:
            raise ValueError("ProductWorkspaceStarterTemplateCatalogResponse.catalog must be non-empty")
        if not self.app_language:
            raise ValueError("ProductWorkspaceStarterTemplateCatalogResponse.app_language must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceStarterTemplateDetailResponse:
    status: str
    workspace_id: str
    template: Mapping[str, Any]
    app_language: str = "en"
    routes: Mapping[str, str] = field(default_factory=dict)
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductWorkspaceStarterTemplateDetailResponse.status: {self.status}")
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceStarterTemplateDetailResponse.workspace_id must be non-empty")
        if not self.template:
            raise ValueError("ProductWorkspaceStarterTemplateDetailResponse.template must be non-empty")
        if not self.app_language:
            raise ValueError("ProductWorkspaceStarterTemplateDetailResponse.app_language must be non-empty")

@dataclass(frozen=True)
class ProductStarterTemplateApplyAcceptedResponse:
    status: str
    workspace_id: str
    template: Mapping[str, Any]
    shell: Mapping[str, Any]
    routes: Mapping[str, str] = field(default_factory=dict)
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "ready"}:
            raise ValueError(f"Unsupported ProductStarterTemplateApplyAcceptedResponse.status: {self.status}")
        if not self.workspace_id:
            raise ValueError("ProductStarterTemplateApplyAcceptedResponse.workspace_id must be non-empty")
        if not self.template:
            raise ValueError("ProductStarterTemplateApplyAcceptedResponse.template must be non-empty")
        if not self.shell:
            raise ValueError("ProductStarterTemplateApplyAcceptedResponse.shell must be non-empty")
