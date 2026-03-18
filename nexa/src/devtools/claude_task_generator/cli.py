"""
cli.py

CLI interface for claude_task_generator.

Commands:
    generate <feature>   — list Steps for a feature
    prompt <step_id>     — print Claude prompt for a step by ID or index
"""
from __future__ import annotations

import sys


def _resolve_step(steps, step_id: str):
    """Find a step by its id string (e.g. 'Step180') or 1-based index."""
    for s in steps:
        if s.id.lower() == step_id.lower():
            return s
    # Try numeric index
    try:
        idx = int(step_id) - 1
        if 0 <= idx < len(steps):
            return steps[idx]
    except ValueError:
        pass
    return None


def cmd_generate(feature_name: str, base_number: int = 180) -> int:
    """Print step plan for a feature. Returns exit code."""
    from src.devtools.claude_task_generator.generator import generate_steps
    from src.devtools.claude_task_generator.file_mapper import apply_file_map
    from src.devtools.claude_task_generator.feature_registry import get_feature

    try:
        feature = get_feature(feature_name)
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    steps = generate_steps(feature_name, base_number=base_number)
    apply_file_map(steps, layer=feature.get("layer", ""))

    print(f"Feature: {feature_name}")
    print()
    for step in steps:
        print(str(step))

    return 0


def cmd_prompt(feature_name: str, step_id: str, base_number: int = 180) -> int:
    """Print Claude prompt for a step. Returns exit code."""
    from src.devtools.claude_task_generator.generator import generate_steps
    from src.devtools.claude_task_generator.file_mapper import apply_file_map
    from src.devtools.claude_task_generator.prompt_builder import build_prompt
    from src.devtools.claude_task_generator.feature_registry import get_feature

    try:
        feature = get_feature(feature_name)
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    steps = generate_steps(feature_name, base_number=base_number)
    apply_file_map(steps, layer=feature.get("layer", ""))

    step = _resolve_step(steps, step_id)
    if step is None:
        print(f"Error: step {step_id!r} not found for feature {feature_name!r}", file=sys.stderr)
        return 1

    print(build_prompt(step))
    return 0
