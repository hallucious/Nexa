from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductPublicMcpManifestResponse:
    status: str
    manifest: Mapping[str, Any]
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    public_sdk_entrypoints: Mapping[str, str] = field(default_factory=dict)
    supported_contract_markers: tuple[str, ...] = ()
    supported_runtime_markers: tuple[str, ...] = ()
    supported_transport_kinds: tuple[str, ...] = ()
    tool_count: int | None = None
    resource_count: int | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicMcpManifestResponse.status: {self.status}")
        if not self.manifest:
            raise ValueError("ProductPublicMcpManifestResponse.manifest must be non-empty")


@dataclass(frozen=True)
class ProductPublicMcpHostBridgeResponse:
    status: str
    host_bridge: Mapping[str, Any]
    identity_policy: Mapping[str, Any] | None = None
    namespace_policy: Mapping[str, Any] | None = None
    routes: Mapping[str, str] = field(default_factory=dict)
    public_sdk_entrypoints: Mapping[str, str] = field(default_factory=dict)
    supported_contract_markers: tuple[str, ...] = ()
    supported_runtime_markers: tuple[str, ...] = ()
    supported_transport_kinds: tuple[str, ...] = ()
    tool_count: int | None = None
    resource_count: int | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "accepted"}:
            raise ValueError(f"Unsupported ProductPublicMcpHostBridgeResponse.status: {self.status}")
        if not self.host_bridge:
            raise ValueError("ProductPublicMcpHostBridgeResponse.host_bridge must be non-empty")
