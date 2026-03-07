from src.engine.node_execution_runtime import NodeExecutionRuntime


def fake_provider(prompt, context):
    return {"answer": "ok", "prompt": prompt}


def test_step123_pipeline_basic(tmp_path):
    runtime = NodeExecutionRuntime(
        provider_execution=fake_provider,
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_test",
        "prompt_ref": "prompt.basic",
        "provider_ref": "fake",
        "pre_plugins": [],
        "post_plugins": [],
        "validation_rules": [],
        "output_mapping": {
            "answer": "answer"
        }
    }

    result = runtime.execute(config, {"question": "test"})

    assert result.output["answer"] == "ok"


def test_step123_pre_plugin(tmp_path):
    def add_field(context):
        return {"added": True}

    runtime = NodeExecutionRuntime(
        provider_execution=fake_provider,
        observability_file=str(tmp_path / "obs.jsonl"),
        plugin_registry={"p1": add_field}
    )

    config = {
        "config_id": "ec_test",
        "pre_plugins": ["p1"],
        "prompt_ref": "prompt.basic",
        "provider_ref": "fake",
        "output_mapping": {"answer": "answer"}
    }

    result = runtime.execute(config, {"x": 1})
    assert result.output["answer"] == "ok"
