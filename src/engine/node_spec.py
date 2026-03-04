
from typing import Dict, Any, List
from src.engine.plugin_loader import load_plugins

class NodeSpecError(Exception):
    pass

def validate_node_spec(node: Dict[str, Any]) -> None:
    if not isinstance(node, dict):
        raise NodeSpecError("node must be dict")

    node_id = node.get("id")
    if not isinstance(node_id, str) or not node_id:
        raise NodeSpecError("node.id must be non-empty string")

    if "prompt" in node and not isinstance(node["prompt"], str):
        raise NodeSpecError("node.prompt must be string")

    for field in ("pre_plugins", "post_plugins"):
        if field in node:
            v = node[field]
            if not isinstance(v, list):
                raise NodeSpecError(f"{field} must be list[str]")

            for x in v:
                if not isinstance(x, str):
                    raise NodeSpecError(f"{field} entries must be string plugin ids")

            # verify plugin ids via loader
            load_plugins(v)
