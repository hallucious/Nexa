from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductPublicNexFormatResponse:
    status: str
    format_boundary: Mapping[str, Any]
    role_boundaries: Mapping[str, Mapping[str, Any]]
    public_sdk_entrypoints: Mapping[str, str]
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicNexFormatResponse.status: {self.status}")
        if not self.format_boundary:
            raise ValueError("ProductPublicNexFormatResponse.format_boundary must be non-empty")
        if not self.role_boundaries:
            raise ValueError("ProductPublicNexFormatResponse.role_boundaries must be non-empty")
        if not self.public_sdk_entrypoints:
            raise ValueError("ProductPublicNexFormatResponse.public_sdk_entrypoints must be non-empty")
