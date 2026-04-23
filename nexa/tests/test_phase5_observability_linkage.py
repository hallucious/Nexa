"""test_phase5_observability_linkage.py

Phase 5 구현 검증:
  1. confidence_aggregator → execution_panel  (ConfidenceSummaryView)
  2. policy_explainability → validation_panel (ExplainabilitySummaryView)
  3. router.py RoutingReliabilitySummary + summarize_routing_reliability
  4. commit_snapshot_model CircuitTimelineView + build_circuit_timeline_view
  5. Phase 0: i18n EN/KO 완전 대칭
"""
from __future__ import annotations

import pytest

# ── shared fixtures ────────────────────────────────────────────────────────

from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
    CircuitTimelineView,
    CircuitNodeTimelineEntry,
    build_circuit_timeline_view,
)
from src.storage.models.execution_record_model import (
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultsModel,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import (
    RuntimeModel,
    UIModel,
    WorkingSaveMeta,
    WorkingSaveModel,
)
from src.contracts.nex_contract import ValidationReport


def _commit(
    nodes=None,
    edges=None,
    entry="n1",
    validation_result="passed",
    approval_status="approved",
    _use_default_nodes: bool = True,
) -> CommitSnapshotModel:
    if nodes is None and _use_default_nodes:
        nodes = [{"id": "n1"}, {"id": "n2"}]
    if edges is None and _use_default_nodes:
        edges = [{"source": "n1", "target": "n2"}]
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version="1.0.0",
            storage_role="commit_snapshot",
            commit_id="commit-001",
            source_working_save_id="ws-001",
        ),
        circuit=CircuitModel(
            nodes=nodes or [],
            edges=edges or [],
            entry=entry,
            outputs=[],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result=validation_result, summary={}),
        approval=CommitApprovalModel(
            approval_completed=True,
            approval_status=approval_status,
            summary={},
        ),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _run(status: str = "completed", node_statuses=None) -> ExecutionRecordModel:
    from src.storage.models.execution_record_model import NodeResultCard
    results = []
    if node_statuses:
        for nid, st in node_statuses.items():
            results.append(NodeResultCard(node_id=nid, status=st))
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-06T00:00:00Z",
            started_at="2026-04-06T00:00:00Z",
            finished_at="2026-04-06T00:00:05Z",
            status=status,
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(results=results),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


# ── 1. confidence_aggregator → execution_panel ────────────────────────────


class TestConfidenceSummaryView:

    def test_confidence_summary_present_on_viewmodel(self):
        from src.ui.execution_panel import ExecutionPanelViewModel, ConfidenceSummaryView
        vm = ExecutionPanelViewModel(
            source_mode="idle", storage_role="working_save", execution_status="idle"
        )
        assert hasattr(vm, "confidence_summary")
        assert isinstance(vm.confidence_summary, ConfidenceSummaryView)

    def test_confidence_from_completed_run_with_node_results(self):
        from src.ui.execution_panel import read_execution_panel_view_model
        run = _run(status="completed", node_statuses={"n1": "success", "n2": "success"})
        vm = read_execution_panel_view_model(run)
        cs = vm.confidence_summary
        assert cs.confidence_score is not None
        assert cs.confidence_score == 1.0
        assert cs.threshold_band == "high"
        assert cs.blocking is False
        assert cs.evidence_source == "node_completion_ratio"

    def test_confidence_from_partial_failure(self):
        from src.ui.execution_panel import read_execution_panel_view_model
        run = _run(
            status="completed",
            node_statuses={"n1": "success", "n2": "failed", "n3": "success"},
        )
        vm = read_execution_panel_view_model(run)
        cs = vm.confidence_summary
        assert cs.confidence_score is not None
        # 2 success / 3 total = 0.6667 → medium band
        assert cs.confidence_score == pytest.approx(2 / 3, rel=1e-3)
        assert cs.threshold_band == "medium"
        assert cs.evidence_source == "node_completion_ratio"

    def test_confidence_status_heuristic_when_no_node_results(self):
        from src.ui.execution_panel import read_execution_panel_view_model
        run = _run(status="completed")
        vm = read_execution_panel_view_model(run)
        cs = vm.confidence_summary
        assert cs.confidence_score == 0.8
        assert cs.threshold_band == "high"
        assert cs.evidence_source == "status_heuristic"

    def test_confidence_failed_run(self):
        from src.ui.execution_panel import read_execution_panel_view_model
        run = _run(status="failed")
        vm = read_execution_panel_view_model(run)
        cs = vm.confidence_summary
        assert cs.confidence_score == 0.0
        assert cs.threshold_band == "critical_low"
        assert cs.blocking is True

    def test_confidence_from_observability_payload(self):
        from src.ui.execution_panel import read_execution_panel_view_model
        run = _run(status="completed")
        # inject pre-computed confidence into observability
        object.__setattr__(
            run.observability,
            "confidence_summary",
            {"confidence_score": 0.92, "explanation": "engine computed"},
        )
        vm = read_execution_panel_view_model(run)
        cs = vm.confidence_summary
        assert cs.confidence_score == 0.92
        assert cs.threshold_band == "high"
        assert cs.evidence_source == "observability"

    def test_confidence_empty_when_no_execution_record(self):
        from src.ui.execution_panel import read_execution_panel_view_model, ConfidenceSummaryView
        from src.storage.models.working_save_model import WorkingSaveModel
        ws = WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version="1.0.0",
                storage_role="working_save",
                working_save_id="ws-1",
                name="Draft",
            ),
            circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
            resources=ResourcesModel(prompts={}, providers={}, plugins={}),
            state=StateModel(input={}, working={}, memory={}),
            runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
            ui=UIModel(layout={}, metadata={}),
        )
        vm = read_execution_panel_view_model(ws)
        assert vm.confidence_summary == ConfidenceSummaryView()


