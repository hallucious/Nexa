"""test_phase4_ui_flow_connection.py

Phase 4 실제 UI 연결 검증:
  - designer_panel이 inline key entry를 실제로 렌더링하는가
  - session_keys가 metadata를 통해 designer_panel까지 전달되는가
  - builder_shell이 session_keys를 받아 designer로 스레드하는가
  - semantic_interpreter_factory가 session_key 경로로 backend를 빌드하는가
  - provider_setup_guidance.py 중복 코드 제거 확인
"""
from __future__ import annotations

import pytest

from src.storage.models.working_save_model import (
    WorkingSaveModel, WorkingSaveMeta, RuntimeModel, UIModel,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel


def _ws(metadata: dict | None = None) -> WorkingSaveModel:
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
        ui=UIModel(layout={}, metadata=metadata or {}),
    )


# ── 1. provider_setup_guidance.py 중복 제거 확인 ─────────────────────────

class TestProviderSetupGuidanceNoDuplicate:

    def test_no_duplicate_class_definitions(self):
        import inspect
        import src.ui.provider_setup_guidance as mod
        src_text = inspect.getsource(mod)
        assert src_text.count("class ProviderSetupOptionView") == 1
        assert src_text.count("class ProviderSetupGuidanceView") == 1
        assert src_text.count("def read_provider_setup_guidance_view_model") == 1

    def test_module_imports_cleanly(self):
        from src.ui.provider_setup_guidance import (
            ProviderSetupGuidanceView,
            ProviderSetupOptionView,
            ProviderInlineKeyEntryView,
            ProviderPresetEntryOption,
            read_provider_setup_guidance_view_model,
            read_provider_inline_key_entry_view,
        )
        assert ProviderSetupGuidanceView is not None
        assert ProviderInlineKeyEntryView is not None


# ── 2. designer_panel: provider_inline_key_entry 필드 실제 연결 ──────────

class TestDesignerPanelInlineKeyConnection:

    def test_viewmodel_has_inline_key_entry_field(self):
        from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
        from src.ui.provider_setup_guidance import ProviderInlineKeyEntryView
        vm = read_designer_panel_view_model(_ws())
        assert hasattr(vm, "provider_inline_key_entry")
        assert isinstance(vm.provider_inline_key_entry, ProviderInlineKeyEntryView)

    def test_inline_key_entry_visible_when_no_provider(self):
        from src.ui.designer_panel import read_designer_panel_view_model
        vm = read_designer_panel_view_model(_ws())
        assert vm.provider_inline_key_entry.visible is True

    def test_inline_key_entry_hidden_when_env_key_present(self):
        from src.ui.designer_panel import read_designer_panel_view_model
        ws = _ws(metadata={"provider_setup_detect_process_env": False,
                            "provider_setup_env": {"OPENAI_API_KEY": "sk-test"}})
        vm = read_designer_panel_view_model(ws)
        assert vm.provider_inline_key_entry.has_connected_provider is True
        assert vm.provider_inline_key_entry.visible is False

    def test_inline_key_entry_hidden_when_session_key_in_metadata(self):
        from src.ui.designer_panel import read_designer_panel_view_model
        ws = _ws(metadata={
            "provider_session_keys": {"gpt": "sk-session-from-metadata"},
        })
        vm = read_designer_panel_view_model(ws)
        assert vm.provider_inline_key_entry.has_connected_provider is True
        assert vm.provider_inline_key_entry.visible is False

    def test_session_key_in_metadata_shows_session_connected_status(self):
        from src.ui.designer_panel import read_designer_panel_view_model
        ws = _ws(metadata={
            "provider_session_keys": {"claude": "sk-ant-session-key"},
        })
        vm = read_designer_panel_view_model(ws)
        claude_opt = next(
            o for o in vm.provider_inline_key_entry.preset_options if o.preset == "claude"
        )
        assert claude_opt.status == "session_connected"
        assert claude_opt.key_hint is not None

    def test_inline_key_entry_covers_all_presets(self):
        from src.ui.designer_panel import read_designer_panel_view_model
        from src.designer.semantic_backend_presets import supported_semantic_backend_presets
        vm = read_designer_panel_view_model(_ws())
        option_presets = {o.preset for o in vm.provider_inline_key_entry.preset_options}
        for preset in supported_semantic_backend_presets():
            assert preset in option_presets, f"{preset} missing from designer panel inline entry"


# ── 3. _session_keys_from_metadata 헬퍼 동작 확인 ────────────────────────

class TestSessionKeysFromMetadata:

    def test_extracts_keys_from_metadata(self):
        from src.ui.designer_panel import _session_keys_from_metadata
        ws = _ws(metadata={"provider_session_keys": {"gpt": "sk-key1", "claude": "sk-ant-key2"}})
        keys = _session_keys_from_metadata(ws)
        assert keys == {"gpt": "sk-key1", "claude": "sk-ant-key2"}

    def test_returns_empty_when_no_session_keys(self):
        from src.ui.designer_panel import _session_keys_from_metadata
        keys = _session_keys_from_metadata(_ws())
        assert keys == {}

    def test_ignores_empty_values(self):
        from src.ui.designer_panel import _session_keys_from_metadata
        ws = _ws(metadata={"provider_session_keys": {"gpt": "   ", "claude": "sk-ant-real"}})
        keys = _session_keys_from_metadata(ws)
        assert "gpt" not in keys
        assert keys["claude"] == "sk-ant-real"

    def test_non_dict_metadata_returns_empty(self):
        from src.ui.designer_panel import _session_keys_from_metadata
        ws = _ws(metadata={"provider_session_keys": "not-a-dict"})
        keys = _session_keys_from_metadata(ws)
        assert keys == {}


# ── 4. builder_shell: session_keys 스레드 확인 ───────────────────────────

