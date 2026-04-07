"""test_step225_trace_intelligence.py

Tests for:
  - src/engine/trace_intelligence.py
"""
from __future__ import annotations

import pytest

from src.engine.trace_intelligence import (
    AttributionSummary,
    BottleneckSummary,
    FailureCategoryCount,
    FailureTaxonomySummary,
    NodeTiming,
    ReplayMutationSummary,
    TraceDiffEntry,
    TraceDiffSummary,
    TraceIntelligenceReport,
    analyze_trace,
    diff_traces,
    explain_run_diff,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _event(node_id="n1", status="pass", reason_code=None,
           duration_ms=None, cost_estimate=None, failure_category=None):
    e = {"node_id": node_id, "status": status}
    if reason_code:
        e["reason_code"] = reason_code
    if duration_ms is not None:
        e["duration_ms"] = duration_ms
    if cost_estimate is not None:
        e["cost_estimate"] = cost_estimate
    if failure_category:
        e["failure_category"] = failure_category
    return e


# ─────────────────────────────────────────────────────────────────────────────
# TraceIntelligenceReport structure
# ─────────────────────────────────────────────────────────────────────────────

class TestTraceIntelligenceReportStructure:
    def test_to_dict_complete(self):
        report = analyze_trace(run_ref="run:r1", node_events=[])
        d = report.to_dict()
        assert "report_id" in d
        assert "run_ref" in d
        assert "failure_taxonomy" in d
        assert "bottleneck_summary" in d
        assert "attribution_summary" in d
        assert d["diff_summary"] is None
        assert d["replay_mutation_summary"] is None

    def test_report_id_generated(self):
        report = analyze_trace(run_ref="r1", node_events=[])
        assert report.report_id

    def test_custom_report_id(self):
        report = analyze_trace(run_ref="r1", node_events=[], report_id="fixed-id")
        assert report.report_id == "fixed-id"


# ─────────────────────────────────────────────────────────────────────────────
# analyze_trace — failure taxonomy
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeTraceFailureTaxonomy:
    def test_no_failures(self):
        events = [_event("n1", "pass"), _event("n2", "pass")]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert report.failure_taxonomy.top_reason_codes == []
        assert report.failure_taxonomy.categories == []

    def test_single_failure(self):
        events = [_event("n1", "fail", reason_code="TIMEOUT", failure_category="latency")]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert "TIMEOUT" in report.failure_taxonomy.top_reason_codes
        assert report.failure_taxonomy.categories[0].category == "latency"
        assert report.failure_taxonomy.categories[0].count == 1

    def test_repeated_failure_detected(self):
        events = [
            _event("n1", "fail", reason_code="EMPTY_OUTPUT"),
            _event("n2", "fail", reason_code="EMPTY_OUTPUT"),
        ]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert "EMPTY_OUTPUT" in report.failure_taxonomy.repeated_failure_patterns

    def test_top_reason_codes_ordered_by_frequency(self):
        events = [
            _event("n1", "fail", reason_code="A"),
            _event("n2", "fail", reason_code="A"),
            _event("n3", "fail", reason_code="B"),
        ]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert report.failure_taxonomy.top_reason_codes[0] == "A"

    def test_error_status_also_counts_as_failure(self):
        events = [_event("n1", "error", reason_code="INTERNAL")]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert "INTERNAL" in report.failure_taxonomy.top_reason_codes


# ─────────────────────────────────────────────────────────────────────────────
# analyze_trace — bottleneck summary
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeTraceBottleneck:
    def test_no_timing_data(self):
        events = [_event("n1", "pass")]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert report.bottleneck_summary.slowest_nodes == []

    def test_slowest_nodes_ordered(self):
        events = [
            _event("n1", duration_ms=500),
            _event("n2", duration_ms=100),
            _event("n3", duration_ms=300),
        ]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert report.bottleneck_summary.slowest_nodes[0] == "n1"

    def test_highest_cost_nodes_ordered(self):
        events = [
            _event("n1", cost_estimate=10.0),
            _event("n2", cost_estimate=1.0),
        ]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert report.bottleneck_summary.highest_cost_nodes[0] == "n1"

    def test_node_timings_recorded(self):
        events = [_event("n1", duration_ms=100, cost_estimate=5.0)]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert len(report.bottleneck_summary.node_timings) == 1
        t = report.bottleneck_summary.node_timings[0]
        assert t.duration_ms == 100.0
        assert t.cost_estimate == 5.0


# ─────────────────────────────────────────────────────────────────────────────
# analyze_trace — attribution
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeTraceAttribution:
    def test_no_failures_primary_cause(self):
        report = analyze_trace(run_ref="r1", node_events=[])
        assert report.attribution_summary.primary_cause == "NO_FAILURES_DETECTED"

    def test_primary_cause_is_top_reason_code(self):
        events = [_event("n1", "fail", reason_code="TIMEOUT")]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert report.attribution_summary.primary_cause == "TIMEOUT"

    def test_slowest_node_in_suggestions(self):
        events = [
            _event("n1", duration_ms=999),
            _event("n2", duration_ms=10),
        ]
        report = analyze_trace(run_ref="r1", node_events=events)
        assert any("n1" in s for s in report.attribution_summary.improvement_suggestions)

    def test_to_dict(self):
        report = analyze_trace(run_ref="r1", node_events=[])
        d = report.attribution_summary.to_dict()
        assert "primary_cause" in d
        assert "improvement_suggestions" in d


# ─────────────────────────────────────────────────────────────────────────────
# diff_traces
# ─────────────────────────────────────────────────────────────────────────────

class TestDiffTraces:
    def test_identical_traces_no_entries(self):
        events = [_event("n1", "pass"), _event("n2", "pass")]
        diff = diff_traces(
            run_a_ref="A", run_b_ref="B",
            events_a=events, events_b=events,
        )
        assert diff.entries == []
        assert diff.high_significance_count == 0

    def test_added_node_detected(self):
        ea = [_event("n1", "pass")]
        eb = [_event("n1", "pass"), _event("n2", "pass")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        change_types = [e.change_type for e in diff.entries]
        assert "added" in change_types

    def test_removed_node_detected(self):
        ea = [_event("n1", "pass"), _event("n2", "pass")]
        eb = [_event("n1", "pass")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        change_types = [e.change_type for e in diff.entries]
        assert "removed" in change_types

    def test_status_change_detected(self):
        ea = [_event("n1", "pass")]
        eb = [_event("n1", "fail")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        changed = [e for e in diff.entries if e.change_type == "changed"]
        assert changed
        assert changed[0].field_path == "node.n1.status"
        assert changed[0].significance == "high"

    def test_reason_code_change_medium_significance(self):
        ea = [_event("n1", "fail", reason_code="A")]
        eb = [_event("n1", "fail", reason_code="B")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        rc_entries = [e for e in diff.entries if "reason_code" in e.field_path]
        assert rc_entries
        assert rc_entries[0].significance == "medium"

    def test_high_significance_count(self):
        ea = [_event("n1", "pass"), _event("n2", "pass")]
        eb = [_event("n1", "fail"), _event("n3", "pass")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        assert diff.high_significance_count >= 2

    def test_to_dict(self):
        diff = diff_traces(
            run_a_ref="A", run_b_ref="B",
            events_a=[_event("n1")], events_b=[_event("n1")],
        )
        d = diff.to_dict()
        assert "entries" in d
        assert d["run_a_ref"] == "A"


# ─────────────────────────────────────────────────────────────────────────────
# explain_run_diff
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainRunDiff:
    def test_identical_runs_message(self):
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=[], events_b=[])
        explanation = explain_run_diff(diff)
        assert "identical" in explanation.lower()

    def test_explanation_mentions_high_significance(self):
        ea = [_event("n1", "pass")]
        eb = [_event("n1", "fail")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        explanation = explain_run_diff(diff)
        assert "High-significance" in explanation

    def test_explanation_is_string(self):
        ea = [_event("n1")]
        eb = [_event("n2")]
        diff = diff_traces(run_a_ref="A", run_b_ref="B", events_a=ea, events_b=eb)
        explanation = explain_run_diff(diff)
        assert isinstance(explanation, str)
        assert len(explanation) > 0
