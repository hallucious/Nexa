from __future__ import annotations

from html import escape
from typing import Mapping, Sequence

from src.ui.i18n import normalize_ui_language, ui_text


def render_starter_template_catalog_html(payload: Mapping[str, object]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    catalog = dict(payload.get("catalog") or {})
    routes = dict(payload.get("routes") or {})
    title = escape(str(catalog.get("title") or ui_text("template_gallery.title", app_language=app_language, fallback_text="Starter workflows")))
    subtitle = escape(str(catalog.get("subtitle") or ui_text("template_gallery.subtitle", app_language=app_language, fallback_text="Choose a starter workflow to begin faster.")))
    empty_title = escape(ui_text("server.templates.empty_title", app_language=app_language, fallback_text="No starter templates projected yet"))
    empty_summary = escape(ui_text("server.templates.empty_summary", app_language=app_language, fallback_text="Starter templates will appear here once the catalog is available."))
    raw_catalog_href = escape(str(routes.get("self") or "/api/templates/starter-circuits"))
    library_href = escape(str(routes.get("app_library") or "/app/library"))
    cards_html = ""
    for template in list(payload.get("templates") or ()):
        template_map = dict(template or {})
        template_id = escape(str(template_map.get("template_id") or "template"))
        display_name = escape(str(template_map.get("display_name") or template_map.get("template_id") or ui_text("server.templates.template_fallback", app_language=app_language, fallback_text="Starter template")))
        category = escape(str(template_map.get("category") or template_map.get("category_id") or ""))
        summary = escape(str(template_map.get("summary") or ""))
        detail_href = escape(str((template_map.get("routes") or {}).get("self") or raw_catalog_href))
        cards_html += f"""
        <article class="template-card" aria-labelledby="template-title-{template_id}">
          <div class="template-card-head">
            <h2 id="template-title-{template_id}">{display_name}</h2>
            <span class="category-badge">{category}</span>
          </div>
          <p>{summary}</p>
          <div class="actions">
            <a class="action-link secondary" href="{detail_href}">{escape(ui_text("server.templates.open_raw_template", app_language=app_language, fallback_text="Open raw template"))}</a>
          </div>
        </article>
        """
    if not cards_html:
        cards_html = f"""
        <article class="template-card empty">
          <h2>{empty_title}</h2>
          <p>{empty_summary}</p>
        </article>
        """
    return f"""<!doctype html>
<html lang="{app_language}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0b1220; color: #e5e7eb; }}
      main {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ margin: 0; color: #cbd5e1; }}
      .template-grid {{ display: grid; gap: 16px; }}
      .template-card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .template-card-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
      .category-badge {{ background: #1f2937; border: 1px solid #475569; border-radius: 999px; padding: 4px 10px; font-size: 0.875rem; }}
      .actions {{ margin-top: 16px; }}
      .action-link {{ display: inline-block; padding: 10px 14px; border-radius: 10px; background: #2563eb; color: white; text-decoration: none; }}
      .action-link.secondary {{ background: #1f2937; border: 1px solid #475569; margin-right: 8px; }}
      a.top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
    </style>
  </head>
  <body>
    <main role="main" aria-labelledby="starter-template-title">
      <header aria-labelledby="starter-template-title">
        <a class="top-link" href="{raw_catalog_href}">{escape(ui_text("server.templates.open_raw_catalog", app_language=app_language, fallback_text="Open raw starter-template catalog"))}</a>
        <a class="top-link" href="{library_href}">{escape(ui_text("server.templates.open_library", app_language=app_language, fallback_text="Open workflow library"))}</a>
        <h1 id="starter-template-title">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class="template-grid" aria-label="{escape(ui_text("server.templates.catalog_aria", app_language=app_language, fallback_text="Starter template catalog"))}">{cards_html}</section>
    </main>
  </body>
</html>"""


__all__ = ["render_starter_template_catalog_html"]
