import pytest

from src.engine.node_spec import NodeSpecError, NodeSpecModel, parse_node_spec, validate_node_spec


def test_step122_parse_node_spec_prompt_only():
    spec = parse_node_spec({
        "node_id": "summarize",
        "prompt_ref": "prompt.summarize.v1",
    })

    assert isinstance(spec, NodeSpecModel)
    assert spec.node_id == "summarize"
    assert spec.prompt_ref == "prompt.summarize.v1"
    assert spec.provider_ref is None
    assert spec.pre_plugins == []
    assert spec.post_plugins == []


def test_step122_parse_node_spec_plugin_only(monkeypatch):
    monkeypatch.setattr("src.engine.node_spec.load_plugins", lambda plugin_ids: [])

    spec = parse_node_spec({
        "node_id": "search",
        "pre_plugins": ["providers.x"],
    })

    assert spec.node_id == "search"
    assert spec.pre_plugins == ["providers.x"]
    assert spec.prompt_ref is None


def test_step122_validate_node_spec_requires_one_active_slot():
    with pytest.raises(NodeSpecError):
        validate_node_spec({
            "node_id": "empty_node",
            "inputs": {"question": "input.question"},
        })
