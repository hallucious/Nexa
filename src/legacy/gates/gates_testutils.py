from __future__ import annotations

"""
Test helper re-exports.

Some tests import:
  from src.gates.gates_testutils import make_contract_pass_gate

But the actual implementation lives in mock gate modules.
This file provides a stable import path for tests.
"""

from src.gates.mock_gate import make_pass_gate, make_info_gate
from src.gates.mock_gate_v2 import make_contract_pass_gate

__all__ = [
    "make_pass_gate",
    "make_info_gate",
    "make_contract_pass_gate",
]
