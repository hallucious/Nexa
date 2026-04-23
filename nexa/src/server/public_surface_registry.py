from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


PUBLIC_API_ROUTES: dict[str, str] = {
    "public_sdk_catalog": "/api/integrations/public-sdk/catalog",
    "public_ecosystem_catalog": "/api/integrations/public-ecosystem/catalog",
    "public_plugin_catalog": "/api/integrations/public-plugins/catalog",
    "public_community_catalog": "/api/integrations/public-community/catalog",
    "public_mcp_manifest": "/api/integrations/public-mcp/manifest",
    "public_mcp_host_bridge": "/api/integrations/public-mcp/host-bridge",
    "public_nex_format": "/api/formats/public-nex",
    "public_share_catalog": "/api/public-shares",
    "public_share_catalog_summary": "/api/public-shares/summary",
    "starter_template_catalog": "/api/templates/starter-circuits",
    "provider_catalog": "/api/providers/catalog",
}


PUBLIC_APP_ROUTES: dict[str, str] = {
    "public_hub_page": "/app/public",
    "public_integration_hub_page": "/app/integrations",
    "community_hub_page": "/app/community",
    "public_ecosystem_catalog_page": "/app/ecosystem",
    "public_sdk_catalog_page": "/app/sdk",
    "public_plugin_catalog_page": "/app/plugins",
    "public_mcp_catalog_page": "/app/mcp",
    "provider_catalog_page": "/app/providers",
    "public_nex_format_page": "/app/public-nex",
    "starter_template_catalog_page": "/app/templates/starter-circuits",
    "public_share_catalog_page": "/app/public-shares",
    "public_share_catalog_summary_page": "/app/public-shares/summary",
}


PUBLIC_COMMUNITY_ASSET_SURFACE_FAMILIES: tuple[str, ...] = (
    "starter-template-catalog",
    "public-share-catalog",
    "public-plugin-catalog",
    "public-mcp-catalog",
)


@dataclass(frozen=True)
class PublicCommunityAssetSpec:
    asset_family: str
    surface_family: str
    community_role: str
    api_route_key: str
    app_route_key: str
    route_family: str


PUBLIC_COMMUNITY_ASSET_SPECS: tuple[PublicCommunityAssetSpec, ...] = (
    PublicCommunityAssetSpec(
        asset_family="starter-templates",
        surface_family="starter-template-catalog",
        community_role="remixable workflow starting points",
        api_route_key="starter_template_catalog",
        app_route_key="starter_template_catalog_page",
        route_family="starter-template-catalog-read",
    ),
    PublicCommunityAssetSpec(
        asset_family="public-shares",
        surface_family="public-share-catalog",
        community_role="shared public Nexa artifacts and run-ready examples",
        api_route_key="public_share_catalog",
        app_route_key="public_share_catalog_page",
        route_family="public-share-catalog",
    ),
    PublicCommunityAssetSpec(
        asset_family="public-plugins",
        surface_family="public-plugin-catalog",
        community_role="extendable community-facing capabilities",
        api_route_key="public_plugin_catalog",
        app_route_key="public_plugin_catalog_page",
        route_family="public-plugin-catalog-read",
    ),
    PublicCommunityAssetSpec(
        asset_family="public-mcp",
        surface_family="public-mcp-catalog",
        community_role="tool/resource compatibility bridge for external integrations",
        api_route_key="public_mcp_manifest",
        app_route_key="public_mcp_catalog_page",
        route_family="public-mcp-manifest-read",
    ),
)


@dataclass(frozen=True)
class PublicEcosystemSurfaceSpec:
    surface_name: str
    surface_family: str
    route_family: str
    api_route_key: str
    app_route_key: str | None = None


