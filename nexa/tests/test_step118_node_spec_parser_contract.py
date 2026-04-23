"""test_step118 — NodeSpec parser. pre_plugins/post_plugins are rejected."""
import pytest
from src.engine.node_spec import NodeSpecError, NodeSpecModel, parse_node_spec, validate_node_spec


def test_parse_node_spec_prompt_only():
    spec = parse_node_spec({"node_id": "summarize", "prompt_ref": "prompt.summarize.v1"})
    assert isinstance(spec, NodeSpecModel)
    assert spec.node_id == "summarize"
    assert spec.prompt_ref == "prompt.summarize.v1"
    assert spec.provider_ref is None
    assert spec.plugins == []


def test_parse_node_spec_plugin_only():
    spec = parse_node_spec({"node_id": "search", "plugins": ["providers.x"]})
    assert spec.node_id == "search"
    assert spec.plugins == ["providers.x"]
    assert spec.prompt_ref is None


def test_parse_node_spec_rejects_pre_plugins():
    with pytest.raises(NodeSpecError, match="pre_plugins"):
        parse_node_spec({"node_id": "search", "pre_plugins": ["providers.x"]})


def test_parse_node_spec_rejects_post_plugins():
    with pytest.raises(NodeSpecError, match="post_plugins"):
        parse_node_spec({"node_id": "search", "post_plugins": ["post.x"]})


def test_validate_node_spec_requires_one_active_slot():
    with pytest.raises(NodeSpecError):
        validate_node_spec({"node_id": "empty_node", "inputs": {"q": "input.q"}})
