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


class NodeFailurePolicy(str, Enum):
    """Controls how upstream FAILURE affects a downstream node.

    Kept separate from FlowPolicy to preserve the single-responsibility rule:
      FlowPolicy   — when a node is allowed to run based on upstream success state
      NodeFailurePolicy — how upstream FAILURE is interpreted for this node

    Values:
        STRICT       — preserve current default behavior: upstream FAILURE /
                       SKIPPED makes progress impossible under FlowPolicy;
                       the downstream node becomes SKIPPED.
        ISOLATE      — upstream FAILURE is ignored for propagation; node may
                       still run if its FlowPolicy condition can be satisfied
                       by available upstream states.
        CASCADE_FAIL — any upstream FAILURE immediately marks this node as
                       FAILURE; handler is not executed.
    """

    STRICT = "STRICT"
    ISOLATE = "ISOLATE"
    CASCADE_FAIL = "CASCADE_FAIL"

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
