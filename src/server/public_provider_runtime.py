from __future__ import annotations

from html import escape
from typing import Any, Mapping


def render_public_provider_catalog_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    routes = dict(payload.get("routes") or {})
    providers = list(payload.get("providers") or ())
    title = escape(str(payload.get("title") or "Provider catalog"))
    subtitle = escape(str(payload.get("subtitle") or "Browse managed provider options that power the public/community Nexa surface."))
    def norm(route_key: str, fallback: str) -> str:
        route = str(routes.get(route_key) or fallback).strip() or fallback
        if "app_language=" not in route:
            route += ("&" if "?" in route else "?") + f"app_language={app_language}"
        return escape(route)
    cards = ''.join(
        f"<article class=\"card\"><h2>{escape(str(dict(p).get('display_name') or dict(p).get('provider_key') or 'provider'))}</h2><p><strong>Family:</strong> {escape(str(dict(p).get('provider_family') or ''))}</p><p><strong>Scope:</strong> {escape(str(dict(p).get('recommended_scope') or 'workspace'))}</p><p><strong>Managed:</strong> {escape(str(dict(p).get('managed_supported')))}</p></article>"
        for p in providers
    ) or '<article class="card"><h2>No providers projected yet</h2></article>'
    return f"""<!doctype html>
<html lang="{escape(app_language)}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; padding: 2rem; background: #0b1020; color: #e5e7eb; }}
      main {{ max-width: 1040px; margin: 0 auto; }}
      .links a {{ color: #93c5fd; margin-right: 1rem; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }}
      .card {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 1rem; }}
    </style>
  </head>
  <body>
    <main>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      <p class="links"><a href="{norm('ecosystem_catalog_page','/app/ecosystem')}">Ecosystem</a><a href="{norm('community_hub_page','/app/community')}">Community</a><a href="{norm('public_sdk_catalog_page','/app/sdk')}">SDK</a><a href="{norm('public_mcp_catalog_page','/app/mcp')}">MCP</a><a href="{escape(str(routes.get('self') or '/api/providers/catalog'))}">Raw provider catalog</a></p>
      <section class="grid">{cards}</section>
    </main>
  </body>
</html>
"""
