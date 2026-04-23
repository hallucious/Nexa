"""test_phase4_provider_access_path.py

Phase 4 완료 검증 — beginner-safe provider access path.

Review gate 항목:
  - raw 환경변수 지식 없이 시작 가능한가?
  - 에러가 status + 원인 + 다음 행동 포맷으로 표시되는가?
  - UI inline key entry surface가 올바르게 렌더링되는가?
"""
from __future__ import annotations

import pytest


# ── 1. env_diagnostics: ProviderKeyResolution layered path ────────────────

class TestResolveProviderKey:

    def test_session_key_takes_priority_over_env(self):
        from src.providers.env_diagnostics import resolve_provider_key, ProviderAccessPathType
        resolution = resolve_provider_key(
            "gpt",
            ("OPENAI_API_KEY",),
            session_key="sk-test-session-key",
            env={"OPENAI_API_KEY": "sk-env-key"},
        )
        assert resolution.access_path.resolved is True
        assert resolution.access_path.path_type == ProviderAccessPathType.SESSION_INJECTED
        assert resolution.api_key == "sk-test-session-key"
        assert resolution.access_path.key_hint is not None

    def test_env_var_used_when_no_session_key(self):
        from src.providers.env_diagnostics import resolve_provider_key, ProviderAccessPathType
        resolution = resolve_provider_key(
            "gpt",
            ("OPENAI_API_KEY",),
            session_key=None,
            env={"OPENAI_API_KEY": "sk-env-only"},
        )
        assert resolution.access_path.resolved is True
        assert resolution.access_path.path_type == ProviderAccessPathType.ENV_VAR
        assert resolution.api_key == "sk-env-only"

    def test_unavailable_when_no_key_anywhere(self):
        from src.providers.env_diagnostics import resolve_provider_key, ProviderAccessPathType
        resolution = resolve_provider_key(
            "gpt",
            ("OPENAI_API_KEY",),
            session_key=None,
            env={},
        )
        assert resolution.access_path.resolved is False
        assert resolution.access_path.path_type == ProviderAccessPathType.UNAVAILABLE
        assert resolution.api_key is None

    def test_empty_session_key_falls_through(self):
        from src.providers.env_diagnostics import resolve_provider_key, ProviderAccessPathType
        resolution = resolve_provider_key(
            "claude",
            ("ANTHROPIC_API_KEY",),
            session_key="   ",
            env={"ANTHROPIC_API_KEY": "sk-ant-real"},
        )
        assert resolution.access_path.path_type == ProviderAccessPathType.ENV_VAR
        assert resolution.api_key == "sk-ant-real"

    def test_key_hint_is_masked(self):
        from src.providers.env_diagnostics import resolve_provider_key
        resolution = resolve_provider_key(
            "gpt",
            ("OPENAI_API_KEY",),
            session_key="sk-test-1234567890abcd",
            env={},
        )
        hint = resolution.access_path.key_hint
        assert hint is not None
        assert "sk-t" in hint
        assert "abcd" in hint
        assert "1234567890" not in hint   # middle part must be masked

    def test_multiple_env_var_names_first_wins(self):
        from src.providers.env_diagnostics import resolve_provider_key, ProviderAccessPathType
        resolution = resolve_provider_key(
            "gemini",
            ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
            session_key=None,
            env={"GOOGLE_API_KEY": "AIza-google-key"},
        )
        assert resolution.access_path.resolved is True
        assert resolution.access_path.path_type == ProviderAccessPathType.ENV_VAR
        assert resolution.api_key == "AIza-google-key"

    def test_resolution_is_frozen(self):
        from src.providers.env_diagnostics import resolve_provider_key
        resolution = resolve_provider_key("gpt", ("OPENAI_API_KEY",), env={})
        with pytest.raises(Exception):
            resolution.preset = "mutated"  # type: ignore[misc]


# ── 2. semantic_backend_presets: available_with_session ───────────────────

