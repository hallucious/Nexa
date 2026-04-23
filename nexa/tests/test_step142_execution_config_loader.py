from src.platform.execution_config_registry import load_execution_configs


def test_execution_config_loader(tmp_path):

    config_file = tmp_path / "test.yaml"

    config_file.write_text(
        """
config_id: qa.answer
prompt_ref: qa.prompt
provider_ref: openai
"""
    )

    registry = load_execution_configs(tmp_path)

    config = registry.get("qa.answer")

    assert config["config_id"] == "qa.answer"