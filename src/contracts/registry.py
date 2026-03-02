from __future__ import annotations

from src.contracts.standard_spec import standard_spec


class ContractRegistry:
    """Central access point for contract specs."""

    @staticmethod
    def gate_spec(gate_id: str):
        return standard_spec(gate_id)
