from __future__ import annotations

from pathlib import Path


def test_engine_cli_delegates_legacy_nex_runtime_to_compat_module():
    source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    assert "from src.engine.cli_legacy_nex_runtime import" in source
    assert "from src.contracts.nex_loader import" not in source
    assert "from src.contracts.nex_engine_adapter import" not in source
    assert "from src.contracts.nex_bundle_loader import" not in source
    assert "from src.contracts.nex_serializer import" not in source
    assert "from src.contracts.nex_validator import" not in source
    assert "from src.contracts.nex_plugin_integration import" not in source



def test_legacy_nex_runtime_keeps_execution_boundary_without_writer_surface():
    source = Path("src/engine/cli_legacy_nex_runtime.py").read_text(encoding="utf-8")
    assert "resolve_plugins(" in source
    assert "def run_legacy_nex(" in source
    assert "def run_legacy_nex_bundle(" in source
    assert "def serialize_nex(" not in source
    assert "def save_nex_file(" not in source
    assert "def build_nex_from_engine(" not in source
    assert "from src.contracts.nex_plugin_integration import" not in source
    assert "from src.contracts.nex_loader import" not in source
    assert "from src.contracts.nex_engine_adapter import" not in source
    assert "from src.contracts.nex_bundle_loader import" not in source
    assert "from src.contracts.nex_serializer import" not in source
    assert "from src.contracts.nex_validator import" not in source
