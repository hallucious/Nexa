from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

DEFAULT_UI_LANGUAGE = "en"
SUPPORTED_UI_LANGUAGES = ("en", "ko")


@dataclass(frozen=True)
class DisplayTextRef:
    text_key: str
    fallback_text: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "designer.request.input_placeholder": "Describe the circuit change you want to make.",
        "designer.request.read_only_disabled": "Designer editing is read-only outside Working Save.",
        "designer.action.submit_request": "Submit request",
        "designer.action.preview_patch": "Preview patch",
        "designer.action.approve_for_commit": "Approve for commit",
        "designer.action.preview_patch_disabled": "Preview requires a patch and passing precheck",
        "designer.action.approve_for_commit_disabled": "Preview or precheck not ready",

        "storage.lifecycle.editing": "Draft currently being edited",
        "storage.lifecycle.review_ready": "Draft is ready for review",
        "storage.lifecycle.approved": "Approved commit snapshot available",
        "storage.lifecycle.executing": "Execution is currently running",
        "storage.lifecycle.executed": "Latest run completed",
        "storage.lifecycle.failed_execution": "Latest run did not complete successfully",
        "storage.lifecycle.unknown": "Storage lifecycle state is incomplete",
        "storage.verifier.data_available": "verifier data available",
        "storage.diagnostics.resume_anchor_requires_revalidation": "resume anchor requires revalidation",
        "storage.diagnostics.stale_commit_reference": "working save references stale commit {commit_id}",
        "storage.diagnostics.mismatched_commit_anchor": "latest execution record is anchored to a different commit snapshot",
        "storage.action.save_working_save": "Save draft",
        "storage.action.submit_for_review": "Submit for review",
        "storage.action.compare_draft_to_commit": "Compare draft to latest commit",
        "storage.action.open_latest_commit": "Open latest commit",
        "storage.action.run_from_commit": "Run from commit",
        "storage.action.select_rollback_target": "Select rollback target",
        "storage.action.open_latest_run": "Open latest run",
        "storage.action.open_trace": "Open trace",
        "storage.action.open_artifacts": "Open artifacts",
        "storage.action.none": "No lifecycle action available",
        "storage.action.compare_runs": "Compare runs",
        "storage.reason.blocking_findings": "Draft still has blocking validation findings",
        "storage.reason.no_commit_snapshot": "No approved commit snapshot available yet",
        "storage.reason.commit_not_approved": "Commit snapshot is not approved",
        "storage.reason.no_trace": "No trace/event stream reference available",
        "storage.reason.no_artifacts": "No execution artifacts recorded",
        "storage.reason.no_storage_artifact": "No storage artifact loaded",
        "storage.reason.second_execution_required": "A second execution record is required",

        "execution.event.execution_started": "execution started",
        "execution.event.execution_started_node": "execution started ({node_id})",
        "execution.event.node_started": "node started ({node_id})",
        "execution.event.node_completed": "node completed ({node_id}): {outcome}",
        "execution.event.execution_terminal": "execution {status}",
        "execution.event.base": "{event_type}",
        "execution.event.base_node": "{event_type} ({node_id})",
        "execution.event.status_suffix": "{base}: {status}",
        "execution.event.error_suffix": "{base}: {error}",
        "execution.progress.no_node_count": "No node-count progress available",
        "execution.context.no_active_node": "No active node",
        "execution.context.executing_node": "Executing {node_id}",
        "execution.control.run": "Run",
        "execution.control.cancel": "Cancel",
        "execution.control.pause": "Pause",
        "execution.control.resume": "Resume",
        "execution.control.replay": "Replay",
        "execution.control.historical_disabled": "Execution record is historical",
        "execution.control.run_not_active": "Run is not active",
        "execution.control.run_not_paused": "Run is not paused",
        "execution.control.replay_unavailable": "Replay unavailable",
        "execution.control.target_not_runnable": "Execution target is not runnable",
        "execution.control.no_active_run": "No active run",
        "execution.control.no_paused_run": "No paused run",
        "execution.control.no_execution_record": "No execution record available",
        "execution.panel.no_execution_record": "No execution record loaded",
        "execution.panel.no_active_execution": "No active execution",

        "validation.group.blocking": "Blocking",
        "validation.group.warning": "Warning",
        "validation.group.confirmation_required": "Confirmation Required",
        "validation.group.info": "Info",
        "validation.target.graph": "graph",
        "validation.title.verifier_report": "Verifier Report",
        "validation.message.verifier_report_recorded": "Verifier report recorded",
        "validation.category.verification": "verification",
        "validation.action.focus_top_issue": "Focus top issue",
        "validation.action.request_revision": "Request revision",
        "validation.action.proceed_to_approval": "Proceed to approval",
        "validation.reason.no_findings": "No findings available",
        "validation.reason.no_revision_required": "No revision required",
        "validation.reason.blocking_issues_remain": "Blocking issues remain",

        "builder.action.save_working_save": "Save Draft",
        "builder.action.review_draft": "Review Draft",
        "builder.action.commit_snapshot": "Commit Snapshot",
        "builder.action.run_current": "Run Current",
        "builder.action.cancel_run": "Cancel Run",
        "builder.action.replay_latest": "Replay Latest",
        "builder.action.open_diff": "Open Diff",
        "builder.action.approve_for_commit": "Approve Proposal",
        "builder.action.request_revision": "Request Revision",
        "builder.reason.only_working_save": "Only working saves can be saved as drafts.",
        "builder.reason.review_requires_ready_working_save": "Draft review requires a working save with non-blocking validation and no active run.",
        "builder.reason.commit_requires_ready_state": "Commit requires a working save, non-blocking review state, no active run, and approval eligibility when designer flow is present.",
        "builder.reason.run_requires_runnable_target": "Running requires a draft or commit target with no blocking validation and no active run.",
        "builder.reason.no_active_run_to_cancel": "No active run is available to cancel.",
        "builder.reason.replay_requires_execution_record": "Replay requires an execution record.",
        "builder.reason.diff_requires_comparison_target": "Diff requires a comparison target such as a commit snapshot or execution record.",
        "builder.reason.designer_not_commit_eligible": "Designer proposal is not yet eligible for commit.",
        "builder.reason.no_active_designer_proposal": "No active designer proposal is available for revision.",
    },
    "ko": {
        "designer.request.input_placeholder": "원하는 회로 변경 내용을 입력하세요.",
        "designer.request.read_only_disabled": "Working Save 외부에서는 Designer 편집이 읽기 전용입니다.",
        "designer.action.submit_request": "요청 제출",
        "designer.action.preview_patch": "패치 미리보기",
        "designer.action.approve_for_commit": "커밋 승인",
        "designer.action.preview_patch_disabled": "미리보기에는 패치와 통과된 사전 점검이 필요합니다",
        "designer.action.approve_for_commit_disabled": "미리보기 또는 사전 점검이 아직 준비되지 않았습니다",

        "storage.lifecycle.editing": "현재 드래프트를 편집 중입니다",
        "storage.lifecycle.review_ready": "드래프트가 검토 준비 상태입니다",
        "storage.lifecycle.approved": "승인된 커밋 스냅샷을 사용할 수 있습니다",
        "storage.lifecycle.executing": "현재 실행 중입니다",
        "storage.lifecycle.executed": "최근 실행이 완료되었습니다",
        "storage.lifecycle.failed_execution": "최근 실행이 정상 완료되지 않았습니다",
        "storage.lifecycle.unknown": "저장 라이프사이클 상태가 불완전합니다",
        "storage.verifier.data_available": "검증기 데이터가 있습니다",
        "storage.diagnostics.resume_anchor_requires_revalidation": "재개 기준점에 재검증이 필요합니다",
        "storage.diagnostics.stale_commit_reference": "working save가 오래된 커밋 {commit_id}를 참조합니다",
        "storage.diagnostics.mismatched_commit_anchor": "최신 실행 기록이 다른 커밋 스냅샷에 연결되어 있습니다",
        "storage.action.save_working_save": "드래프트 저장",
        "storage.action.submit_for_review": "검토 요청",
        "storage.action.compare_draft_to_commit": "드래프트와 최신 커밋 비교",
        "storage.action.open_latest_commit": "최신 커밋 열기",
        "storage.action.run_from_commit": "커밋에서 실행",
        "storage.action.select_rollback_target": "롤백 대상 선택",
        "storage.action.open_latest_run": "최신 실행 열기",
        "storage.action.open_trace": "트레이스 열기",
        "storage.action.open_artifacts": "아티팩트 열기",
        "storage.action.none": "사용 가능한 라이프사이클 작업이 없습니다",
        "storage.action.compare_runs": "실행 비교",
        "storage.reason.blocking_findings": "드래프트에 아직 차단 검증 결과가 남아 있습니다",
        "storage.reason.no_commit_snapshot": "아직 승인된 커밋 스냅샷이 없습니다",
        "storage.reason.commit_not_approved": "커밋 스냅샷이 아직 승인되지 않았습니다",
        "storage.reason.no_trace": "사용 가능한 트레이스/이벤트 스트림 참조가 없습니다",
        "storage.reason.no_artifacts": "기록된 실행 아티팩트가 없습니다",
        "storage.reason.no_storage_artifact": "로드된 저장 아티팩트가 없습니다",
        "storage.reason.second_execution_required": "두 번째 실행 기록이 필요합니다",

        "execution.event.execution_started": "실행 시작",
        "execution.event.execution_started_node": "실행 시작 ({node_id})",
        "execution.event.node_started": "노드 시작 ({node_id})",
        "execution.event.node_completed": "노드 완료 ({node_id}): {outcome}",
        "execution.event.execution_terminal": "실행 {status}",
        "execution.event.base": "{event_type}",
        "execution.event.base_node": "{event_type} ({node_id})",
        "execution.event.status_suffix": "{base}: {status}",
        "execution.event.error_suffix": "{base}: {error}",
        "execution.progress.no_node_count": "노드 수 기반 진행률 정보가 없습니다",
        "execution.context.no_active_node": "활성 노드가 없습니다",
        "execution.context.executing_node": "{node_id} 실행 중",
        "execution.control.run": "실행",
        "execution.control.cancel": "취소",
        "execution.control.pause": "일시정지",
        "execution.control.resume": "재개",
        "execution.control.replay": "재실행",
        "execution.control.historical_disabled": "실행 기록은 과거 기록입니다",
        "execution.control.run_not_active": "현재 활성 실행이 없습니다",
        "execution.control.run_not_paused": "현재 일시정지된 실행이 없습니다",
        "execution.control.replay_unavailable": "재실행을 사용할 수 없습니다",
        "execution.control.target_not_runnable": "이 실행 대상은 실행할 수 없습니다",
        "execution.control.no_active_run": "활성 실행이 없습니다",
        "execution.control.no_paused_run": "일시정지된 실행이 없습니다",
        "execution.control.no_execution_record": "사용 가능한 실행 기록이 없습니다",
        "execution.panel.no_execution_record": "로드된 실행 기록이 없습니다",
        "execution.panel.no_active_execution": "활성 실행이 없습니다",

        "validation.group.blocking": "차단",
        "validation.group.warning": "경고",
        "validation.group.confirmation_required": "확인 필요",
        "validation.group.info": "정보",
        "validation.target.graph": "그래프",
        "validation.title.verifier_report": "검증기 보고서",
        "validation.message.verifier_report_recorded": "검증기 보고서가 기록되었습니다",
        "validation.category.verification": "검증",
        "validation.action.focus_top_issue": "최상위 이슈로 이동",
        "validation.action.request_revision": "수정 요청",
        "validation.action.proceed_to_approval": "승인으로 진행",
        "validation.reason.no_findings": "표시할 결과가 없습니다",
        "validation.reason.no_revision_required": "수정 요청이 필요하지 않습니다",
        "validation.reason.blocking_issues_remain": "차단 이슈가 남아 있습니다",

        "builder.action.save_working_save": "드래프트 저장",
        "builder.action.review_draft": "드래프트 검토",
        "builder.action.commit_snapshot": "커밋 스냅샷",
        "builder.action.run_current": "현재 대상 실행",
        "builder.action.cancel_run": "실행 취소",
        "builder.action.replay_latest": "최신 실행 재실행",
        "builder.action.open_diff": "차이 보기",
        "builder.action.approve_for_commit": "제안 승인",
        "builder.action.request_revision": "수정 요청",
        "builder.reason.only_working_save": "working save만 드래프트로 저장할 수 있습니다.",
        "builder.reason.review_requires_ready_working_save": "드래프트 검토에는 차단 결과가 없는 working save와 비활성 실행 상태가 필요합니다.",
        "builder.reason.commit_requires_ready_state": "커밋에는 working save, 비차단 검토 상태, 비활성 실행 상태, 그리고 Designer 승인 가능 상태가 필요합니다.",
        "builder.reason.run_requires_runnable_target": "실행에는 차단 검증이 없고 활성 실행이 없는 드래프트 또는 커밋 대상이 필요합니다.",
        "builder.reason.no_active_run_to_cancel": "취소할 활성 실행이 없습니다.",
        "builder.reason.replay_requires_execution_record": "재실행에는 실행 기록이 필요합니다.",
        "builder.reason.diff_requires_comparison_target": "차이 보기에는 커밋 스냅샷이나 실행 기록 같은 비교 대상이 필요합니다.",
        "builder.reason.designer_not_commit_eligible": "Designer 제안은 아직 커밋할 수 있는 상태가 아닙니다.",
        "builder.reason.no_active_designer_proposal": "수정 요청할 활성 Designer 제안이 없습니다.",
    },
}


