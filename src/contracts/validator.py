from __future__ import annotations

from typing import Dict, List, Set, TYPE_CHECKING

from ..fingerprint import compute_fingerprint
from ..model import EngineStructure
from .result import ValidationResult, Violation, Severity

if TYPE_CHECKING:
    from ..engine import Engine


APPLIED_RULE_IDS = [
    "ENG-001",
    "ENG-003",
    "NODE-001",
    "CH-001",
    "DET-001",
    "DET-002",
    "DET-003",
    "DET-004",
    "DET-005",
    "DET-006",
    "DET-007",
]


class ValidationEngine:
    def validate(self, engine: "Engine", *, revision_id: str) -> ValidationResult:
        structure: EngineStructure = engine.to_structure()
        fingerprint = compute_fingerprint(structure)

        violations: List[Violation] = []

        # --- ENGINE RULES ---
        if not structure.entry_node_id:
            violations.append(
                Violation("ENG-001", "Missing Entry Node", Severity.ERROR, "engine", None,
                          "Engine must define entry_node_id.")
            )

        if self._has_cycle(structure):
            violations.append(
                Violation("ENG-003", "Cycle Detected", Severity.ERROR, "engine", None,
                          "Engine graph must be DAG.")
            )

        # --- NODE RULES ---
        if len(structure.node_ids) != len(set(structure.node_ids)):
            violations.append(
                Violation("NODE-001", "Duplicate node_id", Severity.ERROR, "engine", None,
                          "Duplicate node_id detected.")
            )

        # --- CHANNEL RULES ---
        node_id_set = set(structure.node_ids)
        for ch in structure.channels:
            if ch.src_node_id not in node_id_set or ch.dst_node_id not in node_id_set:
                violations.append(
                    Violation("CH-001", "Invalid Channel", Severity.ERROR, "engine", None,
                              "Channel references invalid node.")
                )

        # --- DET RULES ---
        if "determinism" not in structure.meta:
            violations.append(
                Violation("DET-001", "Determinism Missing", Severity.ERROR, "engine", None,
                          "Determinism config required.")
            )

        node_specs = structure.meta.get("node_specs", {})

        for node_id in structure.node_ids:
            spec = node_specs.get(node_id)
            if not spec:
                continue

            if spec.get("provider_ref") is None:
                violations.append(
                    Violation("DET-002", "Provider Missing", Severity.ERROR, "node", node_id,
                              "provider_ref required.")
                )

            if spec.get("model") is None:
                violations.append(
                    Violation("DET-003", "Model Missing", Severity.ERROR, "node", node_id,
                              "model required.")
                )

            temp = spec.get("temperature")
            if temp is None:
                violations.append(
                    Violation("DET-004", "Temperature Missing", Severity.ERROR, "node", node_id,
                              "temperature required.")
                )
            else:
                if not isinstance(temp, (int, float)) or not (0 <= temp <= 2):
                    violations.append(
                        Violation("DET-007", "Invalid Temperature Range", Severity.ERROR, "node", node_id,
                                  "temperature must be between 0 and 2.")
                    )

            if spec.get("seed") is None:
                violations.append(
                    Violation("DET-005", "Seed Missing", Severity.ERROR, "node", node_id,
                              "seed required.")
                )

            if spec.get("prompt_ref") is None:
                violations.append(
                    Violation("DET-006", "Prompt Missing", Severity.ERROR, "node", node_id,
                              "prompt_ref required.")
                )

        success = not any(v.severity == Severity.ERROR for v in violations)

        return ValidationResult(
            success=success,
            engine_revision=revision_id,
            structural_fingerprint=fingerprint.value,
            applied_rule_ids=list(APPLIED_RULE_IDS),
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
