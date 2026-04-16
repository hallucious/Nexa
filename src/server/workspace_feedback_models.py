from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

_ALLOWED_FEEDBACK_CATEGORIES = {"confusing_screen", "friction_note", "bug_report"}
_ALLOWED_FEEDBACK_SURFACES = {"circuit_library", "result_history", "workspace_shell", "unknown"}
_ALLOWED_FEEDBACK_STATUS = {"ready", "accepted"}


@dataclass(frozen=True)
class ProductWorkspaceFeedbackWriteRequest:
    category: str
    surface: str
    message: str
    run_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.category not in _ALLOWED_FEEDBACK_CATEGORIES:
            raise ValueError(f"Unsupported ProductWorkspaceFeedbackWriteRequest.category: {self.category}")
        if self.surface not in _ALLOWED_FEEDBACK_SURFACES:
            raise ValueError(f"Unsupported ProductWorkspaceFeedbackWriteRequest.surface: {self.surface}")
        if not self.message.strip():
            raise ValueError("ProductWorkspaceFeedbackWriteRequest.message must be non-empty")
        if len(self.message) > 1000:
            raise ValueError("ProductWorkspaceFeedbackWriteRequest.message must be 1000 characters or fewer")


@dataclass(frozen=True)
class ProductWorkspaceFeedbackReadResponse:
    status: str
    app_language: str
    workspace_id: str
    workspace_title: str
    feedback_channel: Mapping[str, Any]
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_FEEDBACK_STATUS:
            raise ValueError(f"Unsupported ProductWorkspaceFeedbackReadResponse.status: {self.status}")
        if not self.app_language:
            raise ValueError("ProductWorkspaceFeedbackReadResponse.app_language must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceFeedbackReadResponse.workspace_id must be non-empty")
        if not self.workspace_title:
            raise ValueError("ProductWorkspaceFeedbackReadResponse.workspace_title must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceFeedbackWriteAcceptedResponse:
    status: str
    message: str
    feedback: Mapping[str, Any]
    links: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status != "accepted":
            raise ValueError(f"Unsupported ProductWorkspaceFeedbackWriteAcceptedResponse.status: {self.status}")
        if not self.message:
            raise ValueError("ProductWorkspaceFeedbackWriteAcceptedResponse.message must be non-empty")
        feedback_id = str(self.feedback.get("feedback_id") or "").strip()
        if not feedback_id:
            raise ValueError("ProductWorkspaceFeedbackWriteAcceptedResponse.feedback.feedback_id must be non-empty")
