from __future__ import annotations

from html import escape
from typing import Any, Mapping

from src.server.public_runtime_utils import escaped_app_route


def render_public_integration_hub_html(
    payload: Mapping[str, Any],
    *,
    app_language: str | None = None,
) -> str:
    app_language = str(app_language or payload.get("app_language") or "en").strip() or "en"
    routes = dict(payload.get("routes") or {})
    title = escape(str(payload.get("title") or "Public integration hub"))
    subtitle = escape(
        str(
            payload.get("subtitle")
            or "Browse SDK, plugins, MCP, providers, and public .nex surfaces from one integration-focused page."
        )
    )
    cards: list[str] = []
    for entry in list(payload.get("cards") or ()):
        item = dict(entry or {})
        href = escaped_app_route(
            routes,
            str(item.get("route_key") or "public_sdk_catalog_page"),
            str(item.get("fallback") or "/app/sdk"),
            app_language=app_language,
        )
        cards.append(
            "<article class=\"card\">"
            f"<h2>{escape(str(item.get('title') or 'Integration surface'))}</h2>"
            f"<p>{escape(str(item.get('summary') or ''))}</p>"
            f"<p><a href=\"{href}\">Open page</a></p>"
            "</article>"
        )
    cards_html = "".join(cards) or '<article class="card"><h2>No integration surfaces projected yet</h2></article>'
    public_href = escaped_app_route(routes, "public_hub_page", "/app/public", app_language=app_language)
    ecosystem_href = escaped_app_route(routes, "public_ecosystem_catalog_page", "/app/ecosystem", app_language=app_language)
    community_href = escaped_app_route(routes, "community_hub_page", "/app/community", app_language=app_language)
    return f"""<!doctype html>
<html lang=\"{escape(app_language)}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
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
      <p class=\"links\"><a href=\"{public_href}\">Public hub</a><a href=\"{ecosystem_href}\">Ecosystem</a><a href=\"{community_href}\">Community</a></p>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      <section class=\"grid\">{cards_html}</section>
    </main>
  </body>
</html>"""


__all__ = ["render_public_integration_hub_html"]
