"""
regression_reason_codes.py

Contract-level catalog for regression reason codes.

This is the single authoritative source-of-truth for regression reason code
constants and category-specific validation sets.

All consumers (detector, formatter, policy) must import from here.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Node regression reason codes
# ---------------------------------------------------------------------------

NODE_SUCCESS_TO_FAILURE = "NODE_SUCCESS_TO_FAILURE"
NODE_SUCCESS_TO_SKIPPED = "NODE_SUCCESS_TO_SKIPPED"
NODE_REMOVED_SUCCESS = "NODE_REMOVED_SUCCESS"

# ---------------------------------------------------------------------------
# Artifact regression reason codes
# ---------------------------------------------------------------------------

ARTIFACT_REMOVED = "ARTIFACT_REMOVED"
ARTIFACT_HASH_CHANGED = "ARTIFACT_HASH_CHANGED"

# ---------------------------------------------------------------------------
# Context regression reason codes
# ---------------------------------------------------------------------------

CONTEXT_KEY_REMOVED = "CONTEXT_KEY_REMOVED"
CONTEXT_VALUE_CHANGED = "CONTEXT_VALUE_CHANGED"

# ---------------------------------------------------------------------------
# Category-specific valid reason code sets
# ---------------------------------------------------------------------------

VALID_NODE_REASON_CODES = frozenset({
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
    NODE_REMOVED_SUCCESS,
})

VALID_ARTIFACT_REASON_CODES = frozenset({
    ARTIFACT_REMOVED,
    ARTIFACT_HASH_CHANGED,
})

VALID_CONTEXT_REASON_CODES = frozenset({
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
})

# All valid reason codes (union of all categories)
VALID_REASON_CODES = frozenset({
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
    NODE_REMOVED_SUCCESS,
    ARTIFACT_REMOVED,
    ARTIFACT_HASH_CHANGED,
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
})
