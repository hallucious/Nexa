from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class ExternalInputOptionView:
    input_kind: str
    label: str
    summary: str
    action_id: str
    action_target: str
    plugin_id: str
    configured: bool = False


@dataclass(frozen=True)
class ExternalInputGuidanceView:
    visible: bool = False
    title: str | None = None
    summary: str | None = None
    has_configured_input: bool = False
    configured_input_kind: str | None = None
    options: tuple[ExternalInputOptionView, ...] = field(default_factory=tuple)


def _unwrap(source):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source: Any) -> str:
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _ui_metadata(source: Any) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}


def detect_external_input_kind(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
) -> tuple[bool, str | None]:
    source_unwrapped = _unwrap(source)
    if not isinstance(source_unwrapped, WorkingSaveModel):
        return False, None

    metadata = _ui_metadata(source_unwrapped)
    metadata_kind = str(metadata.get("external_input_kind") or "").strip().lower()
    if metadata_kind in {"file", "url"}:
        return True, metadata_kind

    nodes = list(source_unwrapped.circuit.nodes or [])
    plugins = source_unwrapped.resources.plugins if isinstance(source_unwrapped.resources.plugins, Mapping) else {}
    for node in nodes:
        execution = node.get("execution") if isinstance(node, Mapping) else None
        plugin = execution.get("plugin") if isinstance(execution, Mapping) else None
        plugin_id = None
        if isinstance(plugin, Mapping):
            plugin_id = str(plugin.get("plugin_id") or plugin.get("id") or "")
        if isinstance(plugin_id, str) and plugin_id.endswith("file_reader"):
            return True, "file"
        if isinstance(plugin_id, str) and plugin_id.endswith("url_reader"):
            return True, "url"
    for plugin_id in plugins:
        plugin_id_str = str(plugin_id)
        if plugin_id_str.endswith("file_reader"):
            return True, "file"
        if plugin_id_str.endswith("url_reader"):
            return True, "url"
    return False, None


def read_external_input_guidance_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
) -> ExternalInputGuidanceView:
    source_unwrapped = _unwrap(source)
    if _storage_role(source_unwrapped) not in {"working_save", "none"}:
        return ExternalInputGuidanceView()

    app_language = ui_language_from_sources(source_unwrapped)
    has_configured_input, configured_input_kind = detect_external_input_kind(source_unwrapped)

    options = (
        ExternalInputOptionView(
            input_kind="file",
            label=ui_text("external_input.option.file.label", app_language=app_language, fallback_text="Use a file"),
            summary=ui_text(
                "external_input.option.file.summary",
                app_language=app_language,
                fallback_text="Upload a file and read it through the file reader path.",
            ),
            action_id="open_file_input",
            action_target="designer.external_input.file",
            plugin_id="nexa.file_reader",
            configured=configured_input_kind == "file",
        ),
        ExternalInputOptionView(
            input_kind="url",
            label=ui_text("external_input.option.url.label", app_language=app_language, fallback_text="Use a web address"),
            summary=ui_text(
                "external_input.option.url.summary",
                app_language=app_language,
                fallback_text="Enter a web address and read it through the URL reader path.",
            ),
            action_id="enter_url_input",
            action_target="designer.external_input.url",
            plugin_id="nexa.url_reader",
            configured=configured_input_kind == "url",
        ),
    )

    if has_configured_input:
        summary_key = f"external_input.summary.{configured_input_kind}_configured"
        fallback_text = "This workflow already reads from a file." if configured_input_kind == "file" else "This workflow already reads from a web address."
    else:
        summary_key = "external_input.summary.none"
        fallback_text = "You can start from a file or web address, not only pasted text."

    return ExternalInputGuidanceView(
        visible=True,
        title=ui_text("external_input.title", app_language=app_language, fallback_text="Add real data"),
        summary=ui_text(summary_key, app_language=app_language, fallback_text=fallback_text),
        has_configured_input=has_configured_input,
        configured_input_kind=configured_input_kind,
        options=options,
    )


__all__ = [
    "ExternalInputGuidanceView",
    "ExternalInputOptionView",
    "detect_external_input_kind",
    "read_external_input_guidance_view_model",
]
