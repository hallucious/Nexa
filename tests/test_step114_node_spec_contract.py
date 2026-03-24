"""test_step114 — NodeSpec validation. pre_plugins/post_plugins are rejected."""
import pytest
from src.engine.node_spec import validate_node_spec, NodeSpecError


def test_valid_node_with_prompt_ref():
    validate_node_spec({"id": "n1", "prompt_ref": "prompt.basic"})


def test_valid_node_with_plugins():
    validate_node_spec({"id": "n1", "plugins": ["my_plugin"]})


def test_missing_id():
    with pytest.raises(NodeSpecError):
        validate_node_spec({"prompt_ref": "x"})


def test_invalid_plugins_type():
    with pytest.raises(NodeSpecError):
        validate_node_spec({"id": "n1", "plugins": "bad"})


def test_empty_node_no_active_slot_fails():
    with pytest.raises(NodeSpecError):
        validate_node_spec({"id": "n1"})


def test_pre_plugins_rejected():
    with pytest.raises(NodeSpecError, match="pre_plugins"):
        validate_node_spec({"id": "n1", "pre_plugins": ["p1"]})


def test_post_plugins_rejected():
    with pytest.raises(NodeSpecError, match="post_plugins"):
        validate_node_spec({"id": "n1", "post_plugins": ["p1"]})
