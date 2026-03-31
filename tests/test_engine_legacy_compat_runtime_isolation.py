from __future__ import annotations

from pathlib import Path


def test_engine_cli_keeps_legacy_nex_execution_inline_but_moves_preparation_into_runtime_adapter() -> None:
    cli_source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    assert "def _run_legacy_nex(" in cli_source
    assert "def _run_legacy_nex_bundle(" in cli_source
    assert "from src.engine.cli_legacy_nex_runtime import" not in cli_source
    assert "from src.contracts.nex_loader import" not in cli_source
    assert "from src.contracts.nex_engine_adapter import" not in cli_source
    assert "from src.contracts.nex_bundle_loader import" not in cli_source
    assert "def _deserialize_legacy_nex(" not in cli_source
    assert "def _load_legacy_nex_file(" not in cli_source
    assert "def _load_legacy_nex_bundle(" not in cli_source
    assert "def _build_engine_from_legacy_nex(" not in cli_source
    assert "from src.circuit.loader import" not in cli_source
    assert "from src.platform.external_loader import" not in cli_source
    assert "from src.circuit.runtime_adapter import (" in cli_source
    assert "open_legacy_nex_bundle" in cli_source
    assert "prepare_engine_from_legacy_nex_bundle" in cli_source
    assert "load_engine_from_legacy_nex_path" in cli_source


def test_legacy_nex_plugin_validation_moves_to_external_loader() -> None:
    cli_source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    loader_source = Path("src/platform/external_loader.py").read_text(encoding="utf-8")
    assert "def _resolve_legacy_plugins(" not in cli_source
    assert "def validate_legacy_nex_plugins(" in loader_source


def test_legacy_nex_loader_and_bundle_handling_move_to_circuit_loader() -> None:
    loader_source = Path("src/circuit/loader.py").read_text(encoding="utf-8")
    assert "class LegacyNexBundle:" in loader_source
    assert "def load_legacy_nex_file(" in loader_source
    assert "def load_legacy_nex_bundle(" in loader_source


def test_legacy_nex_runtime_preparation_moves_to_runtime_adapter() -> None:
    adapter_source = Path("src/circuit/runtime_adapter.py").read_text(encoding="utf-8")
    assert "def build_engine_from_legacy_nex(" in adapter_source
    assert "def load_engine_from_legacy_nex_path(" in adapter_source
    assert "def open_legacy_nex_bundle(" in adapter_source
    assert "def prepare_engine_from_legacy_nex_bundle(" in adapter_source


def test_legacy_nex_runtime_module_is_physically_absent() -> None:
    assert not Path("src/engine/cli_legacy_nex_runtime.py").exists()
