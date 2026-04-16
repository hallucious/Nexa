from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ProductWorkspaceResultHistoryResponse:
    status: str
    workspace_id: str
    workspace_title: str
    source_of_truth: str
    result_history: Mapping[str, Any]
    overview_section: Mapping[str, Any]
    item_sections: tuple[Mapping[str, Any], ...] = ()
    selected_result: Optional[Mapping[str, Any]] = None
    onboarding_banner: Optional[Mapping[str, Any]] = None
    app_language: str = "en"
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductWorkspaceResultHistoryResponse.status: {self.status}")
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceResultHistoryResponse.workspace_id must be non-empty")
        if not self.workspace_title:
            raise ValueError("ProductWorkspaceResultHistoryResponse.workspace_title must be non-empty")
        if not self.source_of_truth:
            raise ValueError("ProductWorkspaceResultHistoryResponse.source_of_truth must be non-empty")
        if not self.app_language:
            raise ValueError("ProductWorkspaceResultHistoryResponse.app_language must be non-empty")
