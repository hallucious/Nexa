from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional

HttpMethod = Literal["GET", "POST", "PUT"]

_ALLOWED_HTTP_METHODS = {"GET", "POST", "PUT"}


@dataclass(frozen=True)
class HttpRouteRequest:
    method: HttpMethod
    path: str
    headers: Mapping[str, Any] = field(default_factory=dict)
    json_body: Any = None
    path_params: Mapping[str, Any] = field(default_factory=dict)
    query_params: Mapping[str, Any] = field(default_factory=dict)
    session_claims: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        normalized_method = str(self.method).upper()
        object.__setattr__(self, "method", normalized_method)
        if normalized_method not in _ALLOWED_HTTP_METHODS:
            raise ValueError(f"Unsupported HttpRouteRequest.method: {normalized_method}")
        if not self.path:
            raise ValueError("HttpRouteRequest.path must be non-empty")


@dataclass(frozen=True)
class HttpRouteResponse:
    status_code: int
    body: Mapping[str, Any]
    headers: Mapping[str, str] = field(default_factory=lambda: {"content-type": "application/json"})

    def __post_init__(self) -> None:
        if self.status_code < 100:
            raise ValueError("HttpRouteResponse.status_code must be >= 100")
        if not isinstance(self.body, Mapping):
            raise TypeError("HttpRouteResponse.body must be a mapping")
        if not isinstance(self.headers, Mapping):
            raise TypeError("HttpRouteResponse.headers must be a mapping")
