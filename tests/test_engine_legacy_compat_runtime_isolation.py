from __future__ import annotations

from pathlib import Path


def test_engine_cli_keeps_legacy_nex_execution_inline_without_legacy_module():
    source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    assert "def _run_legacy_nex(" in source
    assert "def _run_legacy_nex_bundle(" in source
    assert "from src.engine.cli_legacy_nex_runtime import" not in source
    assert "from src.contracts.nex_loader import" not in source
    assert "from src.contracts.nex_engine_adapter import" not in source
    assert "from src.contracts.nex_bundle_loader import" not in source
    assert "from src.contracts.nex_serializer import" not in source
    assert "from src.contracts.nex_validator import" not in source
    assert "from src.contracts.nex_plugin_integration import" not in source


def test_legacy_nex_plugin_validation_moves_to_external_loader():
    cli_source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    loader_source = Path("src/platform/external_loader.py").read_text(encoding="utf-8")
    assert "def _resolve_legacy_plugins(" not in cli_source
    assert "def validate_legacy_nex_plugins(" in loader_source


def test_legacy_nex_runtime_module_is_physically_absent():
    assert not Path("src/engine/cli_legacy_nex_runtime.py").exists()