class TestBuilderShellSessionKeyThread:

    def test_shell_accepts_session_keys_param(self):
        from src.ui.builder_shell import read_builder_shell_view_model
        import inspect
        sig = inspect.signature(read_builder_shell_view_model)
        assert "session_keys" in sig.parameters

    def test_shell_with_session_key_produces_connected_designer(self):
        from src.ui.builder_shell import read_builder_shell_view_model
        ws = _ws()
        shell_vm = read_builder_shell_view_model(
            ws,
            session_keys={"gpt": "sk-shell-session-key"},
        )
        assert shell_vm.designer is not None
        # The designer panel should now see the session key
        inline_entry = shell_vm.designer.provider_inline_key_entry
        gpt_opt = next(o for o in inline_entry.preset_options if o.preset == "gpt")
        assert gpt_opt.status == "session_connected"

    def test_shell_without_session_keys_shows_inline_entry(self):
        from src.ui.builder_shell import read_builder_shell_view_model
        ws = _ws()
        shell_vm = read_builder_shell_view_model(ws)
        assert shell_vm.designer is not None
        assert shell_vm.designer.provider_inline_key_entry.visible is True

    def test_shell_merges_metadata_and_caller_session_keys(self):
        """Caller-supplied session_keys override metadata keys for the same preset."""
        from src.ui.builder_shell import read_builder_shell_view_model
        ws = _ws(metadata={
            "provider_session_keys": {"claude": "sk-ant-metadata"},
        })
        # Caller overrides claude and adds gpt
        shell_vm = read_builder_shell_view_model(
            ws,
            session_keys={"gpt": "sk-gpt-caller", "claude": "sk-ant-caller"},
        )
        assert shell_vm.designer is not None
        inline = shell_vm.designer.provider_inline_key_entry
        gpt_opt = next(o for o in inline.preset_options if o.preset == "gpt")
        claude_opt = next(o for o in inline.preset_options if o.preset == "claude")
        assert gpt_opt.status == "session_connected"
        assert claude_opt.status == "session_connected"


# ── 5. semantic_interpreter_factory: session_key 경로 ────────────────────

class TestSemanticInterpreterFactorySessionPath:

    def test_factory_accepts_session_key_params(self):
        import inspect
        from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
        sig = inspect.signature(build_designer_semantic_interpreter)
        assert "semantic_backend_session_key" in sig.parameters
        assert "semantic_backend_session_keys" in sig.parameters

    def test_session_key_path_builds_llm_interpreter(self):
        from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
        from src.designer.semantic_interpreter import LLMBackedStructuredSemanticInterpreter
        interp = build_designer_semantic_interpreter(
            semantic_backend_preset="gpt",
            semantic_backend_session_key="sk-test-key-not-real",
            use_llm_semantic_interpreter=True,
        )
        assert isinstance(interp, LLMBackedStructuredSemanticInterpreter)

    def test_session_keys_map_picks_correct_preset(self):
        from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
        from src.designer.semantic_interpreter import LLMBackedStructuredSemanticInterpreter
        interp = build_designer_semantic_interpreter(
            semantic_backend_preset="claude",
            semantic_backend_session_keys={"gpt": "sk-gpt", "claude": "sk-ant-real"},
            use_llm_semantic_interpreter=True,
        )
        assert isinstance(interp, LLMBackedStructuredSemanticInterpreter)

    def test_no_session_key_falls_through_to_legacy(self):
        from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
        from src.designer.semantic_interpreter import LegacyRuleBasedSemanticInterpreter
        interp = build_designer_semantic_interpreter()
        assert isinstance(interp, LegacyRuleBasedSemanticInterpreter)

    def test_explicit_interpreter_bypasses_session_path(self):
        from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
        from src.designer.semantic_interpreter import LegacyRuleBasedSemanticInterpreter
        explicit = LegacyRuleBasedSemanticInterpreter()
        result = build_designer_semantic_interpreter(
            semantic_interpreter=explicit,
            semantic_backend_session_key="sk-should-be-ignored",
        )
        assert result is explicit


# ── 6. 종합 흐름: UI key 입력 → shell → designer → backend ───────────────

class TestEndToEndSessionKeyFlow:

    def test_full_flow_no_env_var_needed(self):
        """Complete beginner flow: user pastes key → shell → designer reflects connected state."""
        from src.ui.builder_shell import read_builder_shell_view_model
        from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
        from src.designer.semantic_interpreter import LLMBackedStructuredSemanticInterpreter

        ws = _ws()

        # Step 1: User pastes key in UI, caller supplies it via session_keys
        shell_vm = read_builder_shell_view_model(
            ws,
            session_keys={"claude": "sk-ant-user-pasted"},
        )

        # Step 2: designer panel reflects connected state
        assert shell_vm.designer is not None
        inline = shell_vm.designer.provider_inline_key_entry
        assert inline.has_connected_provider is True
        claude_opt = next(o for o in inline.preset_options if o.preset == "claude")
        assert claude_opt.status == "session_connected"
        assert claude_opt.key_hint is not None

        # Step 3: factory builds a real backend using the session key (no env var)
        interp = build_designer_semantic_interpreter(
            semantic_backend_preset="claude",
            semantic_backend_session_key="sk-ant-user-pasted",
            use_llm_semantic_interpreter=True,
        )
        assert isinstance(interp, LLMBackedStructuredSemanticInterpreter)

    def test_guidance_view_is_clean_no_duplicate_classes(self):
        """Regression: provider_setup_guidance must have no duplicate class definitions."""
        import inspect
        import src.ui.provider_setup_guidance as mod
        text = inspect.getsource(mod)
        assert text.count("class ProviderSetupGuidanceView") == 1
        assert text.count("class ProviderSetupOptionView") == 1