PUBLIC_ECOSYSTEM_SURFACE_SPECS: tuple[PublicEcosystemSurfaceSpec, ...] = (
    PublicEcosystemSurfaceSpec(
        surface_name="public_sdk_catalog",
        surface_family="public-sdk-catalog",
        route_family="public-sdk-catalog-read",
        api_route_key="public_sdk_catalog",
        app_route_key="public_sdk_catalog_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_nex_format",
        surface_family="public-nex-format",
        route_family="public-nex-format-read",
        api_route_key="public_nex_format",
        app_route_key="public_nex_format_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_plugin_catalog",
        surface_family="public-plugin-catalog",
        route_family="public-plugin-catalog-read",
        api_route_key="public_plugin_catalog",
        app_route_key="public_plugin_catalog_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_community_catalog",
        surface_family="public-community-catalog",
        route_family="public-community-catalog-read",
        api_route_key="public_community_catalog",
        app_route_key="community_hub_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_mcp_manifest",
        surface_family="public-mcp-manifest",
        route_family="public-mcp-manifest-read",
        api_route_key="public_mcp_manifest",
        app_route_key="public_mcp_catalog_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_mcp_host_bridge",
        surface_family="public-mcp-host-bridge",
        route_family="public-mcp-host-bridge-read",
        api_route_key="public_mcp_host_bridge",
        app_route_key="public_mcp_catalog_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_share_catalog",
        surface_family="public-share-catalog",
        route_family="public-share-catalog",
        api_route_key="public_share_catalog",
        app_route_key="public_share_catalog_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="public_share_catalog_summary",
        surface_family="public-share-catalog-summary",
        route_family="public-share-catalog-summary",
        api_route_key="public_share_catalog_summary",
        app_route_key="public_share_catalog_summary_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="starter_template_catalog",
        surface_family="starter-template-catalog",
        route_family="starter-template-catalog-read",
        api_route_key="starter_template_catalog",
        app_route_key="starter_template_catalog_page",
    ),
    PublicEcosystemSurfaceSpec(
        surface_name="provider_catalog",
        surface_family="provider-catalog",
        route_family="provider-catalog-read",
        api_route_key="provider_catalog",
        app_route_key="provider_catalog_page",
    ),
)


def api_route(route_key: str) -> str:
    return PUBLIC_API_ROUTES[route_key]



def app_route(route_key: str) -> str:
    return PUBLIC_APP_ROUTES[route_key]



def app_href(route_key: str, *, app_language: str | None = None, workspace_id: str | None = None) -> str:
    href = app_route(route_key)
    query_parts: list[str] = []
    if app_language:
        query_parts.append(f"app_language={app_language}")
    if workspace_id:
        query_parts.append(f"workspace_id={workspace_id}")
    if not query_parts:
        return href
    joiner = "&" if "?" in href else "?"
    return f"{href}{joiner}{'&'.join(query_parts)}"



def build_public_sdk_route_map() -> dict[str, str]:
    return {
        "self": api_route("public_sdk_catalog"),
        "app_catalog_page": app_route("public_sdk_catalog_page"),
        "public_hub_page": app_route("public_hub_page"),
        "public_integration_hub_page": app_route("public_integration_hub_page"),
        "ecosystem_catalog_page": app_route("public_ecosystem_catalog_page"),
        "community_hub_page": app_route("community_hub_page"),
        "public_plugin_catalog_page": app_route("public_plugin_catalog_page"),
        "public_mcp_catalog_page": app_route("public_mcp_catalog_page"),
        "provider_catalog_page": app_route("provider_catalog_page"),
        "public_nex_format_page": app_route("public_nex_format_page"),
        "public_nex_format": api_route("public_nex_format"),
        "public_plugin_catalog": api_route("public_plugin_catalog"),
        "public_community_catalog": api_route("public_community_catalog"),
        "public_mcp_manifest": api_route("public_mcp_manifest"),
        "public_mcp_host_bridge": api_route("public_mcp_host_bridge"),
        "public_share_catalog": api_route("public_share_catalog"),
        "provider_catalog": api_route("provider_catalog"),
    }



def build_public_plugin_route_map(discovery_routes: Mapping[str, str]) -> dict[str, str]:
    return {
        "self": api_route("public_plugin_catalog"),
        "app_catalog_page": app_route("public_plugin_catalog_page"),
        "community_hub_page": app_route("community_hub_page"),
        **dict(discovery_routes),
    }



def build_public_community_route_map(discovery_routes: Mapping[str, str]) -> dict[str, str]:
    return {
        "self": api_route("public_community_catalog"),
        "public_hub_page": app_route("public_hub_page"),
        "public_integration_hub_page": app_route("public_integration_hub_page"),
        "app_hub": app_route("community_hub_page"),
        "starter_template_catalog_page": app_route("starter_template_catalog_page"),
        "public_share_catalog_page": app_route("public_share_catalog_page"),
        "public_plugin_catalog_page": app_route("public_plugin_catalog_page"),
        "public_mcp_catalog_page": app_route("public_mcp_catalog_page"),
        **dict(discovery_routes),
    }



def build_public_ecosystem_route_map(discovery_routes: Mapping[str, str]) -> dict[str, str]:
    return {
        "self": api_route("public_ecosystem_catalog"),
        "app_catalog_page": app_route("public_ecosystem_catalog_page"),
        "public_hub_page": app_route("public_hub_page"),
        "public_integration_hub_page": app_route("public_integration_hub_page"),
        "community_hub_page": app_route("community_hub_page"),
        "public_sdk_catalog_page": app_route("public_sdk_catalog_page"),
        "public_plugin_catalog_page": app_route("public_plugin_catalog_page"),
        "public_mcp_catalog_page": app_route("public_mcp_catalog_page"),
        "provider_catalog_page": app_route("provider_catalog_page"),
        "public_nex_format_page": app_route("public_nex_format_page"),
        **dict(discovery_routes),
    }



