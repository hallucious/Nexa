from __future__ import annotations

from html import escape
from typing import Mapping

from src.ui.i18n import normalize_ui_language, ui_text


def _template_fallback_name(app_language: str) -> str:
    return ui_text("server.shell.starter_template_fallback", app_language=app_language, fallback_text="starter template")


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
    workspace_href = escape(str(routes.get("workspace_page") or ""))
    cards_html = ""
    for template in list(payload.get("templates") or ()):
        template_map = dict(template or {})
        template_id = escape(str(template_map.get("template_id") or "template"))
        display_name = escape(str(template_map.get("display_name") or template_map.get("template_id") or _template_fallback_name(app_language)))
        category = escape(str(template_map.get("category") or template_map.get("category_id") or ""))
        summary = escape(str(template_map.get("summary") or ""))
        template_routes = dict(template_map.get("routes") or {})
        raw_detail_href = escape(str(template_routes.get("self") or raw_catalog_href))
        workspace_detail_href = escape(str(template_routes.get("app_workspace_detail") or ""))
        primary_href = workspace_detail_href or raw_detail_href
        primary_label = escape(
            ui_text(
                "server.templates.review_in_workspace",
                app_language=app_language,
                fallback_text="Review in workspace",
            )
            if workspace_detail_href
            else ui_text("server.templates.open_raw_template", app_language=app_language, fallback_text="Open raw template")
        )
        secondary_html = ""
        if workspace_detail_href:
            secondary_html = (
                f'<a class="action-link secondary" href="{raw_detail_href}">'
                f'{escape(ui_text("server.templates.open_raw_template", app_language=app_language, fallback_text="Open raw template"))}'
                '</a>'
            )
        cards_html += f"""
        <article class="template-card" aria-labelledby="template-title-{template_id}">
          <div class="template-card-head">
            <h2 id="template-title-{template_id}">{display_name}</h2>
            <span class="category-badge">{category}</span>
          </div>
          <p>{summary}</p>
          <div class="actions">
            <a class="action-link" href="{primary_href}">{primary_label}</a>
            {secondary_html}
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
    workspace_link_html = ""
    if workspace_href:
        workspace_link_html = (
            f'<a class="top-link" href="{workspace_href}">'
            f'{escape(ui_text("server.templates.open_workspace", app_language=app_language, fallback_text="Open workspace"))}'
            '</a>'
        )
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
      .action-link.secondary {{ background: #1f2937; border: 1px solid #475569; margin-left: 8px; }}
      a.top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
    </style>
  </head>
  <body>
    <main role="main" aria-labelledby="starter-template-title">
      <header aria-labelledby="starter-template-title">
        <a class="top-link" href="{raw_catalog_href}">{escape(ui_text("server.templates.open_raw_catalog", app_language=app_language, fallback_text="Open raw starter-template catalog"))}</a>
        <a class="top-link" href="{library_href}">{escape(ui_text("server.templates.open_library", app_language=app_language, fallback_text="Open workflow library"))}</a>
        {workspace_link_html}
        <h1 id="starter-template-title">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class="template-grid" aria-label="{escape(ui_text("server.templates.catalog_aria", app_language=app_language, fallback_text="Starter template catalog"))}">{cards_html}</section>
    </main>
  </body>
</html>"""


