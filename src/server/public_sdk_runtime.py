from __future__ import annotations

from html import escape
from typing import Any, Mapping


def render_public_sdk_catalog_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    catalog = dict(payload.get("catalog") or {})
    routes = dict(payload.get("routes") or {})
    tools = list(payload.get("tools") or ())
    resources = list(payload.get("resources") or ())
    title = escape(str(catalog.get("title") or "Public SDK catalog"))
    subtitle = escape(
        str(
            catalog.get("subtitle")
            or "Browse the public Nexa SDK surface, jump to related public/community pages, and inspect exposed MCP-facing tools and resources."
        )
    )
    raw_catalog_href = escape(str(routes.get("self") or "/api/integrations/public-sdk/catalog"))

    ecosystem_route = str(routes.get("ecosystem_catalog_page") or "/app/ecosystem").strip() or "/app/ecosystem"
    if "app_language=" not in ecosystem_route:
        joiner = "&" if "?" in ecosystem_route else "?"
        ecosystem_route = f"{ecosystem_route}{joiner}app_language={app_language}"
    ecosystem_href = escape(ecosystem_route)

    community_route = str(routes.get("community_hub_page") or "/app/community").strip() or "/app/community"
    if "app_language=" not in community_route:
        joiner = "&" if "?" in community_route else "?"
        community_route = f"{community_route}{joiner}app_language={app_language}"
    community_href = escape(community_route)

    plugin_route = str(routes.get("public_plugin_catalog_page") or "/app/plugins").strip() or "/app/plugins"
    if "app_language=" not in plugin_route:
        joiner = "&" if "?" in plugin_route else "?"
        plugin_route = f"{plugin_route}{joiner}app_language={app_language}"
    plugin_href = escape(plugin_route)

    tool_items = "".join(
        f'<li><strong>{escape(str(item.get("name") or item.get("tool_id") or "tool"))}</strong>: {escape(str(item.get("description") or item.get("title") or "MCP/public SDK tool"))}</li>'
        for item in tools[:6]
    )
    if not tool_items:
        tool_items = '<li>No public SDK tools projected yet.</li>'

    resource_items = "".join(
        f'<li><strong>{escape(str(item.get("resource_id") or item.get("name") or "resource"))}</strong>: {escape(str(item.get("description") or item.get("title") or "MCP/public SDK resource"))}</li>'
        for item in resources[:6]
    )
    if not resource_items:
        resource_items = '<li>No public SDK resources projected yet.</li>'

    entrypoint_cards = "".join(
        f"""
        <article class=\"entry-card\">
          <h2>{escape(str(label).replace("_", " ").title())}</h2>
          <p class=\"entrypoint\">{escape(str(value))}</p>
        </article>
        """
        for label, value in list((payload.get("public_sdk_entrypoints") or {}).items())
    )
    if not entrypoint_cards:
        entrypoint_cards = """
        <article class=\"entry-card empty\">
          <h2>No public SDK entrypoints projected yet</h2>
          <p class=\"entrypoint\">Public SDK entrypoints will appear here once they are projected into the catalog.</p>
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
      .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
      .entry-card, .list-card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .entrypoint {{ word-break: break-word; color: #93c5fd; }}
      .detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
      ul {{ margin: 0; padding-left: 18px; color: #cbd5e1; }}
    </style>
  </head>
  <body>
    <main role=\"main\" aria-labelledby=\"public-sdk-title\">
      <header>
        <a class=\"top-link\" href=\"{raw_catalog_href}\">Open raw SDK catalog</a>
        <a class=\"top-link\" href=\"{ecosystem_href}\">Open ecosystem catalog</a>
        <a class=\"top-link\" href=\"{community_href}\">Open community hub</a>
        <a class=\"top-link\" href=\"{plugin_href}\">Open public plugins</a>
        <h1 id=\"public-sdk-title\">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class=\"summary-grid\" aria-label=\"Public SDK entrypoints\">{entrypoint_cards}</section>
      <section class=\"detail-grid\" aria-label=\"Public SDK tools and resources\">
        <article class=\"list-card\">
          <h2>Public SDK tools</h2>
          <ul>{tool_items}</ul>
        </article>
        <article class=\"list-card\">
          <h2>Public SDK resources</h2>
          <ul>{resource_items}</ul>
        </article>
      </section>
    </main>
  </body>
</html>
"""


__all__ = ["render_public_sdk_catalog_html"]
