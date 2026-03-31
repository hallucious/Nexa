from __future__ import annotations

from pathlib import Path



def test_engine_cli_is_now_a_thin_compatibility_wrapper() -> None:
    cli_source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    compat_source = Path("src/engine/cli_compat_runner.py").read_text(encoding="utf-8")
    assert "from src.engine.cli_compat_runner import (" in cli_source
    assert "def build_parser(" not in cli_source
    assert "def _parse_node_ids(" not in cli_source
    assert "def _render_policy_output(" not in cli_source
    assert "def run_engine(" not in cli_source
    assert "def main(" not in cli_source
    assert "def build_parser(" in compat_source
    assert "def _parse_node_ids(" in compat_source
    assert "def _render_policy_output(" in compat_source
    assert "def run_engine(" in compat_source
    assert "def main(" in compat_source
    assert "run_legacy_nex" in compat_source
    assert "run_legacy_nex_bundle" in compat_source



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



def test_legacy_nex_runtime_preparation_and_summary_move_to_runtime_adapter() -> None:
    adapter_source = Path("src/circuit/runtime_adapter.py").read_text(encoding="utf-8")
    assert "def build_engine_from_legacy_nex(" in adapter_source
    assert "def load_engine_from_legacy_nex_path(" in adapter_source
    assert "def open_legacy_nex_bundle(" in adapter_source
    assert "def prepare_engine_from_legacy_nex_bundle(" in adapter_source
    assert "def build_legacy_trace_summary(" in adapter_source
    assert "def execute_legacy_nex_summary(" in adapter_source
    assert "def execute_legacy_nex_bundle_summary(" in adapter_source



def test_engine_cli_policy_and_summary_dispatch_move_to_savefile_runtime() -> None:
    cli_source = Path("src/engine/cli.py").read_text(encoding="utf-8")
    runtime_source = Path("src/cli/savefile_runtime.py").read_text(encoding="utf-8")
    assert "def _build_regression_result_from_summaries(" not in cli_source
    assert "def _load_policy_overrides(" not in cli_source
    assert "def _apply_baseline_policy(" not in cli_source
    assert "def _write_or_print_payload(" not in cli_source
    assert "def run_nex(" not in runtime_source
    assert "def run_legacy_nex(" in runtime_source
    assert "def run_legacy_nex_bundle(" in runtime_source
    assert "def run_savefile_nex(" in runtime_source
    assert "def write_or_print_payload(" in runtime_source



def test_legacy_nex_runtime_module_is_physically_absent() -> None:
    assert not Path("src/engine/cli_legacy_nex_runtime.py").exists()