# ── 2. policy_explainability → validation_panel ───────────────────────────


class TestExplainabilitySummaryView:

    def test_explainability_present_on_viewmodel(self):
        from src.ui.validation_panel import ValidationPanelViewModel, ExplainabilitySummaryView
        vm = ValidationPanelViewModel(
            source_mode="unknown", storage_role="working_save", overall_status="unknown"
        )
        assert hasattr(vm, "explainability")
        assert isinstance(vm.explainability, ExplainabilitySummaryView)

    def test_explainability_pass_on_clean_report(self):
        from src.ui.validation_panel import read_validation_panel_view_model
        from src.storage.models.working_save_model import WorkingSaveModel
        ws = WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version="1.0.0",
                storage_role="working_save",
                working_save_id="ws-1",
                name="Draft",
            ),
            circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
            resources=ResourcesModel(prompts={}, providers={}, plugins={}),
            state=StateModel(input={}, working={}, memory={}),
            runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
            ui=UIModel(layout={}, metadata={}),
        )
        report = ValidationReport(
            role="working_save",
            findings=[],
            blocking_count=0,
            warning_count=0,
            result="passed",
        )
        vm = read_validation_panel_view_model(ws, validation_report=report)
        exp = vm.explainability
        assert exp.has_explainability is True
        assert exp.status == "PASS"
        assert "PASS" in exp.summary

    def test_explainability_fail_on_blocking_findings(self):
        from src.ui.validation_panel import read_validation_panel_view_model
        from src.contracts.nex_contract import ValidationFinding
        from src.storage.models.working_save_model import WorkingSaveModel
        ws = WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version="1.0.0",
                storage_role="working_save",
                working_save_id="ws-1",
                name="Draft",
            ),
            circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
            resources=ResourcesModel(prompts={}, providers={}, plugins={}),
            state=StateModel(input={}, working={}, memory={}),
            runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
            ui=UIModel(layout={}, metadata={}),
        )
        finding = ValidationFinding(
            code="missing_provider",
            category="structural",
            severity="high",
            blocking=True,
            location="n1",
            message="Node n1 has no provider",
        )
        report = ValidationReport(
            role="working_save",
            findings=[finding],
            blocking_count=1,
            warning_count=0,
            result="blocked",
        )
        vm = read_validation_panel_view_model(ws, validation_report=report)
        exp = vm.explainability
        assert exp.has_explainability is True
        assert exp.status == "FAIL"
        assert len(exp.structural_issues) >= 1

    def test_explainability_empty_without_sources(self):
        from src.ui.validation_panel import read_validation_panel_view_model, ExplainabilitySummaryView
        from src.storage.models.working_save_model import WorkingSaveModel
        ws = WorkingSaveModel(
            meta=WorkingSaveMeta(
                format_version="1.0.0",
                storage_role="working_save",
                working_save_id="ws-1",
                name="Draft",
            ),
            circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
            resources=ResourcesModel(prompts={}, providers={}, plugins={}),
            state=StateModel(input={}, working={}, memory={}),
            runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
            ui=UIModel(layout={}, metadata={}),
        )
        vm = read_validation_panel_view_model(ws)
        assert vm.explainability == ExplainabilitySummaryView()


