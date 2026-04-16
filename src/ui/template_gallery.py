from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.designer.proposal_flow import list_starter_circuit_templates
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class TemplateGalleryItemView:
    template_id: str
    display_name: str
    category: str
    summary: str
    designer_request_text: str
    template_ref: str | None = None
    lookup_aliases: tuple[str, ...] = ()
    identity: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)
    compatibility: dict[str, Any] = field(default_factory=dict)
    action_type: str = "create_circuit_from_template"
    action_label: str | None = None


@dataclass(frozen=True)
class TemplateGalleryViewModel:
    gallery_status: str = "hidden"
    visible: bool = False
    title: str | None = None
    subtitle: str | None = None
    templates: list[TemplateGalleryItemView] = field(default_factory=list)
    category_count: int = 0
    explanation: str | None = None


def _unwrap(source):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _is_empty_working_save(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None) -> bool:
    source = _unwrap(source)
    return isinstance(source, WorkingSaveModel) and not source.circuit.nodes and not source.circuit.edges


def read_template_gallery_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    explanation: str | None = None,
    app_language: str | None = None,
) -> TemplateGalleryViewModel:
    source_unwrapped = _unwrap(source)
    app_language = app_language or ui_language_from_sources(source_unwrapped)
    if not _is_empty_working_save(source_unwrapped):
        return TemplateGalleryViewModel()

    templates = [
        TemplateGalleryItemView(
            template_id=template.template_id,
            display_name=ui_text(f"template_gallery.template.{template.template_id}.name", app_language=app_language, fallback_text=template.display_name),
            category=ui_text(f"template_gallery.category.{template.category}", app_language=app_language, fallback_text=template.category.replace("_", " ")),
            summary=ui_text(f"template_gallery.template.{template.template_id}.summary", app_language=app_language, fallback_text=template.summary),
            designer_request_text=template.designer_request_text,
            template_ref=template.template_ref,
            lookup_aliases=template.lookup_aliases,
            identity={**template.canonical_identity, "lookup_mode": "template_id_or_template_ref"},
            provenance={
                "family": template.provenance_family,
                "source": template.provenance_source,
                "curation_status": template.curation_status,
            },
            compatibility={
                "family": template.compatibility_family,
                "apply_behavior": template.apply_behavior,
                "supported_entry_surfaces": list(template.supported_entry_surfaces),
                "supported_storage_roles": list(template.supported_storage_roles),
            },
            action_label=ui_text("template_gallery.action.use_template", app_language=app_language, fallback_text="Use template"),
        )
        for template in list_starter_circuit_templates()
    ]
    category_count = len({template.category for template in templates})
    return TemplateGalleryViewModel(
        gallery_status="ready",
        visible=True,
        title=ui_text("template_gallery.title", app_language=app_language, fallback_text="Starter workflows"),
        subtitle=ui_text("template_gallery.subtitle", app_language=app_language, fallback_text="Choose a starter workflow to begin faster."),
        templates=templates,
        category_count=category_count,
        explanation=explanation,
    )


__all__ = [
    "TemplateGalleryItemView",
    "TemplateGalleryViewModel",
    "read_template_gallery_view_model",
]
