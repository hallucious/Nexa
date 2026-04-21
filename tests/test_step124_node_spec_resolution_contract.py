
import json

import pytest

from src.platform.execution_config_hash import generate_execution_config_id
from src.engine.node_spec_resolver import NodeSpecResolver
from src.platform.execution_config_registry import (
    ExecutionConfigNotFoundError,
    ExecutionConfigRefError,
    ExecutionConfigRegistry,
    ExecutionConfigVersionError,
)


def _write_config(root, payload):
    config_dir = root / payload["config_id"]
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / f'{payload["version"]}.json'
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_step124_nodespec_resolution_success(tmp_path):
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

    node_spec = {
        "node_id": "n1",
        "execution_config_ref": payload["config_id"],
    }

    config = resolver.resolve(node_spec)

    assert config.config_id == payload["config_id"]
    assert config.version == "1.0.0"


def test_step124_nodespec_resolution_missing_config(tmp_path):
    registry = ExecutionConfigRegistry(root=tmp_path / "registry" / "execution_configs")
    resolver = NodeSpecResolver(registry)

    node_spec = {
        "node_id": "n1",
        "execution_config_ref": "ec_missing",
    }

    with pytest.raises(ExecutionConfigNotFoundError):
        resolver.resolve(node_spec)


def test_step124_nodespec_invalid_ref_format(tmp_path):
    registry = ExecutionConfigRegistry(root=tmp_path / "registry" / "execution_configs")
    resolver = NodeSpecResolver(registry)

    node_spec = {
        "node_id": "n1",
        "execution_config_ref": "invalid_format",
    }

    with pytest.raises(ExecutionConfigRefError):
        resolver.resolve(node_spec)


def test_step124_nodespec_resolution_ambiguous_version_requires_exact_ref(tmp_path):
    registry_root = tmp_path / "registry" / "execution_configs"

    payload = {
        "prompt_ref": "prompt.summarize",
        "provider_ref": "openai.gpt",
        "output_mapping": {"answer": "answer"},
    }

    payload1 = dict(payload, version="1.0.0")
    payload1["config_id"] = generate_execution_config_id(payload1)
    _write_config(registry_root, payload1)

    payload2 = dict(payload, version="2.0.0")
    payload2["config_id"] = payload1["config_id"]
    _write_config(registry_root, payload2)

    registry = ExecutionConfigRegistry(root=registry_root)
    resolver = NodeSpecResolver(registry)

    node_spec = {
        "node_id": "n1",
        "execution_config_ref": payload1["config_id"],
    }

    with pytest.raises(ExecutionConfigVersionError):
        resolver.resolve(node_spec)