def normalize_ui_language(app_language: str | None) -> str:
    if not app_language:
        return DEFAULT_UI_LANGUAGE
    value = str(app_language).strip().lower().replace('_', '-')
    if value.startswith('ko'):
        return 'ko'
    return 'en'


def ui_language_from_sources(*sources: Any) -> str:
    for source in sources:
        if source is None:
            continue
        parsed_model = getattr(source, 'parsed_model', None)
        if parsed_model is not None:
            source = parsed_model
        ui = getattr(source, 'ui', None)
        metadata = getattr(ui, 'metadata', None)
        if isinstance(metadata, Mapping):
            for key in ('app_language', 'locale', 'language'):
                if metadata.get(key):
                    return normalize_ui_language(str(metadata.get(key)))
    return DEFAULT_UI_LANGUAGE


def make_display_text_ref(text_key: str, *, fallback_text: str | None = None, params: Mapping[str, Any] | None = None) -> DisplayTextRef:
    return DisplayTextRef(text_key=text_key, fallback_text=fallback_text, params=dict(params or {}))


def resolve_display_text(ref: DisplayTextRef, *, app_language: str | None = None, fallback_language: str = DEFAULT_UI_LANGUAGE) -> str:
    language = normalize_ui_language(app_language)
    fallback = normalize_ui_language(fallback_language)
    template = (
        _TRANSLATIONS.get(language, {}).get(ref.text_key)
        or _TRANSLATIONS.get(fallback, {}).get(ref.text_key)
        or ref.fallback_text
        or ref.text_key
    )
    if ref.params:
        return template.format(**ref.params)
    return template


def ui_text(text_key: str, *, app_language: str | None = None, fallback_text: str | None = None, params: Mapping[str, Any] | None = None, **kwargs: Any) -> str:
    merged_params = dict(params or {})
    merged_params.update(kwargs)
    ref = make_display_text_ref(text_key, fallback_text=fallback_text, params=merged_params)
    return resolve_display_text(ref, app_language=app_language)


__all__ = [
    'DEFAULT_UI_LANGUAGE',
    'SUPPORTED_UI_LANGUAGES',
    'DisplayTextRef',
    'make_display_text_ref',
    'normalize_ui_language',
    'resolve_display_text',
    'ui_language_from_sources',
    'ui_text',
]
