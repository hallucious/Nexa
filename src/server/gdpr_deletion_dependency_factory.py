from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Request

from src.server.gdpr_deletion_adapters import (
    GdprDeletionAdapterSet,
    GdprObjectStorageDeletionAdapter,
    GdprPostgresDeletionAdapter,
)
from src.server.gdpr_deletion_api import build_gdpr_deletion_router
from src.server.gdpr_deletion_runtime import IdentityDeleter

SessionClaimsResolver = Callable[[Request], Mapping[str, Any] | None]
GdprDeletionRouterProvider = Callable[[], APIRouter | None]


def build_gdpr_deletion_router_provider(
    *,
    sync_engine: Any,
    object_storage_client: Any,
    default_bucket: str | None = None,
    identity_deleter: IdentityDeleter | None = None,
    session_claims_resolver: SessionClaimsResolver | None = None,
) -> GdprDeletionRouterProvider:
    """Build an opt-in provider for the guarded GDPR deletion admin router.

    The provider intentionally creates the router lazily so app construction can
    own route inclusion while dependency construction owns concrete adapter
    wiring. The route remains admin-only because the router produced here is the
    guarded router from ``gdpr_deletion_api``.
    """

    if object_storage_client is None:
        raise ValueError("object_storage_client is required for GDPR deletion router wiring")

    def _provider() -> APIRouter:
        adapter_set = GdprDeletionAdapterSet(
            postgres=GdprPostgresDeletionAdapter(engine=sync_engine),
            object_storage=GdprObjectStorageDeletionAdapter(
                object_storage_client=object_storage_client,
                default_bucket=default_bucket,
            ),
            identity_deleter=identity_deleter,
        )
        return build_gdpr_deletion_router(
            **adapter_set.route_kwargs(),
            session_claims_resolver=session_claims_resolver,
        )

    return _provider


__all__ = [
    "GdprDeletionRouterProvider",
    "SessionClaimsResolver",
    "build_gdpr_deletion_router_provider",
]