# ── 3. router.py RoutingReliabilitySummary ────────────────────────────────


class TestRoutingReliabilitySummary:

    def test_summary_single_success(self):
        from src.providers.router import RoutingAttempt, RoutingReliabilitySummary, summarize_routing_reliability
        attempts = [
            RoutingAttempt(
                attempt_index=0,
                adapter_name="anthropic",
                result="success",
                retryable=False,
                reason_code=None,
                error_type=None,
            )
        ]
        summary = summarize_routing_reliability(attempts)
        assert isinstance(summary, RoutingReliabilitySummary)
        assert summary.total_attempts == 1
        assert summary.successful_attempts == 1
        assert summary.failed_attempts == 0
        assert summary.success_rate == 1.0
        assert summary.winning_adapter == "anthropic"
        assert summary.terminal_reason_code is None

    def test_summary_fallback_success(self):
        from src.providers.router import RoutingAttempt, summarize_routing_reliability
        attempts = [
            RoutingAttempt(0, "openai", "failure", True, "AI.timeout", "TimeoutError"),
            RoutingAttempt(1, "anthropic", "success", False, None, None),
        ]
        summary = summarize_routing_reliability(attempts)
        assert summary.total_attempts == 2
        assert summary.successful_attempts == 1
        assert summary.failed_attempts == 1
        assert summary.retryable_failures == 1
        assert summary.non_retryable_failures == 0
        assert summary.success_rate == 0.5
        assert summary.winning_adapter == "anthropic"
        assert summary.attempted_adapters == ("openai", "anthropic")

    def test_summary_all_failed(self):
        from src.providers.router import RoutingAttempt, summarize_routing_reliability
        attempts = [
            RoutingAttempt(0, "openai", "failure", True, "AI.timeout", "TimeoutError"),
            RoutingAttempt(1, "anthropic", "failure", False, "AI.auth_error", "AuthError"),
        ]
        summary = summarize_routing_reliability(attempts)
        assert summary.successful_attempts == 0
        assert summary.failed_attempts == 2
        assert summary.success_rate == 0.0
        assert summary.winning_adapter is None
        assert summary.terminal_reason_code == "AI.auth_error"

    def test_summary_empty_attempts(self):
        from src.providers.router import summarize_routing_reliability
        summary = summarize_routing_reliability([])
        assert summary.total_attempts == 0
        assert summary.success_rate == 0.0
        assert summary.winning_adapter is None

    def test_summary_to_dict_is_serializable(self):
        from src.providers.router import RoutingAttempt, summarize_routing_reliability
        attempts = [RoutingAttempt(0, "openai", "success", False, None, None)]
        summary = summarize_routing_reliability(attempts)
        d = summary.to_dict()
        assert isinstance(d, dict)
        assert d["total_attempts"] == 1
        assert d["success_rate"] == 1.0
        assert d["winning_adapter"] == "openai"
        assert isinstance(d["attempted_adapters"], list)


# ── 4. CircuitTimelineView ────────────────────────────────────────────────


