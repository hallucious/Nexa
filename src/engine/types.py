from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class NodeStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    NOT_REACHED = "not_reached"


class StageStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"




class FlowPolicy(str, Enum):
    """DAG propagation gating policy for a node with multiple upstream parents."""
    ALL_SUCCESS = "ALL_SUCCESS"
    ANY_SUCCESS = "ANY_SUCCESS"
    FIRST_SUCCESS = "FIRST_SUCCESS"

@dataclass(frozen=True)
class StageResult:
    status: StageStatus
    reason_code: Optional[str] = None
    message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class NodeResult:
    success: bool
    status: NodeStatus
    reason_code: Optional[str] = None
    message: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
