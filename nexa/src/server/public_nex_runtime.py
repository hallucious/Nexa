from __future__ import annotations

from html import escape
from typing import Any, Mapping

from src.server.public_runtime_utils import escaped_app_route


def render_public_nex_format_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    routes = dict(payload.get("routes") or {})
    format_boundary = dict(payload.get("format_boundary") or {})
    role_boundaries = dict(payload.get("role_boundaries") or {})
    working = dict(role_boundaries.get("working_save") or {})
    commit = dict(role_boundaries.get("commit_snapshot") or {})
    return f"""<!doctype html>
<html lang="{escape(app_language)}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Public .nex format</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; padding: 2rem; background: #0b1020; color: #e5e7eb; }}
      main {{ max-width: 1040px; margin: 0 auto; }}
      .links a {{ color: #93c5fd; margin-right: 1rem; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }}
      .card {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 1rem; }}
      code {{ color: #bfdbfe; }}
    </style>
  </head>
  <body>
    <main>
      <h1>Public .nex format</h1>
      <p>Inspect the public .nex format boundary, role rules, and operation posture from a product-facing page.</p>
      <p class="links"><a href="{escaped_app_route(routes, 'public_hub_page', '/app/public', app_language=app_language)}">Public hub</a><a href="{escaped_app_route(routes, 'public_integration_hub_page', '/app/integrations', app_language=app_language)}">Integration hub</a><a href="{escaped_app_route(routes, 'ecosystem_catalog_page', '/app/ecosystem', app_language=app_language)}">Ecosystem</a><a href="{escaped_app_route(routes, 'public_mcp_catalog_page', '/app/mcp', app_language=app_language)}">MCP</a><a href="{escaped_app_route(routes, 'provider_catalog_page', '/app/providers', app_language=app_language)}">Providers</a><a href="{escape(str(routes.get('format') or '/api/formats/public-nex'))}">Raw format route</a></p>
      <section class="grid">
        <article class="card"><h2>Format family</h2><p><code>{escape(str(format_boundary.get('format_family') or '.nex'))}</code></p><p><strong>Roles:</strong> {escape(', '.join(format_boundary.get('supported_roles') or []))}</p></article>
        <article class="card"><h2>Working save</h2><p><strong>Identity:</strong> <code>{escape(str(working.get('identity_field') or 'working_save_id'))}</code></p><p><strong>Commit posture:</strong> {escape(str(working.get('commit_boundary_posture') or ''))}</p></article>
        <article class="card"><h2>Commit snapshot</h2><p><strong>Identity:</strong> <code>{escape(str(commit.get('identity_field') or 'commit_id'))}</code></p><p><strong>Editor posture:</strong> {escape(str(commit.get('editor_continuity_posture') or ''))}</p></article>
      </section>
    </main>
  </body>
</html>
"""
