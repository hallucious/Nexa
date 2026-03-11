from src.config.execution_config_registry import ExecutionConfigRegistry


def test_step136_execution_config_registry_basic():
    registry = ExecutionConfigRegistry()

    config = {
        "config_id": "qa.answer",
        "prompt_ref": "qa_prompt",
        "provider_ref": "openai"
    }

    registry.register(config)

    loaded = registry.get("qa.answer")

    assert loaded["config_id"] == "qa.answer"


def test_step136_registry_duplicate_error():
    registry = ExecutionConfigRegistry()

    config = {"config_id": "qa.answer"}

    registry.register(config)

    try:
        registry.register(config)
        assert False
    except ValueError:
        pass