def render_starter_template_detail_html(payload: Mapping[str, object]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    template = dict(payload.get("template") or {})
    routes = dict(payload.get("routes") or {})
    display_name = escape(str(template.get("display_name") or template.get("template_id") or _template_fallback_name(app_language)))
    summary = escape(str(template.get("summary") or ""))
    category = escape(str(template.get("category") or template.get("category_id") or ""))
    template_ref = escape(str(template.get("template_ref") or template.get("template_id") or ""))
    request_text = escape(str(template.get("designer_request_text") or ""))
    raw_detail_href = escape(str(routes.get("api_detail") or routes.get("self") or "/api/templates/starter-circuits"))
    workspace_templates_href = escape(str(routes.get("workspace_templates_page") or routes.get("catalog") or "/app/templates/starter-circuits"))
    workspace_href = escape(str(routes.get("workspace_page") or ""))
    apply_href = escape(str(routes.get("workspace_apply_html") or "#"))
    apply_label = escape(ui_text("template_gallery.action.use_template", app_language=app_language, fallback_text="Use template"))
    raw_identity = template.get("identity")
    raw_provenance = template.get("provenance")
    raw_compatibility = template.get("compatibility")
    lookup_aliases = template.get("lookup_aliases") or ()
    detail_items = [
        f"{ui_text('server.templates.template_ref', app_language=app_language, fallback_text='Template ref: {value}', value=template_ref)}",
        f"{ui_text('server.templates.category', app_language=app_language, fallback_text='Category: {value}', value=category)}",
        f"{ui_text('server.templates.apply_behavior', app_language=app_language, fallback_text='Apply behavior: {value}', value=str(dict(raw_compatibility or {}).get('apply_behavior') or 'replace-draft'))}",
        f"{ui_text('server.templates.provenance_family', app_language=app_language, fallback_text='Provenance: {value}', value=str(dict(raw_provenance or {}).get('family') or 'starter-template'))}",
    ]
    if lookup_aliases:
        detail_items.append(ui_text("server.templates.lookup_aliases", app_language=app_language, fallback_text="Lookup aliases: {value}", value=", ".join(str(alias) for alias in lookup_aliases)))
    if request_text:
        detail_items.append(ui_text("server.templates.designer_request", app_language=app_language, fallback_text="Designer request: {value}", value=request_text))
    rendered_detail_items = "".join(f"<li>{escape(item)}</li>" for item in detail_items if str(item).strip())
    workspace_link_html = ""
    if workspace_href:
        workspace_link_html = (
            f'<a class="top-link" href="{workspace_href}">'
            f'{escape(ui_text("server.templates.open_workspace", app_language=app_language, fallback_text="Open workspace"))}'
            '</a>'
        )
    return f"""<!doctype html>
<html lang="{app_language}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{display_name}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0b1220; color: #e5e7eb; }}
      main {{ max-width: 880px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ margin: 0; color: #cbd5e1; }}
      article {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 20px; }}
      .category-badge {{ display: inline-block; margin-bottom: 12px; background: #1f2937; border: 1px solid #475569; border-radius: 999px; padding: 4px 10px; font-size: 0.875rem; }}
      .actions {{ margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; }}
      .action-link, button.action-link {{ display: inline-block; padding: 10px 14px; border-radius: 10px; background: #2563eb; color: white; text-decoration: none; border: none; cursor: pointer; font: inherit; }}
      .action-link.secondary {{ background: #1f2937; border: 1px solid #475569; }}
      a.top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
      ul {{ margin: 16px 0 0; padding-left: 18px; }}
      pre {{ white-space: pre-wrap; word-break: break-word; background: #0f172a; border-radius: 12px; padding: 12px; margin-top: 16px; }}
      form {{ display: inline; }}
    </style>
  </head>
  <body>
    <main role="main" aria-labelledby="starter-template-detail-title">
      <header aria-labelledby="starter-template-detail-title">
        <a class="top-link" href="{workspace_templates_href}">{escape(ui_text("server.templates.back_to_catalog", app_language=app_language, fallback_text="Back to starter templates"))}</a>
        {workspace_link_html}
        <a class="top-link" href="{raw_detail_href}">{escape(ui_text("server.templates.open_raw_template", app_language=app_language, fallback_text="Open raw template"))}</a>
        <h1 id="starter-template-detail-title">{display_name}</h1>
        <p>{summary}</p>
      </header>
      <article>
        <span class="category-badge">{category}</span>
        <ul>{rendered_detail_items}</ul>
        <pre>{request_text}</pre>
        <div class="actions">
          <form method="post" action="{apply_href}">
            <button type="submit" class="action-link">{apply_label}</button>
          </form>
          <a class="action-link secondary" href="{workspace_templates_href}">{escape(ui_text("server.templates.back_to_catalog", app_language=app_language, fallback_text="Back to starter templates"))}</a>
        </div>
      </article>
    </main>
  </body>
</html>"""


__all__ = ["render_starter_template_catalog_html", "render_starter_template_detail_html"]
