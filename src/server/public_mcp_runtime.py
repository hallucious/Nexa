from __future__ import annotations

from html import escape
from typing import Any, Mapping


def render_public_mcp_catalog_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    manifest = dict(payload.get("manifest") or {})
    host_bridge = dict(payload.get("host_bridge") or {})
    routes = dict(payload.get("routes") or {})
    title = escape(str(payload.get("title") or "Public MCP surface"))
    subtitle = escape(str(payload.get("subtitle") or "Inspect the public MCP manifest and host bridge from one product-facing page."))
    ecosystem_route = str(routes.get("ecosystem_catalog_page") or "/app/ecosystem").strip() or "/app/ecosystem"
    if "app_language=" not in ecosystem_route:
        ecosystem_route += ("&" if "?" in ecosystem_route else "?") + f"app_language={app_language}"
    community_route = str(routes.get("community_hub_page") or "/app/community").strip() or "/app/community"
    if "app_language=" not in community_route:
        community_route += ("&" if "?" in community_route else "?") + f"app_language={app_language}"
    public_nex_route = str(routes.get("public_nex_format_page") or "/app/public-nex").strip() or "/app/public-nex"
    if "app_language=" not in public_nex_route:
        public_nex_route += ("&" if "?" in public_nex_route else "?") + f"app_language={app_language}"
    provider_route = str(routes.get("provider_catalog_page") or "/app/providers").strip() or "/app/providers"
    if "app_language=" not in provider_route:
        provider_route += ("&" if "?" in provider_route else "?") + f"app_language={app_language}"
    manifest_server = dict(manifest.get("server") or {})
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
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }}
      .card {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 1rem; }}
      code {{ color: #bfdbfe; }}
    </style>
  </head>
  <body>
    <main>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      <p class="links"><a href="{escape(ecosystem_route)}">Ecosystem</a><a href="{escape(community_route)}">Community</a><a href="{escape(public_nex_route)}">Public .nex</a><a href="{escape(provider_route)}">Providers</a></p>
      <section class="grid">
        <article class="card">
          <h2>Manifest</h2>
          <p><strong>Server:</strong> <code>{escape(str(manifest_server.get('name') or 'nexa-public'))}</code></p>
          <p><strong>Tools:</strong> {escape(str(payload.get('tool_count') or 0))}</p>
          <p><strong>Resources:</strong> {escape(str(payload.get('resource_count') or 0))}</p>
          <p><a href="{escape(str(routes.get('manifest') or '/api/integrations/public-mcp/manifest'))}">Open raw manifest route</a></p>
        </article>
        <article class="card">
          <h2>Host bridge</h2>
          <p><strong>Binding:</strong> <code>{escape(str(host_bridge.get('framework_binding_class') or 'FrameworkRouteBindings'))}</code></p>
          <p><a href="{escape(str(routes.get('host_bridge') or '/api/integrations/public-mcp/host-bridge'))}">Open raw host-bridge route</a></p>
        </article>
      </section>
    </main>
  </body>
</html>
"""
