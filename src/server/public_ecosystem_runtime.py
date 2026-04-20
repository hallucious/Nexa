from __future__ import annotations

from html import escape
from typing import Any, Mapping

from src.server.public_runtime_utils import escaped_app_route


def render_public_ecosystem_catalog_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    catalog = dict(payload.get("catalog") or {})
    routes = dict(payload.get("routes") or {})
    surfaces = dict(payload.get("surfaces") or {})

    title = escape(str(catalog.get("title") or "Public ecosystem catalog"))
    subtitle = escape(
        str(
            catalog.get("subtitle")
            or "Browse the broader public Nexa ecosystem surface spanning SDK, community, public shares, templates, providers, and MCP-facing exports."
        )
    )
    raw_catalog_href = escape(str(routes.get("self") or "/api/integrations/public-ecosystem/catalog"))

    public_hub_href = escaped_app_route(routes, "public_hub_page", "/app/public", app_language=app_language)
    integration_hub_href = escaped_app_route(routes, "public_integration_hub_page", "/app/integrations", app_language=app_language)
    community_hub_href = escaped_app_route(routes, "community_hub_page", "/app/community", app_language=app_language)
    sdk_page_href = escaped_app_route(routes, "public_sdk_catalog_page", "/app/sdk", app_language=app_language)
    plugin_page_href = escaped_app_route(routes, "public_plugin_catalog_page", "/app/plugins", app_language=app_language)

    cards: list[str] = []
    for surface_name, surface_value in surfaces.items():
        surface = dict(surface_value or {})
        surface_family = escape(str(surface.get("surface_family") or surface_name))
        route_family = escape(str(surface.get("route_family") or ""))
        route = escape(str(surface.get("app_route") or surface.get("route") or raw_catalog_href))
        cards.append(
            f"""
            <article class=\"surface-card\" aria-labelledby=\"surface-{escape(surface_name)}\">
              <h2 id=\"surface-{escape(surface_name)}\">{surface_family}</h2>
              <p class=\"route-family\">Route family: {route_family}</p>
              <p class=\"route-target\">Target: {route}</p>
            </article>
            """
        )
    cards_html = "".join(cards) or """
        <article class=\"surface-card empty\">
          <h2>No public ecosystem surfaces projected yet</h2>
          <p>Public ecosystem surfaces will appear here once they are projected into the catalog.</p>
        </article>
    """

    return f"""<!doctype html>
<html lang=\"{escape(app_language)}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
      main {{ max-width: 1080px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ color: #cbd5e1; }}
      .top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
      .surface-card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .surface-card.empty {{ grid-column: 1 / -1; }}
      .route-family {{ color: #94a3b8; font-size: 0.95rem; }}
      .route-target {{ word-break: break-all; }}
    </style>
  </head>
  <body>
    <main role=\"main\" aria-labelledby=\"public-ecosystem-title\">
      <header>
        <a class=\"top-link\" href=\"{raw_catalog_href}\">Open raw ecosystem catalog</a>
        <a class=\"top-link\" href=\"{public_hub_href}\">Open public hub</a>
        <a class=\"top-link\" href=\"{integration_hub_href}\">Open integration hub</a>
        <a class=\"top-link\" href=\"{community_hub_href}\">Open community hub</a>
        <a class=\"top-link\" href=\"{sdk_page_href}\">Open public SDK</a>
        <a class=\"top-link\" href=\"{plugin_page_href}\">Open public plugins</a>
        <h1 id=\"public-ecosystem-title\">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class=\"grid\" aria-label=\"Public ecosystem surfaces\">{cards_html}</section>
    </main>
  </body>
</html>"""


__all__ = ["render_public_ecosystem_catalog_html"]
