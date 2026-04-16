from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductPublicMcpManifestResponse:
    status: str
    manifest: Mapping[str, Any]
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicMcpManifestResponse.status: {self.status}")
        if not self.manifest:
            raise ValueError("ProductPublicMcpManifestResponse.manifest must be non-empty")


@dataclass(frozen=True)
class ProductPublicMcpHostBridgeResponse:
    status: str
    host_bridge: Mapping[str, Any]
    routes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicMcpHostBridgeResponse.status: {self.status}")
        if not self.host_bridge:
            raise ValueError("ProductPublicMcpHostBridgeResponse.host_bridge must be non-empty")
