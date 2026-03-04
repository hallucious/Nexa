
import pytest
from src.engine.node_spec import validate_node_spec, NodeSpecError

def test_valid_node():
    node = {
        "id": "n1",
        "prompt": "hello",
        "pre_plugins": [],
        "post_plugins": []
    }
    validate_node_spec(node)

def test_missing_id():
    with pytest.raises(NodeSpecError):
        validate_node_spec({"prompt": "x"})

def test_invalid_plugins_type():
    with pytest.raises(NodeSpecError):
        validate_node_spec({"id": "n1", "pre_plugins": "bad"})
