from __future__ import annotations

from html import escape
from typing import Any, Mapping

from src.server.public_runtime_utils import escaped_app_route, resolve_app_route
from src.ui.i18n import normalize_ui_language, ui_text


def render_public_community_hub_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
    workspace_id: str | None = None,
) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    catalog = dict(payload.get("catalog") or {})
    routes = dict(payload.get("routes") or {})
    workspace_id = workspace_id or (str(payload.get("workspace_id") or "").strip() or None)
    workspace_query = f"&workspace_id={workspace_id}" if workspace_id else ""
    title = escape(
        str(
            catalog.get("title")
            or ui_text(
                "server.community.title",
                app_language=app_language,
                fallback_text="Community hub",
            )
        )
    )
    subtitle = escape(
        str(
            catalog.get("subtitle")
            or ui_text(
                "server.community.subtitle",
                app_language=app_language,
                fallback_text="Browse remixable starter workflows, public shares, and community-facing capabilities from one place.",
            )
        )
    )
    raw_catalog_href = escape(str(routes.get("self") or "/api/integrations/public-community/catalog"))
    public_hub_href = escaped_app_route(routes, "public_hub_page", "/app/public", app_language=app_language, workspace_id=workspace_id)
    integration_hub_href = escaped_app_route(routes, "public_integration_hub_page", "/app/integrations", app_language=app_language, workspace_id=workspace_id)
    ecosystem_href = escaped_app_route(routes, "public_ecosystem_catalog_page", str(routes.get("public_ecosystem_catalog") or "/api/integrations/public-ecosystem/catalog"), app_language=app_language, workspace_id=workspace_id)
    share_summary_href = escape(resolve_app_route(routes, "public_share_catalog_summary", "/app/public-shares/summary", app_language=app_language, workspace_id=workspace_id))
    workspace_href = ""
    if workspace_id:
        workspace_href = escape(f"/app/workspaces/{workspace_id}?app_language={app_language}")

    cards_html = ""
    for asset in list(payload.get("assets") or ()):
        asset_map = dict(asset or {})
        asset_family = escape(str(asset_map.get("asset_family") or "community-asset"))
        surface_family = escape(str(asset_map.get("surface_family") or ""))
        community_role = escape(str(asset_map.get("community_role") or ""))
        route = str(asset_map.get("app_route") or asset_map.get("route") or "").strip()
        if route.startswith("/app/") and "app_language=" not in route:
            joiner = "&" if "?" in route else "?"
            route = f"{route}{joiner}app_language={app_language}{workspace_query}"
        href = escape(route or raw_catalog_href)
        metric_pairs: list[tuple[str, str]] = []
        if asset_map.get("public_item_count") is not None:
            metric_pairs.append((
                ui_text("server.community.public_items", app_language=app_language, fallback_text="Public items"),
                str(asset_map.get("public_item_count") or 0),
            ))
        if asset_map.get("public_operation_count") is not None:
            metric_pairs.append((
                ui_text("server.community.public_operations", app_language=app_language, fallback_text="Supported operations"),
                str(asset_map.get("public_operation_count") or 0),
            ))
        sample_values = asset_map.get("sample_ids") or asset_map.get("supported_operations") or ()
        sample_text = escape(", ".join(str(item) for item in list(sample_values)[:3]))
        metrics_html = "".join(
            f'<li><strong>{escape(label)}</strong>: {escape(value)}</li>' for label, value in metric_pairs
        )
        if sample_text:
            metrics_html += f'<li><strong>{escape(ui_text("server.community.examples", app_language=app_language, fallback_text="Examples"))}</strong>: {sample_text}</li>'
        cards_html += f"""
        <article class="community-card" aria-labelledby="community-card-{asset_family}">
          <div class="community-card-head">
            <div>
              <h2 id="community-card-{asset_family}">{asset_family}</h2>
              <p class="surface-family">{surface_family}</p>
            </div>
            <span class="family-badge">{surface_family}</span>
          </div>
          <p>{community_role}</p>
          <ul>{metrics_html}</ul>
          <div class="actions">
            <a class="action-link" href="{href}">{escape(ui_text("server.community.open_asset", app_language=app_language, fallback_text="Open surface"))}</a>
          </div>
        </article>
        """
    if not cards_html:
        cards_html = f"""
        <article class="community-card empty">
          <h2>{escape(ui_text("server.community.empty_title", app_language=app_language, fallback_text="No community assets projected yet"))}</h2>
          <p>{escape(ui_text("server.community.empty_summary", app_language=app_language, fallback_text="Community-facing surfaces will appear here once they are projected."))}</p>
        </article>
        """

    workspace_link_html = ""
    if workspace_href:
        workspace_link_html = f'<a class="top-link" href="{workspace_href}">{escape(ui_text("server.community.open_workspace", app_language=app_language, fallback_text="Open workspace"))}</a>'

    return f"""<!doctype html>
<html lang="{app_language}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
      main {{ max-width: 1080px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ color: #cbd5e1; }}
      .top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
      .card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
      .community-card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .community-card.empty {{ grid-column: 1 / -1; }}
      .community-card-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: start; }}
      .surface-family {{ margin: 4px 0 0; font-size: 0.9rem; color: #94a3b8; }}
      .family-badge {{ background: #1e293b; border: 1px solid #475569; border-radius: 999px; padding: 4px 10px; font-size: 0.8rem; }}
      ul {{ padding-left: 18px; color: #cbd5e1; }}
      .actions {{ margin-top: 16px; }}
      .action-link {{ display: inline-block; padding: 10px 14px; border-radius: 10px; background: #2563eb; color: white; text-decoration: none; }}
      .action-link.secondary {{ background: #1f2937; border: 1px solid #475569; margin-left: 8px; }}
    </style>
  </head>
  <body>
    <main role="main" aria-labelledby="public-community-title">
      <header aria-labelledby="public-community-title">
        <a class="top-link" href="{raw_catalog_href}">{escape(ui_text("server.community.open_raw_catalog", app_language=app_language, fallback_text="Open raw community catalog"))}</a>
        <a class="top-link" href="{public_hub_href}">Open public hub</a>
        <a class="top-link" href="{integration_hub_href}">Open integration hub</a>
        <a class="top-link" href="{ecosystem_href}">{escape(ui_text("server.community.open_ecosystem", app_language=app_language, fallback_text="Open ecosystem catalog"))}</a>
        <a class="top-link" href="{share_summary_href}">{escape(ui_text("server.community.open_share_summary", app_language=app_language, fallback_text="Open public share summary"))}</a>
        {workspace_link_html}
        <h1 id="public-community-title">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class="card-grid" aria-label="{escape(ui_text('server.community.aria_catalog', app_language=app_language, fallback_text='Community asset hub'))}">{cards_html}</section>
    </main>
  </body>
</html>"""


__all__ = ["render_public_community_hub_html"]
