"""
generator.py

Generates a list of Steps from a feature name.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.devtools.claude_task_generator.feature_registry import get_feature


@dataclass
class Step:
    id: str          # e.g. "Step180"
    name: str        # e.g. "Execution Diff Data Model"
    description: str
    files: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.id} {self.name}"


# Step decomposition rule names (used as descriptions)
_STEP_RULES = [
    "Core Logic",
    "Engine Integration",
    "Interface / CLI",
    "Output Formatting",
    "Tests",
]


def _make_step_id(base_number: int, index: int) -> str:
    return f"Step{base_number + index}"


def generate_steps(feature_name: str, base_number: int = 180) -> list[Step]:
    """Return a list of Steps for the given feature.

    Steps are derived from the feature registry's step list.
    Falls back to the default 5-step decomposition if no custom list exists.

    Args:
        feature_name: Name of the feature (must be registered).
        base_number:  Starting step number (default 180).

    Returns:
        Ordered list of Step objects.
    """
    feature = get_feature(feature_name)
    step_names: list[str] = feature.get("steps") or _STEP_RULES
    layer: str = feature.get("layer", "engine")
    goal: str = feature.get("goal", "")

    steps: list[Step] = []
    for idx, name in enumerate(step_names):
        step = Step(
            id=_make_step_id(base_number, idx),
            name=name,
            description=f"{goal} - {name}",
            files=[],  # populated by file_mapper
        )
        steps.append(step)

    return steps
