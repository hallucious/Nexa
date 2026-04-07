"""test_step224_branch_merge_and_outcome_memory.py

Tests for:
  - src/contracts/branch_contract.py
  - src/engine/outcome_memory.py
"""
from __future__ import annotations

import pytest

from src.contracts.branch_contract import (
    BranchCandidate,
    BranchContractError,
    BranchStateRef,
    BranchStatus,
    MergePolicy,
    MergeResult,
    MergeStrategy,
    create_branch,
    merge_candidates,
)
from src.engine.outcome_memory import (
    FailurePattern,
    MemoryFamily,
    OutcomeMemoryError,
    OutcomeMemoryStore,
    RepairPattern,
    SuccessPattern,
    record_failure_pattern,
    record_repair_pattern,
    record_success_pattern,
)


# ─────────────────────────────────────────────────────────────────────────────
# BranchStateRef contract
# ─────────────────────────────────────────────────────────────────────────────

class TestBranchStateRef:
    def _make(self, **kw):
        defaults = dict(
            branch_id="b1",
            parent_state_ref="run:r1",
            branch_reason="explore alternative",
            branch_policy="default",
            created_at="2025-01-01T00:00:00Z",
        )
        defaults.update(kw)
        return BranchStateRef(**defaults)

    def test_valid(self):
        b = self._make()
        assert b.status == BranchStatus.ACTIVE

    def test_empty_branch_id_rejected(self):
        with pytest.raises(BranchContractError):
            self._make(branch_id="")

    def test_empty_parent_state_ref_rejected(self):
        with pytest.raises(BranchContractError):
            self._make(parent_state_ref="")

    def test_empty_branch_reason_rejected(self):
        with pytest.raises(BranchContractError):
            self._make(branch_reason="")

    def test_invalid_status(self):
        with pytest.raises(BranchContractError):
            self._make(status="flying")

    def test_to_dict(self):
        b = self._make()
        d = b.to_dict()
        assert d["branch_id"] == "b1"
        assert d["status"] == BranchStatus.ACTIVE


# ─────────────────────────────────────────────────────────────────────────────
# create_branch factory
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateBranch:
    def test_produces_active_branch(self):
        b = create_branch(parent_state_ref="run:r1", branch_reason="test")
        assert b.status == BranchStatus.ACTIVE
        assert b.branch_id

    def test_custom_id(self):
        b = create_branch(parent_state_ref="r1", branch_reason="r", branch_id="fixed")
        assert b.branch_id == "fixed"

    def test_timestamp_auto_set(self):
        b = create_branch(parent_state_ref="r1", branch_reason="r")
        assert b.created_at


# ─────────────────────────────────────────────────────────────────────────────
# MergePolicy contract
# ─────────────────────────────────────────────────────────────────────────────

class TestMergePolicy:
    def test_valid(self):
        p = MergePolicy(policy_id="p1", strategy=MergeStrategy.PICK_BEST)
        assert p.strategy == MergeStrategy.PICK_BEST

    def test_empty_policy_id_rejected(self):
        with pytest.raises(BranchContractError):
            MergePolicy(policy_id="", strategy=MergeStrategy.PICK_BEST)

    def test_invalid_strategy(self):
        with pytest.raises(BranchContractError):
            MergePolicy(policy_id="p1", strategy="magic_sort")

    def test_to_dict(self):
        p = MergePolicy(policy_id="p1", strategy=MergeStrategy.HUMAN_CHOICE)
        d = p.to_dict()
        assert d["strategy"] == MergeStrategy.HUMAN_CHOICE


# ─────────────────────────────────────────────────────────────────────────────
# merge_candidates
# ─────────────────────────────────────────────────────────────────────────────

def _make_candidate(branch_id: str, score: float, artifacts=None) -> BranchCandidate:
    ref = create_branch(parent_state_ref="run:r1", branch_reason="test", branch_id=branch_id)
    return BranchCandidate(
        branch_ref=ref,
        score=score,
        artifact_refs=artifacts or [f"art:{branch_id}"],
        trace_ref=None,
        summary=f"branch {branch_id}",
    )


class TestMergeCandidates:
    def test_pick_best_selects_highest(self):
        c1 = _make_candidate("b1", 0.9)
        c2 = _make_candidate("b2", 0.5)
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.PICK_BEST)
        result = merge_candidates([c1, c2], policy=policy)
        assert result.selected_branch_id == "b1"
        assert "b2" in result.discarded_branch_ids

    def test_pick_first(self):
        c1 = _make_candidate("b1", 0.3)
        c2 = _make_candidate("b2", 0.9)
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.PICK_FIRST)
        result = merge_candidates([c1, c2], policy=policy)
        assert result.selected_branch_id == "b1"

    def test_human_choice_requires_human(self):
        c1 = _make_candidate("b1", 0.5)
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.HUMAN_CHOICE)
        result = merge_candidates([c1], policy=policy)
        assert result.requires_human_decision

    def test_union_combines_artifacts(self):
        c1 = _make_candidate("b1", 0.5, artifacts=["art:1a", "art:1b"])
        c2 = _make_candidate("b2", 0.7, artifacts=["art:2a"])
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.UNION)
        result = merge_candidates([c1, c2], policy=policy)
        assert "art:1a" in result.merged_artifact_refs
        assert "art:2a" in result.merged_artifact_refs
        assert result.selected_branch_id is None

    def test_tie_detected_with_human_required(self):
        c1 = _make_candidate("b1", 0.5)
        c2 = _make_candidate("b2", 0.5)
        policy = MergePolicy(
            policy_id="p1",
            strategy=MergeStrategy.PICK_BEST,
            require_human_on_tie=True,
        )
        result = merge_candidates([c1, c2], policy=policy)
        assert result.conflict_detected
        assert result.requires_human_decision

    def test_empty_candidates_raises(self):
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.PICK_BEST)
        with pytest.raises(BranchContractError):
            merge_candidates([], policy=policy)

    def test_result_to_dict(self):
        c1 = _make_candidate("b1", 0.8)
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.PICK_BEST)
        result = merge_candidates([c1], policy=policy)
        d = result.to_dict()
        assert "merge_id" in d
        assert "merge_policy" in d

    def test_discarded_branches_traceable(self):
        c1 = _make_candidate("b1", 0.9)
        c2 = _make_candidate("b2", 0.3)
        c3 = _make_candidate("b3", 0.1)
        policy = MergePolicy(policy_id="p1", strategy=MergeStrategy.PICK_BEST)
        result = merge_candidates([c1, c2, c3], policy=policy)
        assert len(result.discarded_branch_ids) == 2


