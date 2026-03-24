
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.engine.execution_config_hash import generate_execution_config_id
from src.platform.execution_config_registry import (
    ExecutionConfigFormatError,
    ExecutionConfigNotFoundError,
    ExecutionConfigRegistry,
    ExecutionConfigVersionError,
    resolve_execution_config,
)


def _write_config(root: Path, payload: dict) -> str:
    config_id = generate_execution_config_id(payload)
    version = payload["version"]
    payload = dict(payload)
    payload["config_id"] = config_id
    path = root / config_id
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{version}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"{config_id}:{version}"


def test_step122_resolve_execution_config_success(tmp_path: Path):
    root = tmp_path / "registry"
    payload = {
        "version": "1.0.0",
        "config_schema_version": "1",
        "prompt_ref": "prompt.basic.v1",
        "provider_ref": "openai.gpt4",
        "validation_rules": [],
        "output_mapping": {},
        "policy": {},
        "runtime_config": {"execution": {"temperature": 0.2}},
    }
    ref = _write_config(root, payload)

    reg = ExecutionConfigRegistry(root=root)
    model = resolve_execution_config(ref, registry=reg)

    assert model.config_id == ref.split(":")[0]
    assert model.version == "1.0.0"
    assert model.prompt_ref == "prompt.basic.v1"
    assert model.provider_ref == "openai.gpt4"


def test_step122_resolve_execution_config_not_found(tmp_path: Path):
    reg = ExecutionConfigRegistry(root=tmp_path / "registry")
    with pytest.raises(ExecutionConfigNotFoundError):
        resolve_execution_config("ec_deadbeef:1.0.0", registry=reg)


def test_step122_resolve_execution_config_missing_version(tmp_path: Path):
    root = tmp_path / "registry"
    payload = {
        "version": "1.0.0",
        "config_schema_version": "1",
        "prompt_ref": "prompt.basic.v1",
    }
    ref = _write_config(root, payload)
    config_id = ref.split(":")[0]

    reg = ExecutionConfigRegistry(root=root)
    with pytest.raises(ExecutionConfigVersionError):
        resolve_execution_config(f"{config_id}:2.0.0", registry=reg)


def test_step122_resolve_execution_config_uses_cache(tmp_path: Path):
    root = tmp_path / "registry"
    payload = {
        "version": "1.0.0",
        "config_schema_version": "1",
        "provider_ref": "openai.gpt4",
    }
    ref = _write_config(root, payload)

    reg = ExecutionConfigRegistry(root=root)
    m1 = resolve_execution_config(ref, registry=reg)
    m2 = resolve_execution_config(ref, registry=reg)

    assert m1 is m2


def test_step122_resolve_execution_config_detects_id_mismatch(tmp_path: Path):
    root = tmp_path / "registry"
    bad_id = "ec_badbad00"
    version = "1.0.0"
    path = root / bad_id
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "config_id": bad_id,
        "version": version,
        "config_schema_version": "1",
        "prompt_ref": "prompt.basic.v1",
    }
    (path / f"{version}.json").write_text(json.dumps(payload), encoding="utf-8")

    reg = ExecutionConfigRegistry(root=root)
    with pytest.raises(ExecutionConfigFormatError):
        resolve_execution_config(f"{bad_id}:{version}", registry=reg)