class TestCircuitTimelineView:

    def test_build_basic_timeline(self):
        snapshot = _commit(
            nodes=[{"id": "n1", "label": "Extract"}, {"id": "n2", "label": "Summarize"}],
            edges=[{"source": "n1", "target": "n2"}],
            entry="n1",
        )
        tl = build_circuit_timeline_view(snapshot)
        assert isinstance(tl, CircuitTimelineView)
        assert tl.has_timeline is True
        assert tl.commit_id == "commit-001"
        assert tl.total_node_count == 2
        assert tl.entry_node_id == "n1"
        assert tl.edge_count == 1
        assert tl.validation_result == "passed"
        assert tl.approval_status == "approved"

    def test_node_ordering_respects_entry(self):
        snapshot = _commit(
            nodes=[{"id": "n2"}, {"id": "n1"}],
            edges=[{"source": "n1", "target": "n2"}],
            entry="n1",
        )
        tl = build_circuit_timeline_view(snapshot)
        ids = [e.node_id for e in tl.node_entries]
        assert ids.index("n1") < ids.index("n2")

    def test_dependency_counts(self):
        snapshot = _commit(
            nodes=[{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
            edges=[
                {"source": "n1", "target": "n2"},
                {"source": "n1", "target": "n3"},
            ],
            entry="n1",
        )
        tl = build_circuit_timeline_view(snapshot)
        by_id = {e.node_id: e for e in tl.node_entries}
        # n1 has 2 dependents, n2 and n3 each have 1 dependency
        assert by_id["n1"].dependent_count == 2
        assert by_id["n2"].dependency_count == 1
        assert by_id["n3"].dependency_count == 1

    def test_node_resource_flags(self):
        snapshot = _commit(
            nodes=[
                {"id": "n1", "resources": {"prompt": "p1", "provider": "openai"}},
                {"id": "n2", "resources": {"plugin": "formatter"}},
            ],
            edges=[{"source": "n1", "target": "n2"}],
            entry="n1",
        )
        tl = build_circuit_timeline_view(snapshot)
        by_id = {e.node_id: e for e in tl.node_entries}
        assert by_id["n1"].has_prompt is True
        assert by_id["n1"].has_provider is True
        assert by_id["n1"].has_plugin is False
        assert by_id["n2"].has_plugin is True
        assert by_id["n2"].has_prompt is False

    def test_empty_circuit(self):
        snapshot = _commit(nodes=[], edges=[], entry=None, _use_default_nodes=False)
        tl = build_circuit_timeline_view(snapshot)
        assert tl.total_node_count == 0
        assert tl.edge_count == 0
        assert tl.entry_node_id is None

    def test_timeline_is_frozen(self):
        snapshot = _commit()
        tl = build_circuit_timeline_view(snapshot)
        with pytest.raises(Exception):
            tl.commit_id = "mutated"  # type: ignore[misc]

    def test_node_entries_are_circuit_node_timeline_entries(self):
        snapshot = _commit()
        tl = build_circuit_timeline_view(snapshot)
        for entry in tl.node_entries:
            assert isinstance(entry, CircuitNodeTimelineEntry)


# ── 5. Phase 0: i18n EN/KO 완전 대칭 ─────────────────────────────────────


class TestI18nParity:

    def test_en_ko_key_parity(self):
        from src.ui.i18n import _TRANSLATIONS
        en_keys = set(_TRANSLATIONS.get("en", {}).keys())
        ko_keys = set(_TRANSLATIONS.get("ko", {}).keys())
        missing_in_ko = en_keys - ko_keys
        assert missing_in_ko == set(), (
            f"KO is missing {len(missing_in_ko)} keys: {sorted(missing_in_ko)[:10]}"
        )

    def test_closure_stage_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("closure.stage.approval", app_language="ko") == "승인"
        assert ui_text("closure.stage.commit", app_language="ko") == "커밋"
        assert ui_text("closure.stage.run", app_language="ko") == "실행"

    def test_e2e_checkpoint_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("e2e.checkpoint.artifact", app_language="ko") == "아티팩트"
        assert ui_text("e2e.checkpoint.trace", app_language="ko") == "추적"

    def test_friendly_error_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("friendly_error.API_KEY_MISSING.title", app_language="ko") == "AI 연결 필요"
        assert ui_text("friendly_error.QUOTA_EXCEEDED.title", app_language="ko") == "사용 한도 초과"
        assert ui_text("friendly_error.NETWORK_ERROR.action", app_language="ko") == "다시 시도"

    def test_handoff_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("handoff.status.complete", app_language="ko") == "다음 단계 핸드오프 완료"
        assert ui_text("handoff.status.blocked", app_language="ko") == "다음 단계 핸드오프 차단됨"

    def test_runbook_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("runbook.status.ready", app_language="ko") == "런북 준비됨"
        assert ui_text("runbook.entry_status.active", app_language="ko") == "활성"

    def test_template_gallery_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("template_gallery.title", app_language="ko") == "스타터 워크플로우"
        assert ui_text("template_gallery.action.use_template", app_language="ko") == "템플릿 사용"

    def test_provider_setup_keys_ko(self):
        from src.ui.i18n import ui_text
        assert ui_text("provider_setup.title", app_language="ko") == "AI 모델 연결"
        assert ui_text("provider_setup.option.status.connected", app_language="ko") == "연결됨"
