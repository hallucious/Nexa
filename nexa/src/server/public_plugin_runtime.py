from __future__ import annotations

from html import escape
from typing import Any, Mapping

from src.server.public_runtime_utils import escaped_app_route


def render_public_plugin_catalog_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    catalog = dict(payload.get("catalog") or {})
    routes = dict(payload.get("routes") or {})
    title = escape(str(catalog.get("title") or "Public plugin catalog"))
    subtitle = escape(
        str(
            catalog.get("subtitle")
            or "Browse community-facing plugin capabilities and jump to the raw API contract when needed."
        )
    )
    raw_catalog_href = escape(str(routes.get("self") or "/api/integrations/public-plugins/catalog"))
    public_hub_href = escaped_app_route(routes, "public_hub_page", "/app/public", app_language=app_language)
    integration_hub_href = escaped_app_route(routes, "public_integration_hub_page", "/app/integrations", app_language=app_language)
    community_hub_href = escaped_app_route(routes, "community_hub_page", "/app/community", app_language=app_language)

    cards: list[str] = []
    for plugin in list(payload.get("plugins") or ()):
        plugin_map = dict(plugin or {})
        plugin_id = escape(str(plugin_map.get("plugin_id") or "plugin"))
        version = escape(str(plugin_map.get("version") or "unknown"))
        description = escape(str(plugin_map.get("description") or "No public description available."))
        cards.append(
            f"""
            <article class=\"plugin-card\" aria-labelledby=\"plugin-{plugin_id}\">
              <h2 id=\"plugin-{plugin_id}\">{plugin_id}</h2>
              <p class=\"version\">Version: {version}</p>
              <p>{description}</p>
            </article>
            """
        )
    cards_html = "".join(cards) or """
        <article class=\"plugin-card empty\">
          <h2>No public plugins projected yet</h2>
          <p>Public plugins will appear here once they are projected into the catalog.</p>
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
      main {{ max-width: 980px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ color: #cbd5e1; }}
      .top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
      .plugin-card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .plugin-card.empty {{ grid-column: 1 / -1; }}
      .version {{ color: #94a3b8; font-size: 0.95rem; }}
    </style>
  </head>
  <body>
    <main role=\"main\" aria-labelledby=\"public-plugin-title\">
      <header>
        <a class=\"top-link\" href=\"{raw_catalog_href}\">Open raw plugin catalog</a>
        <a class=\"top-link\" href=\"{public_hub_href}\">Open public hub</a>
        <a class=\"top-link\" href=\"{integration_hub_href}\">Open integration hub</a>
        <a class=\"top-link\" href=\"{community_hub_href}\">Open community hub</a>
        <h1 id=\"public-plugin-title\">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class=\"grid\" aria-label=\"Public plugin catalog\">{cards_html}</section>
    </main>
  </body>
</html>"""


__all__ = ["render_public_plugin_catalog_html"]
