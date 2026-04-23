from __future__ import annotations

from enum import Enum


class ReasonCode(str, Enum):
    """Canonical reason codes for gate decisions.

    IMPORTANT:
    - Enum values are part of the external contract (persisted into JSON).
    - Do NOT change existing values without a migration plan and test updates.
    """

    OK = "OK"

    # G1
    G1_SELF_CHECK_FAILED = "G1_SELF_CHECK_FAILED"

    # G2
    G2_BASELINE_KEYS_REMOVED = "G2_BASELINE_KEYS_REMOVED"
    G2_SEMANTIC_UNKNOWN_WITH_PROVIDER = "G2_SEMANTIC_UNKNOWN_WITH_PROVIDER"
    G2_SEMANTIC_DRIFT = "G2_SEMANTIC_DRIFT"
    G2_SEMANTIC_VIOLATION = "G2_SEMANTIC_VIOLATION"

    # G3
    G3_PROVIDER_ERROR = "G3_PROVIDER_ERROR"
    G3_FACT_ERROR = "G3_FACT_ERROR"

    # G4
    G4_PREREQ_MISSING = "G4_PREREQ_MISSING"
    G4_SCHEMA_INVALID = "G4_SCHEMA_INVALID"

    # G5
    G5_TIMEOUT = "G5_TIMEOUT"
    G5_TEST_FAILED = "G5_TEST_FAILED"

    # G6
    G6_COUNTERFACTUAL_CONFLICT = "G6_COUNTERFACTUAL_CONFLICT"

    # G7
    G7_PREREQ_MISSING = "G7_PREREQ_MISSING"
