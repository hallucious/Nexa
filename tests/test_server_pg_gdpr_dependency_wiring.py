from __future__ import annotations

from src.server.gdpr_deletion_api import GDPR_DELETION_ROUTE
from src.server.pg.dependencies_factory import build_postgres_gdpr_deletion_router_provider_if_available


class _FakeEngine:
    pass


class _FakeS3:
    pass


def _route_paths(router) -> set[str]:  # noqa: ANN001
    return {str(getattr(route, "path", "")) for route in router.routes}


def test_postgres_gdpr_router_provider_is_absent_without_object_storage_client(monkeypatch) -> None:  # noqa: ANN001
    from src.server.pg import dependencies_factory

    monkeypatch.setattr(dependencies_factory, "_table_exists", lambda _engine, _table: True)

    provider = build_postgres_gdpr_deletion_router_provider_if_available(
        sync_engine=_FakeEngine(),
        object_storage_client=None,
        object_storage_bucket="bucket",
    )

    assert provider is None


def test_postgres_gdpr_router_provider_is_absent_without_audit_table(monkeypatch) -> None:  # noqa: ANN001
    from src.server.pg import dependencies_factory

    monkeypatch.setattr(dependencies_factory, "_table_exists", lambda _engine, _table: False)

    provider = build_postgres_gdpr_deletion_router_provider_if_available(
        sync_engine=_FakeEngine(),
        object_storage_client=_FakeS3(),
        object_storage_bucket="bucket",
    )

    assert provider is None


def test_postgres_gdpr_router_provider_is_available_when_dependencies_exist(monkeypatch) -> None:  # noqa: ANN001
    from src.server.pg import dependencies_factory

    monkeypatch.setattr(dependencies_factory, "_table_exists", lambda _engine, _table: True)

    provider = build_postgres_gdpr_deletion_router_provider_if_available(
        sync_engine=_FakeEngine(),
        object_storage_client=_FakeS3(),
        object_storage_bucket="bucket",
    )

    assert provider is not None
    router = provider()
    assert GDPR_DELETION_ROUTE in _route_paths(router)