# ─────────────────────────────────────────────────────────────────────────────
# OutcomeMemoryStore
# ─────────────────────────────────────────────────────────────────────────────

class TestOutcomeMemoryStore:
    def test_record_success(self):
        store = OutcomeMemoryStore()
        p = record_success_pattern(
            store,
            route_tier="balanced",
            provider_id="gpt4",
            task_types=["summarize"],
            confidence_score=0.85,
        )
        assert store.total_entries() == 1
        assert p.family == MemoryFamily.SUCCESS

    def test_record_failure(self):
        store = OutcomeMemoryStore()
        p = record_failure_pattern(
            store,
            reason_codes=["REQUIREMENT_EMPTY_OUTPUT"],
            task_types=["generate"],
            occurrence_count=3,
        )
        assert store.total_entries() == 1
        assert p.family == MemoryFamily.FAILURE

    def test_record_repair(self):
        store = OutcomeMemoryStore()
        p = record_repair_pattern(
            store,
            problem_reason_codes=["REQUIREMENT_EMPTY_OUTPUT"],
            repair_action="retry_with_higher_quality",
            success_rate=0.8,
            task_types=["generate"],
        )
        assert p.family == MemoryFamily.REPAIR

    def test_duplicate_success_rejected(self):
        store = OutcomeMemoryStore()
        record_success_pattern(
            store, route_tier="cheap", provider_id="p1",
            task_types=["t"], confidence_score=0.5, pattern_id="fixed",
        )
        with pytest.raises(OutcomeMemoryError):
            record_success_pattern(
                store, route_tier="cheap", provider_id="p1",
                task_types=["t"], confidence_score=0.5, pattern_id="fixed",
            )

    def test_query_failures_by_reason_code(self):
        store = OutcomeMemoryStore()
        record_failure_pattern(
            store, reason_codes=["CODE_A", "CODE_B"], task_types=["t"]
        )
        record_failure_pattern(
            store, reason_codes=["CODE_C"], task_types=["t"]
        )
        results = store.query_failures_by_reason_code("CODE_A")
        assert len(results) == 1

    def test_query_successes_by_task_type(self):
        store = OutcomeMemoryStore()
        record_success_pattern(
            store, route_tier="balanced", provider_id="p1",
            task_types=["summarize", "classify"], confidence_score=0.8,
        )
        results = store.query_successes_by_task_type("summarize")
        assert len(results) == 1
        results_miss = store.query_successes_by_task_type("translate")
        assert len(results_miss) == 0

    def test_query_repairs_by_reason_code(self):
        store = OutcomeMemoryStore()
        record_repair_pattern(
            store, problem_reason_codes=["TIMEOUT"], repair_action="retry",
            success_rate=0.7, task_types=["t"],
        )
        results = store.query_repairs_by_reason_code("TIMEOUT")
        assert len(results) == 1

    def test_suggest_route_tier(self):
        store = OutcomeMemoryStore()
        record_success_pattern(
            store, route_tier="cheap", provider_id="p1",
            task_types=["easy"], confidence_score=0.6,
        )
        record_success_pattern(
            store, route_tier="high_quality", provider_id="p2",
            task_types=["easy"], confidence_score=0.95,
        )
        tier = store.suggest_route_tier("easy")
        assert tier == "high_quality"  # highest confidence

    def test_suggest_route_tier_no_data(self):
        store = OutcomeMemoryStore()
        assert store.suggest_route_tier("unknown") is None

    def test_capacity_limit(self):
        store = OutcomeMemoryStore(max_entries=2)
        record_success_pattern(
            store, route_tier="cheap", provider_id="p1",
            task_types=["t"], confidence_score=0.5,
        )
        record_failure_pattern(
            store, reason_codes=["X"], task_types=["t"]
        )
        with pytest.raises(OutcomeMemoryError):
            record_repair_pattern(
                store, problem_reason_codes=["X"],
                repair_action="retry", success_rate=0.5, task_types=["t"],
            )

    def test_all_families_summary(self):
        store = OutcomeMemoryStore()
        record_success_pattern(
            store, route_tier="cheap", provider_id="p1",
            task_types=["t"], confidence_score=0.5,
        )
        summary = store.all_families_summary()
        assert summary[MemoryFamily.SUCCESS] == 1
        assert summary[MemoryFamily.FAILURE] == 0

    def test_to_dict_completeness(self):
        p = record_failure_pattern(
            OutcomeMemoryStore(),
            reason_codes=["X"], task_types=["t"], occurrence_count=2,
        )
        d = p.to_dict()
        assert d["family"] == MemoryFamily.FAILURE
        assert d["occurrence_count"] == 2
