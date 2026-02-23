from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from src.pipeline.state import GateId


@dataclass
class GateRegistry:
    """In-memory registry for gate executors.

    v0 goal: provide a single place to register and introspect gates.
    Dynamic plugin loading is explicitly out-of-scope for v0.
    """

    _executors: Dict[GateId, object] = field(default_factory=dict)

    def register(self, gate_id: GateId, executor: object) -> None:
        self._executors[gate_id] = executor

    def get(self, gate_id: GateId) -> Optional[object]:
        return self._executors.get(gate_id)

    def ids(self) -> List[GateId]:
        return list(self._executors.keys())

    def items(self) -> Iterable[tuple[GateId, object]]:
        return self._executors.items()