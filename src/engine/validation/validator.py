from __future__ import annotations

from typing import TYPE_CHECKING

from .result import ValidationResult
from .structural_validator import StructuralValidator

if TYPE_CHECKING:
    from ..engine import Engine


# Backward compatibility: maintain the same APPLIED_RULE_IDS for existing tests
APPLIED_RULE_IDS = ["CH-001", "ENG-001", "ENG-003", "NODE-001"]


class ValidationEngine:
    """Validation Engine Facade (v2 with validation layer split).

    Orchestrates structural and determinism validation.

    By default, this maintains backward compatibility by only running
    structural validation. The determinism validator can be accessed
    separately for post-execution or strict-mode validation.

    Implemented rules (via StructuralValidator):
    - ENG-001: Missing Entry
    - NODE-001: Duplicate node_id
    - ENG-003: Cycle (DAG violation)
    - CH-001: Channel References Missing Node
    """

    def __init__(self):
        self._structural_validator = StructuralValidator()

    def validate(self, engine: "Engine", *, revision_id: str) -> ValidationResult:
        """Run structural validation (blocking).

        This method maintains backward compatibility with existing code
        that expects only structural validation.

        For determinism validation, use validate_determinism() separately.
        """
        return self._structural_validator.validate(engine, revision_id=revision_id)

    def validate_structural(
        self, engine: "Engine", *, revision_id: str
    ) -> ValidationResult:
        """Explicitly run structural validation.

        This is an alias for validate() to make the intent clear.
        """
        return self._structural_validator.validate(engine, revision_id=revision_id)

    def validate_determinism(
        self,
        engine: "Engine",
        *,
        revision_id: str,
        strict_determinism: bool = False,
    ) -> ValidationResult:
        """Run determinism validation.

        Args:
            engine: The engine to validate
            revision_id: The revision identifier
            strict_determinism: If True, determinism violations become blocking errors.
                               If False (default), violations are advisory warnings.

        Returns:
            ValidationResult with determinism findings
        """
        from .determinism_validator import DeterminismValidator

        det_validator = DeterminismValidator()
        return det_validator.validate(
            engine, revision_id=revision_id, strict_determinism=strict_determinism
        )
