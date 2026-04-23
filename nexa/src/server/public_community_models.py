from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductPublicCommunityCatalogResponse:
    status: str
    catalog: Mapping[str, Any]
    assets: tuple[Mapping[str, Any], ...] = ()
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    public_sdk_entrypoints: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicCommunityCatalogResponse.status: {self.status}")
        if not self.catalog:
            raise ValueError("ProductPublicCommunityCatalogResponse.catalog must be non-empty")
        if not self.assets:
            raise ValueError("ProductPublicCommunityCatalogResponse.assets must be non-empty")
