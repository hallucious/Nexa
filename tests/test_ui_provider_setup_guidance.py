from __future__ import annotations

from src.providers.env_diagnostics import publish_dotenv_status
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.provider_setup_guidance import read_provider_setup_guidance_view_model


def _empty_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_provider_setup_guidance_visible_when_no_provider_env_is_available(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY", "PPLX_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("NEXA_DOTENV_INSTALLED", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_PATH", raising=False)

    vm = read_provider_setup_guidance_view_model(_empty_working_save())

    assert vm.visible is True
    assert vm.mode == "local_bridge_setup"
    assert vm.available_provider_count == 0
    assert vm.primary_action_target == "provider_setup"
    assert len(vm.options) == 4
    assert vm.options[0].status == "setup_required"
    assert any(".env" in step for step in vm.setup_steps)


def test_provider_setup_guidance_hides_when_provider_env_is_available(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY", "PPLX_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    vm = read_provider_setup_guidance_view_model(_empty_working_save())

    assert vm.visible is False
    assert vm.available_provider_count == 1
    assert any(option.preset == "gpt" and option.status == "connected" for option in vm.options)


def test_provider_setup_guidance_reports_missing_python_dotenv(monkeypatch, tmp_path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY", "PPLX_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    publish_dotenv_status(installed=False, loaded_path=str(dotenv_path))

    vm = read_provider_setup_guidance_view_model(_empty_working_save())

    assert vm.visible is True
    assert "python-dotenv" in (vm.summary or "")
