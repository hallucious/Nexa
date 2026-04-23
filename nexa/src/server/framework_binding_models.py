from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

_ALLOWED_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class FrameworkRouteDefinition:
    route_name: str
    method: str
    path_template: str
    summary: str

    def __post_init__(self) -> None:
        normalized_method = str(self.method).upper()
        object.__setattr__(self, "method", normalized_method)
        if normalized_method not in _ALLOWED_HTTP_METHODS:
            raise ValueError(f"Unsupported FrameworkRouteDefinition.method: {normalized_method}")
        if not str(self.route_name).strip():
            raise ValueError("FrameworkRouteDefinition.route_name must be non-empty")
        if not str(self.path_template).strip().startswith("/"):
            raise ValueError("FrameworkRouteDefinition.path_template must start with '/'")


@dataclass(frozen=True)
class FrameworkInboundRequest:
    method: str
    path: str
    headers: Mapping[str, Any] = field(default_factory=dict)
    path_params: Mapping[str, Any] = field(default_factory=dict)
    query_params: Mapping[str, Any] = field(default_factory=dict)
    json_body: Any = None
    session_claims: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        normalized_method = str(self.method).upper()
        object.__setattr__(self, "method", normalized_method)
        if normalized_method not in _ALLOWED_HTTP_METHODS:
            raise ValueError(f"Unsupported FrameworkInboundRequest.method: {normalized_method}")
        if not str(self.path).strip():
            raise ValueError("FrameworkInboundRequest.path must be non-empty")


@dataclass(frozen=True)
class FrameworkOutboundResponse:
    status_code: int
    headers: Mapping[str, str]
    body_text: str
    media_type: str = "application/json"

    def __post_init__(self) -> None:
        if self.status_code < 100:
            raise ValueError("FrameworkOutboundResponse.status_code must be >= 100")
        if not isinstance(self.headers, Mapping):
            raise TypeError("FrameworkOutboundResponse.headers must be a mapping")
        if not isinstance(self.body_text, str):
            raise TypeError("FrameworkOutboundResponse.body_text must be a string")
        if not self.media_type:
            raise ValueError("FrameworkOutboundResponse.media_type must be non-empty")