def build_provider_catalog_route_map() -> dict[str, str]:
    return {
        "self": api_route("provider_catalog"),
        "app_catalog_page": app_route("provider_catalog_page"),
        "public_hub_page": app_route("public_hub_page"),
        "public_integration_hub_page": app_route("public_integration_hub_page"),
        "ecosystem_catalog_page": app_route("public_ecosystem_catalog_page"),
        "community_hub_page": app_route("community_hub_page"),
        "public_sdk_catalog_page": app_route("public_sdk_catalog_page"),
        "public_mcp_catalog_page": app_route("public_mcp_catalog_page"),
    }



def build_public_nex_route_map() -> dict[str, str]:
    return {
        "app_catalog_page": app_route("public_nex_format_page"),
        "public_hub_page": app_route("public_hub_page"),
        "public_integration_hub_page": app_route("public_integration_hub_page"),
        "ecosystem_catalog_page": app_route("public_ecosystem_catalog_page"),
        "community_hub_page": app_route("community_hub_page"),
        "public_sdk_catalog_page": app_route("public_sdk_catalog_page"),
        "public_mcp_catalog_page": app_route("public_mcp_catalog_page"),
        "provider_catalog_page": app_route("provider_catalog_page"),
    }



def build_public_community_assets(
    *,
    starter_templates: Sequence[Any],
    share_boundary: Any,
    plugin_summary: Any,
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for spec in PUBLIC_COMMUNITY_ASSET_SPECS:
        asset: dict[str, Any] = {
            "asset_family": spec.asset_family,
            "surface_family": spec.surface_family,
            "community_role": spec.community_role,
            "route": api_route(spec.api_route_key),
            "app_route": app_route(spec.app_route_key),
        }
        if spec.asset_family == "starter-templates":
            asset["public_item_count"] = len(starter_templates)
            asset["sample_ids"] = [template.template_id for template in starter_templates[:3]]
        elif spec.asset_family == "public-shares":
            asset["public_operation_count"] = len(share_boundary.supported_operations)
            asset["supported_operations"] = list(share_boundary.supported_operations)
        elif spec.asset_family == "public-plugins":
            asset["public_item_count"] = plugin_summary.plugin_count
            asset["sample_ids"] = list(plugin_summary.plugin_ids[:3])
        elif spec.asset_family == "public-mcp":
            asset["public_item_count"] = 2
            asset["sample_ids"] = ["manifest", "host-bridge"]
        assets.append(asset)
    return assets



def build_public_ecosystem_surfaces() -> dict[str, dict[str, str]]:
    surfaces: dict[str, dict[str, str]] = {}
    for spec in PUBLIC_ECOSYSTEM_SURFACE_SPECS:
        entry = {
            "surface_family": spec.surface_family,
            "route_family": spec.route_family,
            "route": api_route(spec.api_route_key),
        }
        if spec.app_route_key is not None:
            entry["app_route"] = app_route(spec.app_route_key)
        surfaces[spec.surface_name] = entry
    return surfaces



def community_asset_app_route_key(asset_family: str) -> str | None:
    for spec in PUBLIC_COMMUNITY_ASSET_SPECS:
        if spec.asset_family == asset_family:
            return spec.app_route_key
    return None



def ecosystem_surface_app_route_key(surface_name: str) -> str | None:
    for spec in PUBLIC_ECOSYSTEM_SURFACE_SPECS:
        if spec.surface_name == surface_name:
            return spec.app_route_key
    return None



def with_app_route_map(route_keys: Mapping[str, str], *, app_language: str | None = None, workspace_id: str | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in route_keys.items():
        if key in PUBLIC_APP_ROUTES:
            result[key] = app_href(key, app_language=app_language, workspace_id=workspace_id)
        else:
            result[key] = value
    return result


__all__ = [
    "PUBLIC_API_ROUTES",
    "PUBLIC_APP_ROUTES",
    "PUBLIC_COMMUNITY_ASSET_SPECS",
    "PUBLIC_COMMUNITY_ASSET_SURFACE_FAMILIES",
    "PUBLIC_ECOSYSTEM_SURFACE_SPECS",
    "api_route",
    "app_route",
    "app_href",
    "build_provider_catalog_route_map",
    "build_public_community_assets",
    "build_public_community_route_map",
    "build_public_ecosystem_route_map",
    "build_public_ecosystem_surfaces",
    "build_public_nex_route_map",
    "build_public_plugin_route_map",
    "build_public_sdk_route_map",
    "community_asset_app_route_key",
    "ecosystem_surface_app_route_key",
    "with_app_route_map",
]