class TestAvailableWithSession:

    def test_session_key_counts_as_available(self):
        from src.designer.semantic_backend_presets import available_semantic_backend_presets_with_session
        available = available_semantic_backend_presets_with_session(
            session_keys={"gpt": "sk-session-key"},
            env={},
        )
        assert "gpt" in available

    def test_env_key_still_works(self):
        from src.designer.semantic_backend_presets import available_semantic_backend_presets_with_session
        available = available_semantic_backend_presets_with_session(
            session_keys={},
            env={"ANTHROPIC_API_KEY": "sk-ant-key"},
        )
        assert "claude" in available

    def test_no_keys_returns_empty(self):
        from src.designer.semantic_backend_presets import available_semantic_backend_presets_with_session
        available = available_semantic_backend_presets_with_session(
            session_keys={},
            env={},
        )
        assert available == ()

    def test_session_and_env_combined(self):
        from src.designer.semantic_backend_presets import available_semantic_backend_presets_with_session
        available = available_semantic_backend_presets_with_session(
            session_keys={"gpt": "sk-gpt-session"},
            env={"ANTHROPIC_API_KEY": "sk-ant-key"},
        )
        assert "gpt" in available
        assert "claude" in available


# ── 3. semantic_backend_presets: resolve_semantic_backend_key ─────────────

class TestResolveSemanticBackendKey:

    def test_resolves_via_session_key(self):
        from src.designer.semantic_backend_presets import resolve_semantic_backend_key
        from src.providers.env_diagnostics import ProviderAccessPathType
        result = resolve_semantic_backend_key("gpt", session_key="sk-direct", env={})
        assert result.access_path.resolved is True
        assert result.access_path.path_type == ProviderAccessPathType.SESSION_INJECTED
        assert result.api_key == "sk-direct"

    def test_resolves_via_env_var(self):
        from src.designer.semantic_backend_presets import resolve_semantic_backend_key
        from src.providers.env_diagnostics import ProviderAccessPathType
        result = resolve_semantic_backend_key(
            "claude", session_key=None, env={"ANTHROPIC_API_KEY": "sk-ant"}
        )
        assert result.access_path.path_type == ProviderAccessPathType.ENV_VAR

    def test_unavailable_without_keys(self):
        from src.designer.semantic_backend_presets import resolve_semantic_backend_key
        from src.providers.env_diagnostics import ProviderAccessPathType
        result = resolve_semantic_backend_key("gemini", session_key=None, env={})
        assert result.access_path.path_type == ProviderAccessPathType.UNAVAILABLE
        assert result.api_key is None

    def test_accepts_alias(self):
        from src.designer.semantic_backend_presets import resolve_semantic_backend_key
        result = resolve_semantic_backend_key("openai", session_key="sk-key", env={})
        assert result.preset == "gpt"   # alias normalized to canonical


# ── 4. build_semantic_backend_from_key: inline key path ───────────────────

class TestBuildSemanticBackendFromKey:

    def test_raises_on_empty_key(self):
        from src.designer.semantic_backend_presets import build_semantic_backend_from_key
        with pytest.raises(ValueError, match="api_key must be non-empty"):
            build_semantic_backend_from_key("gpt", "")

    def test_raises_on_whitespace_key(self):
        from src.designer.semantic_backend_presets import build_semantic_backend_from_key
        with pytest.raises(ValueError):
            build_semantic_backend_from_key("claude", "   ")

    def test_raises_on_unknown_preset(self):
        from src.designer.semantic_backend_presets import build_semantic_backend_from_key
        with pytest.raises(ValueError):
            build_semantic_backend_from_key("unknown_preset", "sk-key")

    def test_returns_generate_text_backend_for_valid_key(self):
        from src.designer.semantic_backend_presets import build_semantic_backend_from_key
        from src.designer.semantic_backend import GenerateTextSemanticBackend
        # No network call is made here; provider is constructed but not invoked
        backend = build_semantic_backend_from_key("gpt", "sk-test-key-that-is-not-real")
        assert isinstance(backend, GenerateTextSemanticBackend)

    def test_all_presets_accept_inline_key(self):
        from src.designer.semantic_backend_presets import (
            build_semantic_backend_from_key,
            supported_semantic_backend_presets,
        )
        from src.designer.semantic_backend import GenerateTextSemanticBackend
        for preset in supported_semantic_backend_presets():
            backend = build_semantic_backend_from_key(preset, f"fake-key-for-{preset}")
            assert isinstance(backend, GenerateTextSemanticBackend), f"failed for {preset}"


