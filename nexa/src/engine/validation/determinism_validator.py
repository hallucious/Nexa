from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..fingerprint import compute_fingerprint
from ..model import EngineStructure
from .result import ValidationResult, Violation, Severity

if TYPE_CHECKING:
    from ..engine import Engine


DETERMINISM_RULE_IDS = [
    "DET-001",
    "DET-002",
    "DET-003",
    "DET-004",
    "DET-005",
    "DET-006",
    "DET-007",
]


class DeterminismValidator:
    """Determinism Validation Engine.

    Validates determinism/reproducibility requirements.
    This validator is non-blocking by default (findings are recorded as warnings).
    In strict mode, findings become blocking errors.

    Implemented rules:
    - DET-001: Determinism config presence
    - DET-002: provider_ref presence
    - DET-003: model presence
    - DET-004: temperature presence
    - DET-005: seed presence
    - DET-006: prompt_ref presence
    - DET-007: temperature range validity
    """

    def validate(
        self,
        engine: "Engine",
        *,
        revision_id: str,
        strict_determinism: bool = False,
    ) -> ValidationResult:
        structure: EngineStructure = engine.to_structure()
        fingerprint = compute_fingerprint(structure)

        violations: List[Violation] = []

        # Determine severity based on strict mode
        det_severity = Severity.ERROR if strict_determinism else Severity.WARNING

        # DET-001: Determinism configuration presence
        determinism_config = structure.meta.get("determinism")
        if not determinism_config:
            violations.append(
                Violation(
                    rule_id="DET-001",
                    rule_name="Determinism Missing",
                    severity=det_severity,
                    location_type="engine",
                    location_id=None,
                    message="Engine meta must include 'determinism' configuration.",
                )
            )

        # Node-level determinism checks
        node_specs = structure.meta.get("node_specs", {})

        for node_id in structure.node_ids:
            node_spec = node_specs.get(node_id, {})

            # DET-002: provider_ref presence
            provider_ref = node_spec.get("provider_ref")
            if provider_ref is None:
                violations.append(
                    Violation(
                        rule_id="DET-002",
                        rule_name="Provider Missing",
                        severity=det_severity,
                        location_type="node",
                        location_id=node_id,
                        message=f"Node '{node_id}' must specify 'provider_ref'.",
                    )
                )

            # DET-003: model presence
            model = node_spec.get("model")
            if model is None:
                violations.append(
                    Violation(
                        rule_id="DET-003",
                        rule_name="Model Missing",
                        severity=det_severity,
                        location_type="node",
                        location_id=node_id,
                        message=f"Node '{node_id}' must specify 'model'.",
                    )
                )

            # DET-004: temperature presence
            temperature = node_spec.get("temperature")
            if temperature is None:
                violations.append(
                    Violation(
                        rule_id="DET-004",
                        rule_name="Temperature Missing",
                        severity=det_severity,
                        location_type="node",
                        location_id=node_id,
                        message=f"Node '{node_id}' must specify 'temperature'.",
                    )
                )
            else:
                # DET-007: temperature range validity
                if not isinstance(temperature, (int, float)) or not (
                    0 <= temperature <= 2
                ):
                    violations.append(
                        Violation(
                            rule_id="DET-007",
                            rule_name="Invalid Temperature Range",
                            severity=det_severity,
                            location_type="node",
                            location_id=node_id,
                            message=f"Node '{node_id}' temperature must be between 0 and 2.",
                        )
                    )

            # DET-005: seed presence
            seed = node_spec.get("seed")
            if seed is None:
                violations.append(
                    Violation(
                        rule_id="DET-005",
                        rule_name="Seed Missing",
                        severity=det_severity,
                        location_type="node",
                        location_id=node_id,
                        message=f"Node '{node_id}' must specify 'seed'.",
                    )
                )

            # DET-006: prompt_ref presence
            prompt_ref = node_spec.get("prompt_ref")
            if prompt_ref is None:
                violations.append(
                    Violation(
                        rule_id="DET-006",
                        rule_name="Prompt Missing",
                        severity=det_severity,
                        location_type="node",
                        location_id=node_id,
                        message=f"Node '{node_id}' must specify 'prompt_ref'.",
                    )
                )

        # In strict mode, errors block execution
        # In non-strict mode, even ERROR-severity findings don't block
        if strict_determinism:
            success = not any(v.severity == Severity.ERROR for v in violations)
        else:
            # Non-blocking: always succeed, findings are advisory
            success = True

        return ValidationResult(
            success=success,
            engine_revision=revision_id,
            structural_fingerprint=fingerprint.value,
            applied_rule_ids=list(DETERMINISM_RULE_IDS),
            violations=violations,
        )
