from __future__ import annotations

from src.models.decision_models import GateResult, Decision
from src.pipeline.state import GateId
from src.pipeline.runner import GateContext


def make_pass_gate(message: str):
    def _exec(ctx: GateContext) -> GateResult:
        return GateResult(
            decision=Decision.PASS,
            message=message,
            outputs={},
        )
    return _exec


def make_info_gate(message: str):
    def _exec(ctx: GateContext) -> GateResult:
        return GateResult(
            decision=Decision.PASS,
            message=message,
            outputs={},
        )
    return _exec
