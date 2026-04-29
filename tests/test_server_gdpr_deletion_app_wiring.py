from __future__ import annotations

from typing import Any, Mapping

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.gdpr_deletion_api import GDPR_DELETION_ROUTE, build_gdpr_deletion_router


def _route_paths(app) -> set[str]:  # noqa: ANN001
    return {str(getattr(route, "path", "")) for route in app.routes}


def test_fastapi_app_does_not_mount_gdpr_deletion_route_by_default() -> None:
    app = create_fastapi_app(dependencies=FastApiRouteDependencies())

    assert GDPR_DELETION_ROUTE not in _route_paths(app)


def test_fastapi_app_mounts_gdpr_deletion_route_when_dependency_provider_is_set() -> None:
    def _mutable_row_deleter(_table_name: str, _user_ref: str) -> int:
        return 1

    def _object_storage_deleter(_object_ref: str) -> bool:
        return True

    def _audit_writer(_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return dict(_payload)

    def _router_provider():
        return build_gdpr_deletion_router(
            mutable_row_deleter=_mutable_row_deleter,
            object_storage_deleter=_object_storage_deleter,
            audit_writer=_audit_writer,
        )

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(gdpr_deletion_router_provider=_router_provider)
    )

    assert GDPR_DELETION_ROUTE in _route_paths(app)


def test_fastapi_app_allows_gdpr_router_provider_to_return_none() -> None:
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(gdpr_deletion_router_provider=lambda: None)
    )

    assert GDPR_DELETION_ROUTE not in _route_paths(app)
