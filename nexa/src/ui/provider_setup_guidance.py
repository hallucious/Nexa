from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from src.designer.semantic_backend_presets import (
    available_semantic_backend_presets,
    available_semantic_backend_presets_with_session,
    resolve_semantic_backend_key,
    semantic_backend_preset_specs,
)
from src.providers.env_diagnostics import ProviderAccessPathType, read_env_setup_status
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


# ── Phase 4: Inline key entry surface (beginner path) ────────────────────
#
# Allows users to connect an AI provider directly in the UI without knowing
# env var names or creating a .env file.  The key lives only for the current
# session and is never written to disk by this layer.


@dataclass(frozen=True)
class ProviderPresetEntryOption:
    """One selectable provider row in the inline key entry UI."""
    preset: str
    display_name: str
    key_placeholder: str        # e.g. "Paste your OpenAI API key"
    key_help_url: str | None    # link to provider's API key page
    status: str                 # "connected" | "not_connected" | "session_connected"
    status_label: str
    key_hint: str | None        # masked key hint if already resolved, else None
    access_path_type: str | None  # ProviderAccessPathType value


@dataclass(frozen=True)
class ProviderInlineKeyEntryView:
    """UI view model for inline API key entry.

    Renders a provider picker + key input form that lets a beginner connect
    to an AI provider without any knowledge of environment variables or .env
    files.  The submitted key is forwarded to build_semantic_backend_from_key()
    for the current session.

    visible=True means the UI should show the inline entry form.
    When at least one provider is already connected (via session or env), the
    form remains available but is collapsed by default (visible=False).
    """
    visible: bool = False
    preset_options: tuple[ProviderPresetEntryOption, ...] = ()
    active_preset: str | None = None
    submit_label: str = "Connect"
    cancel_label: str = "Cancel"
    privacy_note: str = ""
    has_connected_provider: bool = False
    connected_count: int = 0


_KEY_HELP_URLS: dict[str, str] = {
    "gpt": "https://platform.openai.com/api-keys",
    "claude": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
    "perplexity": "https://www.perplexity.ai/settings/api",
}

_KEY_PLACEHOLDERS: dict[str, str] = {
    "gpt": "sk-...",
    "claude": "sk-ant-...",
    "gemini": "AIza...",
    "perplexity": "pplx-...",
}


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


def read_provider_inline_key_entry_view(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    session_keys: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
    active_preset: str | None = None,
) -> ProviderInlineKeyEntryView:
    """Build the inline key entry view model.

    This is the Phase 4 beginner-safe provider access surface.
    Users can paste an API key directly in the UI without knowing env var
    names or how to create a .env file.

    Args:
        source:       Current storage source (used for language preference).
        session_keys: Mapping of preset → raw API key already provided this
                      session via the UI.  These keys have already been
                      validated at the UI layer before storage here.
        env:          Optional env override for checking existing env vars.
        active_preset: Which preset the key entry form is open for, or None.
    """
    source_unwrapped = _unwrap(source)
    app_language = ui_language_from_sources(source_unwrapped)
    session_keys = session_keys or {}
    specs = semantic_backend_preset_specs()

    preset_options: list[ProviderPresetEntryOption] = []
    connected_count = 0

    for spec in specs.values():
        resolution = resolve_semantic_backend_key(
            spec.preset,
            session_key=session_keys.get(spec.preset),
            env=env,
        )
        resolved = resolution.access_path.resolved
        path_type = resolution.access_path.path_type if resolved else None

        if resolved:
            connected_count += 1
            if path_type == ProviderAccessPathType.SESSION_INJECTED:
                status = "session_connected"
                status_label = ui_text(
                    "provider_setup.option.status.connected",
                    app_language=app_language,
                    fallback_text="Connected (this session)",
                )
            else:
                status = "connected"
                status_label = ui_text(
                    "provider_setup.option.status.connected",
                    app_language=app_language,
                    fallback_text="Connected",
                )
        else:
            status = "not_connected"
            status_label = ui_text(
                "provider_setup.option.status.setup_required",
                app_language=app_language,
                fallback_text="Not connected",
            )

        preset_options.append(ProviderPresetEntryOption(
            preset=spec.preset,
            display_name=spec.display_name,
            key_placeholder=_KEY_PLACEHOLDERS.get(spec.preset, "Paste your API key here"),
            key_help_url=_KEY_HELP_URLS.get(spec.preset),
            status=status,
            status_label=status_label,
            key_hint=resolution.access_path.key_hint,
            access_path_type=path_type,
        ))

    # Show the inline entry form when no provider is connected at all
    visible = connected_count == 0

    privacy_note = (
        "Your API key is used only for this session and is not stored on disk."
        if app_language == "en"
        else "API 키는 이 세션에서만 사용되며 디스크에 저장되지 않습니다."
    )

    return ProviderInlineKeyEntryView(
        visible=visible,
        preset_options=tuple(preset_options),
        active_preset=active_preset,
        submit_label=ui_text(
            "provider_setup.action.open_guide",
            app_language=app_language,
            fallback_text="Connect",
        ),
        cancel_label="Cancel" if app_language == "en" else "취소",
        privacy_note=privacy_note,
        has_connected_provider=connected_count > 0,
        connected_count=connected_count,
    )


__all__ = [
    "ProviderInlineKeyEntryView",
    "ProviderPresetEntryOption",
    "ProviderSetupGuidanceView",
    "ProviderSetupOptionView",
    "read_provider_inline_key_entry_view",
    "read_provider_setup_guidance_view_model",
]
