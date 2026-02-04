from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class GateArtifactSpec:
    """
    Defines required artifact filenames for a gate.
    """
    gate_prefix: str  # e.g. "G1"
    required_files: List[str]

    def validate(self, outputs: Dict[str, str]) -> None:
        missing = [f for f in self.required_files if f not in outputs]
        if missing:
            raise ValueError(
                f"{self.gate_prefix} missing required artifacts: {missing}"
            )


def standard_spec(gate_prefix: str) -> GateArtifactSpec:
    """
    Standard artifact contract for all gates.
    """
    return GateArtifactSpec(
        gate_prefix=gate_prefix,
        required_files=[
            f"{gate_prefix}_DECISION.md",
            f"{gate_prefix}_OUTPUT.json",
            f"{gate_prefix}_META.json",
        ],
    )
