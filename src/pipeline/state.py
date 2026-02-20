from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from src.models.decision_models import Transition


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    STOP = "STOP"


class GateId(str, Enum):
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    G4 = "G4"
    G5 = "G5"
    G6 = "G6"
    G7 = "G7"
    DONE = "DONE"
    STOP = "STOP"


@dataclass
class RunMeta:
    run_id: str
    created_at: str  # ISO8601
    baseline_version_id: Optional[str] = None
    current_gate: GateId = GateId.G1
    status: RunStatus = RunStatus.RUNNING
    transitions: List[Transition] = field(default_factory=list)
    attempts: Dict[str, int] = field(default_factory=dict)
    providers: Dict[str, str] = field(default_factory=dict)  # e.g. {"gpt":"stub", ...}
    stop_reason: Optional[str] = None  # terminal STOP reason (if any)