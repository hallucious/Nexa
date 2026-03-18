"""
tests/test_claude_task_generator.py

Tests for the claude_task_generator devtool (nexa task command).

Covers:
1. generator — Step creation and structure
2. file_mapper — file inference
3. prompt_builder — prompt content
4. CLI commands — generate and prompt
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from src.devtools.claude_task_generator.generator import Step, generate_steps
from src.devtools.claude_task_generator.file_mapper import map_files, apply_file_map, _to_snake
from src.devtools.claude_task_generator.prompt_builder import build_prompt
from src.devtools.claude_task_generator.feature_registry import (
    FEATURES, get_feature, list_features,
)
from src.devtools.claude_task_generator.cli import cmd_generate, cmd_prompt


# ---------------------------------------------------------------------------
# 1. Generator
# ---------------------------------------------------------------------------

def test_generate_steps_returns_list():
    steps = generate_steps("execution_diff")
    assert isinstance(steps, list)
    assert len(steps) > 0


def test_generate_steps_all_are_step_instances():
    steps = generate_steps("execution_diff")
    for s in steps:
        assert isinstance(s, Step)


def test_generate_steps_have_ids():
    steps = generate_steps("execution_diff", base_number=180)
    assert steps[0].id == "Step180"
    assert steps[1].id == "Step181"


def test_generate_steps_have_names():
    steps = generate_steps("execution_diff")
    names = [s.name for s in steps]
    assert all(isinstance(n, str) and len(n) > 0 for n in names)


def test_generate_steps_have_descriptions():
    steps = generate_steps("execution_diff")
    for s in steps:
        assert isinstance(s.description, str)
        assert len(s.description) > 0


def test_generate_steps_unknown_feature_raises():
    with pytest.raises(KeyError):
        generate_steps("nonexistent_feature_xyz")


def test_step_str_representation():
    s = Step(id="Step180", name="My Step", description="desc")
    assert str(s) == "Step180 My Step"


def test_generate_steps_base_number_offset():
    steps = generate_steps("execution_diff", base_number=200)
    assert steps[0].id == "Step200"
    assert steps[-1].id == f"Step{200 + len(steps) - 1}"


def test_generate_steps_count_matches_feature_registry():
    feature = get_feature("execution_diff")
    expected_count = len(feature.get("steps", []))
    steps = generate_steps("execution_diff")
    assert len(steps) == expected_count


# ---------------------------------------------------------------------------
# 2. File Mapper
# ---------------------------------------------------------------------------

def test_to_snake_basic():
    assert _to_snake("Execution Diff Engine") == "execution_diff_engine"


def test_to_snake_with_special_chars():
    assert _to_snake("Interface / CLI") == "interface_cli"


def test_map_files_returns_list():
    step = Step(id="Step180", name="Execution Diff Engine", description="d")
    files = map_files(step, layer="engine")
    assert isinstance(files, list)
    assert len(files) == 2


def test_map_files_engine_layer():
    step = Step(id="Step180", name="Execution Diff Engine", description="d")
    files = map_files(step, layer="engine")
    assert any("src/engine" in f for f in files)
    assert any("tests/" in f for f in files)


def test_map_files_cli_layer():
    step = Step(id="Step182", name="Execution Diff CLI", description="d")
    files = map_files(step, layer="cli")
    assert any("src/cli" in f for f in files)


def test_map_files_infer_cli_from_name():
    step = Step(id="Step182", name="Execution Diff CLI", description="d")
    files = map_files(step)  # no explicit layer
    assert any("src/cli" in f for f in files)


def test_apply_file_map_populates_steps():
    steps = generate_steps("execution_diff")
    result = apply_file_map(steps, layer="engine")
    for s in result:
        assert len(s.files) > 0


# ---------------------------------------------------------------------------
# 3. Prompt Builder
# ---------------------------------------------------------------------------

def test_build_prompt_returns_string():
    step = Step(id="Step180", name="Execution Diff Data Model", description="Compare runs",
                files=["src/engine/execution_diff_model.py", "tests/test_execution_diff_model.py"])
    prompt = build_prompt(step)
    assert isinstance(prompt, str)


def test_build_prompt_contains_project_section():
    step = Step(id="Step180", name="Data Model", description="desc")
    prompt = build_prompt(step)
    assert "PROJECT" in prompt
    assert "Nexa" in prompt


def test_build_prompt_contains_step_id():
    step = Step(id="Step180", name="Data Model", description="desc")
    prompt = build_prompt(step)
    assert "Step180" in prompt


def test_build_prompt_contains_step_name():
    step = Step(id="Step180", name="Execution Diff Data Model", description="desc")
    prompt = build_prompt(step)
    assert "Execution Diff Data Model" in prompt


def test_build_prompt_contains_files():
    step = Step(id="Step180", name="Model", description="desc",
                files=["src/engine/my_module.py", "tests/test_my_module.py"])
    prompt = build_prompt(step)
    assert "src/engine/my_module.py" in prompt
    assert "tests/test_my_module.py" in prompt


def test_build_prompt_contains_test_requirements():
    step = Step(id="Step180", name="Model", description="desc")
    prompt = build_prompt(step)
    assert "TEST REQUIREMENTS" in prompt


def test_build_prompt_contains_architecture_invariants():
    step = Step(id="Step180", name="Model", description="desc")
    prompt = build_prompt(step)
    assert "Node is the only execution unit" in prompt


def test_build_prompt_is_deterministic():
    step = Step(id="Step180", name="Model", description="desc")
    assert build_prompt(step) == build_prompt(step)


# ---------------------------------------------------------------------------
# 4. Feature Registry
# ---------------------------------------------------------------------------

def test_list_features_returns_list():
    features = list_features()
    assert isinstance(features, list)
    assert len(features) > 0


def test_execution_diff_is_registered():
    assert "execution_diff" in FEATURES


def test_get_feature_known():
    f = get_feature("execution_diff")
    assert "layer" in f
    assert "goal" in f


def test_get_feature_unknown_raises():
    with pytest.raises(KeyError):
        get_feature("does_not_exist")


# ---------------------------------------------------------------------------
# 5. CLI cmd_generate
# ---------------------------------------------------------------------------

def test_cmd_generate_known_feature(capsys):
    code = cmd_generate("execution_diff")
    assert code == 0
    out = capsys.readouterr().out
    assert "Feature: execution_diff" in out
    assert "Step180" in out


def test_cmd_generate_lists_all_steps(capsys):
    cmd_generate("execution_diff")
    out = capsys.readouterr().out
    feature = get_feature("execution_diff")
    expected = len(feature["steps"])
    step_lines = [l for l in out.splitlines() if l.startswith("Step")]
    assert len(step_lines) == expected


def test_cmd_generate_unknown_feature_returns_nonzero(capsys):
    code = cmd_generate("totally_unknown_xyz")
    assert code != 0


# ---------------------------------------------------------------------------
# 6. CLI cmd_prompt
# ---------------------------------------------------------------------------

def test_cmd_prompt_by_id(capsys):
    code = cmd_prompt("execution_diff", "Step180")
    assert code == 0
    out = capsys.readouterr().out
    assert "Step180" in out
    assert "PROJECT" in out


def test_cmd_prompt_by_index(capsys):
    code = cmd_prompt("execution_diff", "1")
    assert code == 0
    out = capsys.readouterr().out
    assert "PROJECT" in out


def test_cmd_prompt_unknown_step_returns_nonzero():
    code = cmd_prompt("execution_diff", "StepXXX999")
    assert code != 0


def test_cmd_prompt_unknown_feature_returns_nonzero():
    code = cmd_prompt("nope_feature", "Step180")
    assert code != 0


# ---------------------------------------------------------------------------
# 7. Nexa CLI integration (subprocess)
# ---------------------------------------------------------------------------

def test_nexa_task_generate_subprocess():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "task", "generate", "execution_diff"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Feature: execution_diff" in result.stdout
    assert "Step180" in result.stdout


def test_nexa_task_prompt_subprocess():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "task", "prompt", "execution_diff", "Step180"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "PROJECT" in result.stdout
    assert "Step180" in result.stdout


def test_nexa_task_no_subcommand_returns_nonzero():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "task"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
