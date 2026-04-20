from __future__ import annotations

from src.public_surface_registry import (
    PUBLIC_API_ROUTES,
    PUBLIC_APP_ROUTES,
    PUBLIC_COMMUNITY_ASSET_SPECS,
    PUBLIC_COMMUNITY_ASSET_SURFACE_FAMILIES,
    PUBLIC_ECOSYSTEM_SURFACE_SPECS,
    app_href,
    build_public_ecosystem_surfaces,
)


def test_public_surface_registry_routes_are_unique_within_each_family() -> None:
    assert len(set(PUBLIC_API_ROUTES.values())) == len(PUBLIC_API_ROUTES)
    assert len(set(PUBLIC_APP_ROUTES.values())) == len(PUBLIC_APP_ROUTES)


def test_public_community_asset_family_count_matches_asset_specs() -> None:
    assert tuple(spec.surface_family for spec in PUBLIC_COMMUNITY_ASSET_SPECS) == PUBLIC_COMMUNITY_ASSET_SURFACE_FAMILIES


def test_public_ecosystem_surface_specs_cover_surface_builder_output() -> None:
    surfaces = build_public_ecosystem_surfaces()
    assert set(surfaces.keys()) == {spec.surface_name for spec in PUBLIC_ECOSYSTEM_SURFACE_SPECS}


def test_app_href_appends_language_and_workspace_when_requested() -> None:
    href = app_href("community_hub_page", app_language="ko", workspace_id="ws-001")
    assert href == "/app/community?app_language=ko&workspace_id=ws-001"
