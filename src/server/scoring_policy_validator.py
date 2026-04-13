from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class ScoringPolicyValidationResult:
    is_valid: bool
    normalized_policy: Any
    reason: str | None = None
    used_default: bool = False


_DEFAULT_POLICY_KW = dict(health_weight=0.6, cost_weight=0.3, priority_weight=0.1, latency_weight=0.0, reliability_weight=0.0)


def _policy_cls():
    from src.server.run_auto_recovery_policy import AutoRecoveryScoringPolicy
    return AutoRecoveryScoringPolicy


def _default_policy():
    return _policy_cls()(**_DEFAULT_POLICY_KW)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(policy):
    return policy.normalized()


def validate_scoring_policy(policy: AutoRecoveryScoringPolicy | Mapping[str, Any] | None) -> ScoringPolicyValidationResult:
    if policy is None:
        normalized = _normalize(_default_policy())
        return ScoringPolicyValidationResult(is_valid=True, normalized_policy=normalized, reason='missing_policy_defaulted', used_default=True)

    if isinstance(policy, Mapping):
        candidate = _policy_cls()(
            health_weight=_as_float(policy.get('health_weight', _DEFAULT_POLICY_KW['health_weight']), _DEFAULT_POLICY_KW['health_weight']),
            cost_weight=_as_float(policy.get('cost_weight', _DEFAULT_POLICY_KW['cost_weight']), _DEFAULT_POLICY_KW['cost_weight']),
            priority_weight=_as_float(policy.get('priority_weight', _DEFAULT_POLICY_KW['priority_weight']), _DEFAULT_POLICY_KW['priority_weight']),
            latency_weight=_as_float(policy.get('latency_weight', _DEFAULT_POLICY_KW['latency_weight']), _DEFAULT_POLICY_KW['latency_weight']),
            reliability_weight=_as_float(policy.get('reliability_weight', _DEFAULT_POLICY_KW['reliability_weight']), _DEFAULT_POLICY_KW['reliability_weight']),
        )
    elif policy.__class__.__name__ == "AutoRecoveryScoringPolicy":
        candidate = policy
    else:
        normalized = _normalize(_default_policy())
        return ScoringPolicyValidationResult(is_valid=False, normalized_policy=normalized, reason='unsupported_policy_type', used_default=True)

    weights = [
        float(candidate.health_weight),
        float(candidate.cost_weight),
        float(candidate.priority_weight),
        float(candidate.latency_weight),
        float(candidate.reliability_weight),
    ]
    if any(weight < 0 for weight in weights):
        normalized = _normalize(_default_policy())
        return ScoringPolicyValidationResult(is_valid=False, normalized_policy=normalized, reason='negative_weight', used_default=True)

    if sum(weights) <= 0:
        normalized = _normalize(_default_policy())
        return ScoringPolicyValidationResult(is_valid=False, normalized_policy=normalized, reason='zero_weight_sum', used_default=True)

    normalized = _normalize(candidate)
    return ScoringPolicyValidationResult(is_valid=True, normalized_policy=normalized)
