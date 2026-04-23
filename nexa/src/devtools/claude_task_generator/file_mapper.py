"""
file_mapper.py

Infers modified files for a Step based on its name and layer.
"""
from __future__ import annotations

import re
from typing import List

from src.devtools.claude_task_generator.generator import Step


# Layer → source path prefix
_LAYER_PATHS = {
    "engine":     "src/engine",
    "runtime":    "src/runtime",
    "plugin":     "src/plugins",
    "artifact":   "src/artifacts",
    "trace":      "src/engine",     # trace lives inside engine
    "cli":        "src/cli",
    "validation": "src/engine/validation",
    "contracts":  "src/contracts",
    "platform":   "src/platform",
    "prompts":    "src/platform",
    "providers":  "src/providers",
    "circuit":    "src/circuit",
    "utils":      "src/utils",
}


def _to_snake(name: str) -> str:
    """Convert 'Execution Diff Engine' → 'execution_diff_engine'."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _infer_layer_from_step(step: Step) -> str:
    """Guess the layer from the step name."""
    name_lower = step.name.lower()
    for layer in ("cli", "validation", "artifact", "trace", "plugin", "runtime",
                  "circuit", "contracts", "platform", "prompts", "providers"):
        if layer in name_lower:
            return layer
    return "engine"


def map_files(step: Step, layer: str = "") -> List[str]:
    """Return a list of likely source + test files for a Step.

    Args:
        step:  The Step to map files for.
        layer: Optional layer override (e.g. "engine", "cli").

    Returns:
        List of relative file paths.
    """
    effective_layer = layer or _infer_layer_from_step(step)
    src_prefix = _LAYER_PATHS.get(effective_layer, "src/engine")
    module_name = _to_snake(step.name)

    src_file = f"{src_prefix}/{module_name}.py"
    test_file = f"tests/test_{module_name}.py"

    return [src_file, test_file]


def apply_file_map(steps: list[Step], layer: str = "") -> list[Step]:
    """Populate the files field on each Step in place, then return the list."""
    for step in steps:
        step.files = map_files(step, layer=layer)
    return steps
