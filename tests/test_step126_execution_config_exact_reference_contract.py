
import json
import pytest

from src.platform.execution_config_hash import generate_execution_config_id
from src.engine.node_spec_resolver import NodeSpecResolver, validate_execution_config_ref
from src.platform.execution_config_registry import (
    ExecutionConfigRefError,
    ExecutionConfigRegistry,
)


def _write_config(root, payload):
    config_dir = root / payload["config_id"]
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / f"{payload['version']}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_step126_valid_reference():
    validate_execution_config_ref("ec_abc123")


def test_step126_invalid_reference():
    with pytest.raises(ExecutionConfigRefError):
        validate_execution_config_ref("summarize@1")


def test_step126_reject_version_suffix():
    with pytest.raises(ExecutionConfigRefError):
        validate_execution_config_ref("ec_abc123:1.0.0")


def test_step126_resolver_success(tmp_path):
    registry_root = tmp_path / "registry" / "execution_configs"

    payload = {
        "version": "1.0.0",
        "prompt_ref": "prompt.summarize",
        "provider_ref": "openai.gpt",
        "output_mapping": {"answer": "answer"},
    }

    payload["config_id"] = generate_execution_config_id(payload)
    _write_config(registry_root, payload)

    registry = ExecutionConfigRegistry(root=registry_root)
    resolver = NodeSpecResolver(registry)

    node = {
        "node_id": "n1",
        "execution_config_ref": payload["config_id"],
    }

    config = resolver.resolve(node)

    assert config.config_id == payload["config_id"]
