from __future__ import annotations

from pathlib import Path


def test_engine_cli_delegates_legacy_nex_runtime_to_compat_module():
    source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    assert "from src.engine.cli_legacy_nex_runtime import" in source
    assert "from src.contracts.nex_loader import" not in source
    assert "from src.contracts.nex_engine_adapter import" not in source
    assert "from src.contracts.nex_bundle_loader import" not in source
    assert "from src.contracts.nex_plugin_integration import" not in source
