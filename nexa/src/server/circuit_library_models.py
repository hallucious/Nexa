from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Any


@dataclass(frozen=True)
class ProductCircuitLibraryResponse:
    status: str
    source_of_truth: str
    library: Mapping[str, Any]
    overview_section: Mapping[str, Any]
    item_sections: tuple[Mapping[str, Any], ...] = ()
    app_language: str = "en"
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductCircuitLibraryResponse.status: {self.status}")
        if not self.source_of_truth:
            raise ValueError("ProductCircuitLibraryResponse.source_of_truth must be non-empty")
        if not self.app_language:
            raise ValueError("ProductCircuitLibraryResponse.app_language must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceCircuitLibraryResponse:
    status: str
    workspace_id: str
    source_of_truth: str
    library: Mapping[str, Any]
    overview_section: Mapping[str, Any]
    item_sections: tuple[Mapping[str, Any], ...] = ()
    app_language: str = "en"
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductWorkspaceCircuitLibraryResponse.status: {self.status}")
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceCircuitLibraryResponse.workspace_id must be non-empty")
        if not self.source_of_truth:
            raise ValueError("ProductWorkspaceCircuitLibraryResponse.source_of_truth must be non-empty")
        if not self.app_language:
            raise ValueError("ProductWorkspaceCircuitLibraryResponse.app_language must be non-empty")
