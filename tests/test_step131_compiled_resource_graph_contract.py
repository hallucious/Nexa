from src.engine.compiled_resource_graph import (
    CompiledResourceGraphError,
    compile_execution_config_to_graph,
)


def test_compiled_resource_graph_builds_prompt_provider_plugin_dependencies():
    config = {
        "version": "1.0.0",
        "prompt": {
            "prompt_id": "main",
            "inputs": {"question": "input.question"},
        },
        "provider": {
            "provider_id": "openai",
        },
        "plugins": [
            {
                "plugin_id": "formatter",
                "inputs": {"text": "provider.openai.output"},
            }
        ],
    }

    graph = compile_execution_config_to_graph(config)

    assert set(graph.resources.keys()) == {
        "prompt.main",
        "provider.openai",
        "plugin.formatter",
    }
    assert graph.dependencies["prompt.main"] == set()
    assert graph.dependencies["provider.openai"] == {"prompt.main"}
    assert graph.dependencies["plugin.formatter"] == {"provider.openai"}
    assert graph.dependents["prompt.main"] == {"provider.openai"}
    assert graph.dependents["provider.openai"] == {"plugin.formatter"}
    assert graph.final_candidates == {"plugin.formatter.result"}


def test_compiled_resource_graph_supports_multi_field_plugin_outputs():
    config = {
        "plugins": [
            {
                "plugin_id": "search",
                "inputs": {"query": "input.query"},
                "output_fields": ["results", "score", "metadata"],
            },
            {
                "plugin_id": "rank",
                "inputs": {"score": "plugin.search.score"},
                "output_fields": ["result"],
            },
        ]
    }

    graph = compile_execution_config_to_graph(config)

    assert graph.resources["plugin.search"].writes == {
        "plugin.search.results",
        "plugin.search.score",
        "plugin.search.metadata",
    }
    assert graph.dependencies["plugin.rank"] == {"plugin.search"}
    assert graph.final_candidates == {
        "plugin.search.results",
        "plugin.search.metadata",
        "plugin.rank.result",
    }


def test_compiled_resource_graph_rejects_unresolved_internal_read_key():
    config = {
        "plugins": [
            {
                "plugin_id": "normalize",
                "inputs": {"text": "provider.missing.output"},
            }
        ]
    }

    try:
        compile_execution_config_to_graph(config)
    except CompiledResourceGraphError as exc:
        assert "unresolved input reference" in str(exc)
    else:
        raise AssertionError("expected unresolved input reference error")