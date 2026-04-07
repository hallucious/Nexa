"""trace_intelligence.py

Trace Intelligence layer (precision track, v0.1).

Upgrades trace from passive history into analyzable operational evidence.
Derived insights never rewrite trace truth.

Canonical outputs:
  - FailureTaxonomySummary
  - BottleneckSummary
  - TraceDiffSummary
  - ReplayMutationSummary
  - AttributionSummary
  - TraceIntelligenceReport

Entry points:
  - analyze_trace()       — full report from raw trace dicts
  - diff_traces()         — compare two runs beyond raw diff
  - explain_run_diff()    — human-readable attribution of divergence
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Sub-objects ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailureCategoryCount:
    category: str
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return {"category": self.category, "count": self.count}


@dataclass(frozen=True)
class FailureTaxonomySummary:
    categories: List[FailureCategoryCount]
    top_reason_codes: List[str]
    repeated_failure_patterns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "categories": [c.to_dict() for c in self.categories],
            "top_reason_codes": list(self.top_reason_codes),
            "repeated_failure_patterns": list(self.repeated_failure_patterns),
        }


@dataclass(frozen=True)
class NodeTiming:
    node_id: str
    duration_ms: Optional[float]
    cost_estimate: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "duration_ms": self.duration_ms,
            "cost_estimate": self.cost_estimate,
        }


@dataclass(frozen=True)
class BottleneckSummary:
    slowest_nodes: List[str]       # node_ids by descending duration
    highest_cost_nodes: List[str]  # node_ids by descending cost
    node_timings: List[NodeTiming]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slowest_nodes": list(self.slowest_nodes),
            "highest_cost_nodes": list(self.highest_cost_nodes),
            "node_timings": [n.to_dict() for n in self.node_timings],
        }


@dataclass(frozen=True)
class TraceDiffEntry:
    field_path: str
    run_a_value: Any
    run_b_value: Any
    change_type: str  # "added" | "removed" | "changed" | "unchanged"
    significance: str  # "high" | "medium" | "low"
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_path": self.field_path,
            "run_a_value": self.run_a_value,
            "run_b_value": self.run_b_value,
            "change_type": self.change_type,
            "significance": self.significance,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class TraceDiffSummary:
    run_a_ref: str
    run_b_ref: str
    entries: List[TraceDiffEntry]
    high_significance_count: int
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_a_ref": self.run_a_ref,
            "run_b_ref": self.run_b_ref,
            "entries": [e.to_dict() for e in self.entries],
            "high_significance_count": self.high_significance_count,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class ReplayMutationSummary:
    original_run_ref: str
    mutated_fields: List[str]
    expected_impact: str   # "high" | "medium" | "low" | "unknown"
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_run_ref": self.original_run_ref,
            "mutated_fields": list(self.mutated_fields),
            "expected_impact": self.expected_impact,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class AttributionSummary:
    primary_cause: str
    contributing_factors: List[str]
    improvement_suggestions: List[str]
    degradation_signals: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_cause": self.primary_cause,
            "contributing_factors": list(self.contributing_factors),
            "improvement_suggestions": list(self.improvement_suggestions),
            "degradation_signals": list(self.degradation_signals),
        }


@dataclass(frozen=True)
class TraceIntelligenceReport:
    report_id: str
    run_ref: str
    trace_refs: List[str]
    failure_taxonomy: FailureTaxonomySummary
    bottleneck_summary: BottleneckSummary
    attribution_summary: AttributionSummary
    explanation: str
    diff_summary: Optional[TraceDiffSummary] = None
    replay_mutation_summary: Optional[ReplayMutationSummary] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_ref": self.run_ref,
            "trace_refs": list(self.trace_refs),
            "failure_taxonomy": self.failure_taxonomy.to_dict(),
            "bottleneck_summary": self.bottleneck_summary.to_dict(),
            "attribution_summary": self.attribution_summary.to_dict(),
            "diff_summary": self.diff_summary.to_dict() if self.diff_summary else None,
            "replay_mutation_summary": (
                self.replay_mutation_summary.to_dict()
                if self.replay_mutation_summary
                else None
            ),
            "explanation": self.explanation,
        }


# ── Analysis logic ─────────────────────────────────────────────────────────

def _extract_failure_taxonomy(
    node_events: List[Dict[str, Any]],
) -> FailureTaxonomySummary:
    """Build a FailureTaxonomySummary from a list of node event dicts."""
    category_counts: Dict[str, int] = {}
    reason_code_counts: Dict[str, int] = {}
    repeated: List[str] = []

    for evt in node_events:
        status = evt.get("status", "")
        if status in ("fail", "error"):
            reason = evt.get("reason_code") or evt.get("reason") or "UNKNOWN"
            category = evt.get("failure_category") or "uncategorized"
            category_counts[category] = category_counts.get(category, 0) + 1
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1

    # Repeated = reason_code seen more than once
    repeated = [rc for rc, cnt in reason_code_counts.items() if cnt > 1]

    top_codes = sorted(
        reason_code_counts, key=lambda x: reason_code_counts[x], reverse=True
    )[:5]

    cats = [
        FailureCategoryCount(category=k, count=v)
        for k, v in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return FailureTaxonomySummary(
        categories=cats,
        top_reason_codes=top_codes,
        repeated_failure_patterns=repeated,
    )


def _extract_bottleneck(
    node_events: List[Dict[str, Any]],
) -> BottleneckSummary:
    """Build a BottleneckSummary from node event dicts."""
    timings: List[NodeTiming] = []

    for evt in node_events:
        node_id = evt.get("node_id") or evt.get("id") or ""
        duration = evt.get("duration_ms") or evt.get("duration")
        cost = evt.get("cost_estimate") or evt.get("cost")
        if node_id:
            timings.append(NodeTiming(
                node_id=node_id,
                duration_ms=float(duration) if duration is not None else None,
                cost_estimate=float(cost) if cost is not None else None,
            ))

    slowest = sorted(
        [t for t in timings if t.duration_ms is not None],
        key=lambda t: t.duration_ms,  # type: ignore[arg-type]
        reverse=True,
    )
    highest_cost = sorted(
        [t for t in timings if t.cost_estimate is not None],
        key=lambda t: t.cost_estimate,  # type: ignore[arg-type]
        reverse=True,
    )

    return BottleneckSummary(
        slowest_nodes=[t.node_id for t in slowest[:5]],
        highest_cost_nodes=[t.node_id for t in highest_cost[:5]],
        node_timings=timings,
    )


def analyze_trace(
    *,
    run_ref: str,
    node_events: List[Dict[str, Any]],
    trace_refs: Optional[List[str]] = None,
    report_id: Optional[str] = None,
) -> TraceIntelligenceReport:
    """Produce a TraceIntelligenceReport from raw node event dicts.

    node_events: list of dicts with fields like node_id, status, reason_code,
                 duration_ms, cost_estimate, failure_category.
    """
    failure_taxonomy = _extract_failure_taxonomy(node_events)
    bottleneck = _extract_bottleneck(node_events)

    # Attribution: primary cause from top reason code
    primary_cause = (
        failure_taxonomy.top_reason_codes[0]
        if failure_taxonomy.top_reason_codes
        else "NO_FAILURES_DETECTED"
    )

    contributing = failure_taxonomy.repeated_failure_patterns[:3]

    improvement_suggestions: List[str] = []
    degradation_signals: List[str] = []

    if bottleneck.slowest_nodes:
        improvement_suggestions.append(
            f"optimize slowest node: {bottleneck.slowest_nodes[0]}"
        )
    if bottleneck.highest_cost_nodes:
        degradation_signals.append(
            f"highest cost node: {bottleneck.highest_cost_nodes[0]}"
        )
    if failure_taxonomy.repeated_failure_patterns:
        degradation_signals.append(
            f"repeated failure pattern: {failure_taxonomy.repeated_failure_patterns[0]}"
        )

    attribution = AttributionSummary(
        primary_cause=primary_cause,
        contributing_factors=contributing,
        improvement_suggestions=improvement_suggestions,
        degradation_signals=degradation_signals,
    )

    total_failures = sum(c.count for c in failure_taxonomy.categories)
    explanation = (
        f"analyzed {len(node_events)} node event(s); "
        f"{total_failures} failure(s); "
        f"{len(bottleneck.node_timings)} timing records"
    )

    return TraceIntelligenceReport(
        report_id=report_id or str(uuid.uuid4()),
        run_ref=run_ref,
        trace_refs=list(trace_refs or []),
        failure_taxonomy=failure_taxonomy,
        bottleneck_summary=bottleneck,
        attribution_summary=attribution,
        explanation=explanation,
    )


def diff_traces(
    *,
    run_a_ref: str,
    run_b_ref: str,
    events_a: List[Dict[str, Any]],
    events_b: List[Dict[str, Any]],
) -> TraceDiffSummary:
    """Compare two run trace event sets beyond raw field diff.

    Detects: node presence changes, status changes, reason_code changes.
    """
    entries: List[TraceDiffEntry] = []

    nodes_a = {e.get("node_id", e.get("id", "")): e for e in events_a if e.get("node_id") or e.get("id")}
    nodes_b = {e.get("node_id", e.get("id", "")): e for e in events_b if e.get("node_id") or e.get("id")}

    all_nodes = set(nodes_a) | set(nodes_b)
    for node_id in sorted(all_nodes):
        if node_id not in nodes_a:
            entries.append(TraceDiffEntry(
                field_path=f"node.{node_id}",
                run_a_value=None,
                run_b_value="present",
                change_type="added",
                significance="high",
                explanation=f"node {node_id!r} appeared in run B but not A",
            ))
        elif node_id not in nodes_b:
            entries.append(TraceDiffEntry(
                field_path=f"node.{node_id}",
                run_a_value="present",
                run_b_value=None,
                change_type="removed",
                significance="high",
                explanation=f"node {node_id!r} disappeared in run B",
            ))
        else:
            ea, eb = nodes_a[node_id], nodes_b[node_id]
            for field in ("status", "reason_code", "failure_category"):
                va, vb = ea.get(field), eb.get(field)
                if va != vb:
                    sig = "high" if field == "status" else "medium"
                    entries.append(TraceDiffEntry(
                        field_path=f"node.{node_id}.{field}",
                        run_a_value=va,
                        run_b_value=vb,
                        change_type="changed",
                        significance=sig,
                        explanation=f"{field} changed from {va!r} to {vb!r}",
                    ))

    high_count = sum(1 for e in entries if e.significance == "high")
    explanation = (
        f"diff of {run_a_ref!r} vs {run_b_ref!r}; "
        f"{len(entries)} change(s); {high_count} high-significance"
    )

    return TraceDiffSummary(
        run_a_ref=run_a_ref,
        run_b_ref=run_b_ref,
        entries=entries,
        high_significance_count=high_count,
        explanation=explanation,
    )


def explain_run_diff(
    diff: TraceDiffSummary,
) -> str:
    """Produce a human-readable explanation of why run A and run B differ.

    Goes beyond raw diff output by grouping and attributing changes.
    """
    if not diff.entries:
        return "Run A and run B produced identical trace structures."

    high = [e for e in diff.entries if e.significance == "high"]
    medium = [e for e in diff.entries if e.significance == "medium"]
    low = [e for e in diff.entries if e.significance == "low"]

    lines = [
        f"Comparing run {diff.run_a_ref!r} → {diff.run_b_ref!r}:",
        f"  Total changes: {len(diff.entries)} "
        f"({len(high)} high, {len(medium)} medium, {len(low)} low significance)",
    ]

    if high:
        lines.append("High-significance changes:")
        for e in high[:5]:
            lines.append(f"  • {e.explanation}")

    if medium:
        lines.append("Medium-significance changes:")
        for e in medium[:3]:
            lines.append(f"  • {e.explanation}")

    return "\n".join(lines)
