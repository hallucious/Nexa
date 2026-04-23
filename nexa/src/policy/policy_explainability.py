from typing import Dict, List

from src.contracts.policy_result_contract import (  # noqa: F401 — re-exported for callers
    ExplainabilityResult,
    PolicyDecision,
)

# ExplainabilityResult and PolicyDecision are defined in
# src.contracts.policy_result_contract and re-exported here for backward
# compatibility. New code should import from src.contracts.policy_result_contract.


def build_explainability(decision: PolicyDecision) -> ExplainabilityResult:
    structural: List[str] = []
    semantic: List[str] = []

    for reason in decision.reasons:
        if "signal" in reason:
            semantic.append(reason)
        else:
            structural.append(reason)

    if decision.status == "PASS":
        summary = "PASS: no issues"
    else:
        summary = f"{decision.status}: {len(structural)} structural issues, {len(semantic)} semantic issues"

    verification_contracts: List[str] = []
    for item in decision.details.get("verification_contracts", []):
        contract = item.get("contract_resolution") or {}
        verification_contracts.append(
            f"{item.get('target_type')}:{item.get('target_id')} severity={item.get('severity')} source={contract.get('resolution_source')} fallback={contract.get('fallback_severity')} detail={contract.get('detail_severity')} codes={','.join(contract.get('detail_reason_codes', []))}"
        )

    return ExplainabilityResult(
        status=decision.status,
        summary=summary,
        categories={
            "structural": structural,
            "semantic": semantic,
        },
        verification_contracts=verification_contracts,
    )
