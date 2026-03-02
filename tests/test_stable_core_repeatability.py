"""
DEPRECATED (Legacy Pipeline Repeatability)

This legacy repeatability test is pipeline/runner-based.
It is replaced by Engine-level repeatability contract:

- tests/test_engine_repeatability_contract.py

We keep this file temporarily for migration traceability.
"""

import pytest

pytest.skip(
    "Deprecated legacy pipeline repeatability test. Use Engine repeatability contract instead.",
    allow_module_level=True,
)
