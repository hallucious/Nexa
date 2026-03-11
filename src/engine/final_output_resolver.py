from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.engine.compiled_resource_graph import CompiledResourceGraph


class FinalOutputResolverError(ValueError):
    """Raised when runtime cannot resolve a deterministic final output."""


@dataclass(frozen=True)
class ResolvedFinalOutput:
    value: Any
    source_key: str
    candidates: List[str]


_DOMAIN_PRIORITY = {
    "plugin": 0,
    "provider": 1,
    "prompt": 2,
    "output": 3,
    "system": 4,
    "input": 5,
}

_FIELD_PRIORITY = {
    "value": 0,
    "result": 1,
    "output": 2,
    "rendered": 3,
}


def _candidate_priority(key: str) -> tuple[int, int, str]:
    parts = key.split(".")
    domain = parts[0] if parts else ""
    field = parts[-1] if parts else ""
    return (
        _DOMAIN_PRIORITY.get(domain, 99),
        _FIELD_PRIORITY.get(field, 99),
        key,
    )


def resolve_final_output(
    graph: CompiledResourceGraph,
    flat_context: Dict[str, Any],
) -> ResolvedFinalOutput:
    available_candidates = sorted(
        [key for key in graph.final_candidates if key in flat_context],
        key=_candidate_priority,
    )

    if not available_candidates:
        raise FinalOutputResolverError(
            "no available final output candidates found in runtime context"
        )

    selected_key = available_candidates[0]
    return ResolvedFinalOutput(
        value=flat_context[selected_key],
        source_key=selected_key,
        candidates=available_candidates,
    )