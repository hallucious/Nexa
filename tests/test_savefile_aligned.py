#!/usr/bin/env python
"""Test script for aligned savefile execution with Nexa architecture.

Tests integration with:
- ProviderRegistry (not duplicate provider execution)
- PluginResult contract
- Working context behavior
- Append-only artifacts
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from src.contracts.savefile_loader import load_savefile_from_path
from src.contracts.savefile_validator import validate_savefile, SavefileValidationError
from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.contracts.savefile_provider_builder import build_provider_registry_from_savefile


def test_5_section_structure():
    """Test that 5-section structure is enforced."""
    demo_path = Path(__file__).parent / "examples" / "investment_demo_v2_complete.nex"
    assert demo_path.exists(), f"Demo file not found: {demo_path}"

    with open(demo_path, encoding="utf-8") as f:
        data = json.load(f)

    required_sections = {"meta", "circuit", "resources", "state", "ui"}
    actual_sections = set(data.keys())

    assert required_sections == actual_sections, (
        f"Section mismatch. missing={required_sections - actual_sections}, "
        f"extra={actual_sections - required_sections}"
    )


def test_provider_registry_integration():
    """Test provider execution goes through ProviderRegistry."""
    demo_path = Path(__file__).parent / "examples" / "investment_demo_v2_complete.nex"
    savefile = load_savefile_from_path(str(demo_path))

    provider_registry = build_provider_registry_from_savefile(savefile)
    provider_list = provider_registry.list_providers()

    assert "test_provider" in provider_list, f"test_provider not registered: {provider_list}"

    provider = provider_registry.resolve("test_provider")
    assert provider is not None


def test_plugin_result_contract():
    """Test plugins conform to PluginResult contract."""
    demo_path = Path(__file__).parent / "examples" / "investment_demo_v2_complete.nex"
    savefile = load_savefile_from_path(str(demo_path))

    sys.path.insert(0, str(Path(__file__).parent / "examples"))

    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)
    trace = executor.execute(savefile, run_id="test-plugin-contract")

    for node_id, result in trace.node_results.items():
        if result.status == "success":
            assert hasattr(result, "artifacts"), f"Node '{node_id}' result missing artifacts"
            assert hasattr(result, "trace"), f"Node '{node_id}' result missing trace"


def test_no_duplicate_execution_paths():
    """Test that there's only one execution path."""
    demo_path = Path(__file__).parent / "examples" / "investment_demo_v2_complete.nex"
    savefile = load_savefile_from_path(str(demo_path))

    sys.path.insert(0, str(Path(__file__).parent / "examples"))

    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)

    assert hasattr(executor, "provider_registry"), "Executor missing provider_registry"
    assert not hasattr(executor, "provider_executor"), "Executor has duplicate provider_executor"


def test_aligned_execution():
    """Test complete aligned execution."""
    demo_path = Path(__file__).parent / "examples" / "investment_demo_v2_complete.nex"

    savefile = load_savefile_from_path(str(demo_path))

    warnings = validate_savefile(savefile)
    assert isinstance(warnings, list)

    sys.path.insert(0, str(Path(__file__).parent / "examples"))

    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)

    trace = executor.execute(savefile, run_id="test-aligned")

    assert trace.status == "success", f"Expected success status, got {trace.status}"

    working = trace.final_state.get("working", {})
    decision = working.get("final_decision")

    assert decision in ("invest", "pass"), f"Invalid decision: {decision}"
