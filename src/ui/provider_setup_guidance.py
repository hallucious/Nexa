from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from src.designer.semantic_backend_presets import available_semantic_backend_presets, semantic_backend_preset_specs
from src.providers.env_diagnostics import read_env_setup_status
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class ProviderSetupOptionView:
    preset: str
    display_name: str
    status: str
    status_label: str
    required_keys_label: str
    setup_hint: str


@dataclass(frozen=True)
class ProviderSetupGuidanceView:
    visible: bool = False
    mode: str = "hidden"
    title: str | None = None
    summary: str | None = None
    primary_action_label: str | None = None
    primary_action_target: str | None = None
    available_provider_count: int = 0
    setup_steps: tuple[str, ...] = ()
    options: tuple[ProviderSetupOptionView, ...] = field(default_factory=tuple)


def _unwrap(source):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source) -> str:
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def read_provider_setup_guidance_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    env: Mapping[str, str] | None = None,
) -> ProviderSetupGuidanceView:
    source_unwrapped = _unwrap(source)
    if _storage_role(source_unwrapped) not in {"working_save", "none"}:
        return ProviderSetupGuidanceView()

    app_language = ui_language_from_sources(source_unwrapped)
    available = set(available_semantic_backend_presets(env=env))
    specs = semantic_backend_preset_specs()
    options = tuple(
        ProviderSetupOptionView(
            preset=spec.preset,
            display_name=spec.display_name,
            status=("connected" if spec.preset in available else "setup_required"),
            status_label=ui_text(
                "provider_setup.option.status.connected" if spec.preset in available else "provider_setup.option.status.setup_required",
                app_language=app_language,
                fallback_text=("Connected" if spec.preset in available else "Setup needed"),
            ),
            required_keys_label=", ".join(spec.env_var_names),
            setup_hint=ui_text(
                "provider_setup.option.hint.connected" if spec.preset in available else "provider_setup.option.hint.local_env",
                app_language=app_language,
                fallback_text=("Ready to use" if spec.preset in available else "Add one key to your .env file"),
            ),
        )
        for spec in specs.values()
    )
    available_count = len(available)
    if available_count > 0:
        return ProviderSetupGuidanceView(
            visible=False,
            available_provider_count=available_count,
            options=options,
        )

    env_status = read_env_setup_status()
    if not env_status.dotenv_file_found:
        summary_key = "provider_setup.summary.no_dotenv"
        step_keys = (
            "provider_setup.step.create_dotenv",
            "provider_setup.step.add_one_key",
            "provider_setup.step.rerun",
        )
    elif not env_status.dotenv_installed:
        summary_key = "provider_setup.summary.dotenv_not_installed"
        step_keys = (
            "provider_setup.step.install_dotenv",
            "provider_setup.step.rerun",
        )
    else:
        summary_key = "provider_setup.summary.no_supported_key"
        step_keys = (
            "provider_setup.step.add_one_key",
            "provider_setup.step.rerun",
        )

    return ProviderSetupGuidanceView(
        visible=True,
        mode="local_bridge_setup",
        title=ui_text("provider_setup.title", app_language=app_language, fallback_text="Connect an AI model"),
        summary=ui_text(summary_key, app_language=app_language, fallback_text="Add one AI provider key to continue."),
        primary_action_label=ui_text("provider_setup.action.open_guide", app_language=app_language, fallback_text="Open AI setup guide"),
        primary_action_target="provider_setup",
        available_provider_count=0,
        setup_steps=tuple(ui_text(key, app_language=app_language) for key in step_keys),
        options=options,
    )


__all__ = [
    "ProviderSetupGuidanceView",
    "ProviderSetupOptionView",
    "read_provider_setup_guidance_view_model",
]
