from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.engine.plugin_loader import load_plugins


class NodeSpecError(Exception):
    pass


@dataclass(frozen=True)
class NodeSpecModel:
    node_id: str
    inputs: Dict[str, str] = field(default_factory=dict)
    pre_plugins: List[str] = field(default_factory=list)
    prompt_ref: Optional[str] = None
    provider_ref: Optional[str] = None
    post_plugins: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)
    runtime_config: Dict[str, Any] = field(default_factory=dict)


def _ensure_str_dict(value: Any, field_name: str) -> Dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise NodeSpecError(f"{field_name} must be dict[str, str]")
    out: Dict[str, str] = {}
    for k, v in value.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise NodeSpecError(f"{field_name} must be dict[str, str]")
        out[k] = v
    return out


def _ensure_str_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise NodeSpecError(f"{field_name} must be list[str]")
    out: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise NodeSpecError(f"{field_name} entries must be string")
        out.append(item)
    return out


def validate_node_spec(node: Dict[str, Any]) -> None:
    if not isinstance(node, dict):
        raise NodeSpecError("node must be dict")

    node_id = node.get("id") or node.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise NodeSpecError("node.id/node_id must be non-empty string")

    prompt_value = node.get("prompt")
    prompt_ref = node.get("prompt_ref", prompt_value)
    if prompt_ref is not None and not isinstance(prompt_ref, str):
        raise NodeSpecError("prompt/prompt_ref must be string")

    provider_ref = node.get("provider_ref")
    if provider_ref is not None and not isinstance(provider_ref, str):
        raise NodeSpecError("provider_ref must be string")

    inputs = node.get("inputs")
    if inputs is not None:
        _ensure_str_dict(inputs, "inputs")

    output_mapping = node.get("output_mapping")
    if output_mapping is not None:
        _ensure_str_dict(output_mapping, "output_mapping")

    for field_name in ("pre_plugins", "post_plugins", "validation_rules"):
        values = node.get(field_name)
        if values is not None:
            parsed = _ensure_str_list(values, field_name)
            if field_name in ("pre_plugins", "post_plugins"):
                load_plugins(parsed)

    for field_name in ("policy", "runtime_config"):
        value = node.get(field_name)
        if value is not None and not isinstance(value, dict):
            raise NodeSpecError(f"{field_name} must be dict")

    active_slots = [
        bool(node.get("pre_plugins")),
        bool(prompt_ref),
        bool(provider_ref),
        bool(node.get("post_plugins")),
        bool(node.get("validation_rules")),
    ]
    if not any(active_slots):
        raise NodeSpecError(
            "node must activate at least one slot: pre_plugins, prompt_ref, provider_ref, post_plugins, validation_rules"
        )


def parse_node_spec(node: Dict[str, Any]) -> NodeSpecModel:
    validate_node_spec(node)

    prompt_value = node.get("prompt")
    prompt_ref = node.get("prompt_ref", prompt_value)

    return NodeSpecModel(
        node_id=node.get("node_id") or node.get("id"),
        inputs=_ensure_str_dict(node.get("inputs"), "inputs"),
        pre_plugins=_ensure_str_list(node.get("pre_plugins"), "pre_plugins"),
        prompt_ref=prompt_ref,
        provider_ref=node.get("provider_ref"),
        post_plugins=_ensure_str_list(node.get("post_plugins"), "post_plugins"),
        validation_rules=_ensure_str_list(node.get("validation_rules"), "validation_rules"),
        output_mapping=_ensure_str_dict(node.get("output_mapping"), "output_mapping"),
        policy=dict(node.get("policy") or {}),
        runtime_config=dict(node.get("runtime_config") or {}),
    )
