from __future__ import annotations

from typing import Dict, List, Set, TYPE_CHECKING

from ..fingerprint import compute_fingerprint
from ..model import EngineStructure
from .result import ValidationResult, Violation, Severity

if TYPE_CHECKING:
    from ..engine import Engine


STRUCTURAL_RULE_IDS = ["CH-001", "ENG-001", "ENG-003", "NODE-001"]


class StructuralValidator:
    """Structural Validation Engine.

    Validates engine/circuit structural correctness.
    This validator is always blocking - if it fails, execution cannot proceed.

    Implemented rules:
    - ENG-001: Missing Entry
    - NODE-001: Duplicate node_id
    - ENG-003: Cycle (DAG violation)
    - CH-001: Channel References Missing Node
    """

    def validate(self, engine: "Engine", *, revision_id: str) -> ValidationResult:
        structure: EngineStructure = engine.to_structure()
        fingerprint = compute_fingerprint(structure)

        violations: List[Violation] = []

        # ENG-001: Missing Entry
        if not structure.entry_node_id:
            violations.append(
                Violation(
                    rule_id="ENG-001",
                    rule_name="Missing Entry Node",
                    severity=Severity.ERROR,
                    location_type="engine",
                    location_id=None,
                    message="Engine must define exactly one entry_node_id.",
                )
            )

        # NODE-001: Duplicate node_id
        if len(structure.node_ids) != len(set(structure.node_ids)):
            violations.append(
                Violation(
                    rule_id="NODE-001",
                    rule_name="Duplicate node_id",
                    severity=Severity.ERROR,
                    location_type="engine",
                    location_id=None,
                    message="Duplicate node_id detected in EngineStructure.",
                )
            )

        # CH-001: Channel References Missing Node
        node_id_set = set(structure.node_ids)
        for ch in structure.channels:
            if ch.src_node_id not in node_id_set or ch.dst_node_id not in node_id_set:
                violations.append(
                    Violation(
                        rule_id="CH-001",
                        rule_name="Channel References Missing Node",
                        severity=Severity.ERROR,
                        location_type="engine",
                        location_id=None,
                        message="Channel references undefined src or dst node_id.",
                    )
                )

        # ENG-003: Cycle detection (DAG validation)
        if self._has_cycle(structure):
            violations.append(
                Violation(
                    rule_id="ENG-003",
                    rule_name="Cycle Detected",
                    severity=Severity.ERROR,
                    location_type="engine",
                    location_id=None,
                    message="Engine graph must be a DAG (cycle detected).",
                )
            )

        success = not any(v.severity == Severity.ERROR for v in violations)

        return ValidationResult(
            success=success,
            engine_revision=revision_id,
            structural_fingerprint=fingerprint.value,
            applied_rule_ids=list(STRUCTURAL_RULE_IDS),
            violations=violations,
        )

    def _has_cycle(self, structure: EngineStructure) -> bool:
        graph: Dict[str, List[str]] = {nid: [] for nid in structure.node_ids}

        for ch in structure.channels:
            if ch.src_node_id in graph and ch.dst_node_id in graph:
                graph[ch.src_node_id].append(ch.dst_node_id)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True

        return False