# ── 5. provider_setup_guidance: ProviderInlineKeyEntryView ────────────────

class TestProviderInlineKeyEntryView:

    def _ws(self):
        from src.storage.models.working_save_model import (
            WorkingSaveModel, WorkingSaveMeta, RuntimeModel, UIModel,
        )
        from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
        return WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version="1.0.0",
                storage_role="working_save",
                working_save_id="ws-1",
                name="Draft",
            ),
            circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
            resources=ResourcesModel(prompts={}, providers={}, plugins={}),
            state=StateModel(input={}, working={}, memory={}),
            runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
            ui=UIModel(layout={}, metadata={}),
        )

    def test_visible_when_no_provider_connected(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(self._ws(), session_keys={}, env={})
        assert vm.visible is True
        assert vm.has_connected_provider is False
        assert vm.connected_count == 0

    def test_not_visible_when_session_key_present(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(
            self._ws(),
            session_keys={"gpt": "sk-session-key"},
            env={},
        )
        assert vm.visible is False
        assert vm.has_connected_provider is True
        assert vm.connected_count >= 1

    def test_not_visible_when_env_key_present(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(
            self._ws(),
            session_keys={},
            env={"ANTHROPIC_API_KEY": "sk-ant"},
        )
        assert vm.visible is False
        assert vm.has_connected_provider is True

    def test_preset_options_cover_all_presets(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        from src.designer.semantic_backend_presets import supported_semantic_backend_presets
        vm = read_provider_inline_key_entry_view(self._ws(), env={})
        option_presets = {o.preset for o in vm.preset_options}
        for preset in supported_semantic_backend_presets():
            assert preset in option_presets, f"{preset} missing from inline entry options"

    def test_session_connected_status_label(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(
            self._ws(),
            session_keys={"claude": "sk-ant-session"},
            env={},
        )
        claude_option = next(o for o in vm.preset_options if o.preset == "claude")
        assert claude_option.status == "session_connected"
        assert claude_option.key_hint is not None

    def test_not_connected_option_has_no_key_hint(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(self._ws(), env={})
        for option in vm.preset_options:
            assert option.status == "not_connected"
            assert option.key_hint is None

    def test_key_help_urls_present(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(self._ws(), env={})
        for option in vm.preset_options:
            assert option.key_help_url is not None, f"no help URL for {option.preset}"
            assert option.key_help_url.startswith("https://")

    def test_privacy_note_present(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(self._ws(), env={})
        assert vm.privacy_note
        assert "session" in vm.privacy_note.lower() or "세션" in vm.privacy_note

    def test_active_preset_forwarded(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(
            self._ws(), env={}, active_preset="claude"
        )
        assert vm.active_preset == "claude"

    def test_view_is_frozen(self):
        from src.ui.provider_setup_guidance import read_provider_inline_key_entry_view
        vm = read_provider_inline_key_entry_view(self._ws(), env={})
        with pytest.raises(Exception):
            vm.visible = False  # type: ignore[misc]


# ── 6. provider classmethod: from_api_key ─────────────────────────────────

class TestProviderFromApiKey:

    def test_gpt_from_api_key(self):
        from src.providers.gpt_provider import GPTProvider
        p = GPTProvider.from_api_key("sk-test")
        assert p.api_key == "sk-test"

    def test_claude_from_api_key(self):
        from src.providers.claude_provider import ClaudeProvider
        p = ClaudeProvider.from_api_key("sk-ant-test")
        assert p.api_key == "sk-ant-test"

    def test_gemini_from_api_key(self):
        from src.providers.gemini_provider import GeminiProvider
        p = GeminiProvider.from_api_key("AIza-test")
        assert p.api_key == "AIza-test"

    def test_perplexity_from_api_key(self):
        from src.providers.perplexity_provider import PerplexityProvider
        p = PerplexityProvider.from_api_key("pplx-test")
        assert p.api_key == "pplx-test"
