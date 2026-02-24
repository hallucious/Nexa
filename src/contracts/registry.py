
from __future__ import annotations

from src.pipeline.contracts import standard_spec


class ContractRegistry:
    """Central access point for gate contract specs."""

    @staticmethod
    def gate_spec(gate_id: str):
        return standard_spec(gate_id)
