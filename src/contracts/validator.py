
from __future__ import annotations

from typing import Dict

from src.contracts.registry import ContractRegistry


class ContractValidator:
    """Validates gate outputs against registered contract."""

    @staticmethod
    def validate_gate_outputs(gate_id: str, outputs: Dict[str, str]) -> None:
        spec = ContractRegistry.gate_spec(gate_id)
        spec.validate(outputs)
