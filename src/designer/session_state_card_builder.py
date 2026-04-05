from __future__ import annotations

import hashlib
from typing import Any

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE, WORKING_SAVE_ROLE
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec
from src.designer.reason_codes import archive_latest_mixed_referential_reason_notes
from src.designer.models.designer_session_state_card import (
    ApprovalState,
    AvailableResources,
    ConversationContext,
    CurrentFindingsState,
    CurrentRisksState,
    CurrentSelectionState,
    DesignerSessionStateCard,
    ResourceAvailability,
    RevisionState,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel
from src.designer.session_state_persistence import (
    load_persisted_approval_flow_state,
    load_persisted_commit_candidate_state,
    load_persisted_session_state_card,
)

_COMMITTED_SUMMARY_EXPOSED_HISTORY_LIMIT = 2


class DesignerSessionStateCardBuilder:
    def build(
        self,
        *,
        request_text: str,
        artifact: WorkingSaveModel | CommitSnapshotModel | None = None,
        session_id: str | None = None,
        selection_mode: str = "none",
        selected_refs: tuple[str, ...] = (),
        target_scope_mode: str | None = None,
        touch_budget: str = "bounded",
        destructive_edit_allowed: bool = False,
        revision_index: int = 0,
        prior_rejection_reasons: tuple[str, ...] = (),
        retry_reason: str | None = None,
        user_corrections: tuple[str, ...] = (),
    ) -> DesignerSessionStateCard:
        storage_role = getattr(getattr(artifact, 'meta', None), 'storage_role', 'none') if artifact is not None else 'none'
        persisted_card = load_persisted_session_state_card(artifact if isinstance(artifact, WorkingSaveModel) else None)
        persisted_approval = load_persisted_approval_flow_state(artifact if isinstance(artifact, WorkingSaveModel) else None)
        persisted_candidate = load_persisted_commit_candidate_state(artifact if isinstance(artifact, WorkingSaveModel) else None)
        current_working_save = self._build_working_save_reality(artifact)
        fresh_cycle_from_committed_baseline = self._should_start_fresh_cycle_from_committed_baseline(
            request_text=request_text,
            persisted_card=persisted_card,
            persisted_approval=persisted_approval,
        )
        persisted_scope = None if fresh_cycle_from_committed_baseline else (persisted_card.target_scope if persisted_card is not None else None)
        scope_mode = target_scope_mode or (persisted_scope.mode if persisted_scope is not None else self._default_scope_mode(storage_role))
        target_scope = SessionTargetScope(
            mode=scope_mode,
            touch_budget=persisted_scope.touch_budget if persisted_scope is not None else touch_budget,
            allowed_node_refs=tuple(current_working_save.node_list),
            allowed_edge_refs=tuple(current_working_save.edge_list),
            allowed_output_refs=tuple(current_working_save.output_list),
            destructive_edit_allowed=(
                persisted_scope.destructive_edit_allowed if persisted_scope is not None else destructive_edit_allowed
            ),
        )
        available_resources = self._build_available_resources(artifact)
        findings = self._build_findings(artifact)
        risks = self._build_risks(artifact)
        approval_status = persisted_card.approval_state.approval_status if persisted_card is not None else "not_started"
        if fresh_cycle_from_committed_baseline:
            approval_status = "not_started"
        elif persisted_approval is not None and persisted_approval.current_stage == "committed":
            approval_status = "committed"
        elif persisted_candidate is not None and persisted_candidate.ready_for_commit:
            approval_status = "approved"
        approval_state = ApprovalState(
            approval_required=scope_mode not in {"read_only"},
            approval_status=approval_status,
            confirmation_required=bool(findings.confirmation_findings)
            or (
                False
                if fresh_cycle_from_committed_baseline
                else (persisted_card.approval_state.confirmation_required if persisted_card is not None else False)
            ),
            blocking_before_commit=bool(findings.blocking_findings)
            or (
                False
                if fresh_cycle_from_committed_baseline
                else (persisted_card.approval_state.blocking_before_commit if persisted_card is not None else False)
            ),
        )
        objective = ObjectiveSpec(primary_goal=request_text.strip())
        constraints = persisted_card.constraints if persisted_card is not None else ConstraintSet()
        persisted_selection = None if fresh_cycle_from_committed_baseline else (persisted_card.current_selection if persisted_card is not None else None)
        persisted_revision = None if fresh_cycle_from_committed_baseline else (persisted_card.revision_state if persisted_card is not None else None)
        persisted_conversation = persisted_card.conversation_context if persisted_card is not None else None
        notes = dict(persisted_card.notes) if persisted_card is not None else {}
        notes = self._apply_committed_summary_exposure_policy(notes)
        if fresh_cycle_from_committed_baseline:
            notes = self._prepare_notes_for_fresh_cycle_from_committed_baseline(
                notes,
                previous_request_text=(persisted_card.conversation_context.user_request_text if persisted_card is not None else None),
            )
            notes.update({
                "fresh_cycle_from_committed_baseline": True,
                "fresh_cycle_request_text": request_text.strip(),
                "fresh_cycle_baseline_commit_id": notes.get("last_commit_id"),
                "fresh_cycle_housekeeping_applied": True,
            })
        if persisted_candidate is not None:
            notes.update({
                "resume_commit_candidate_ready": persisted_candidate.ready_for_commit,
                "resume_commit_candidate_patch_ref": persisted_candidate.patch_ref,
                "resume_commit_candidate_approval_id": persisted_candidate.approval_id,
                "resume_commit_candidate_working_save_ref": persisted_candidate.candidate_working_save_ref,
            })

        return DesignerSessionStateCard(
            card_version="0.1",
            session_id=session_id or (persisted_card.session_id if persisted_card is not None else self._stable_id("session", request_text)),
            storage_role=storage_role,
            current_working_save=current_working_save,
            current_selection=CurrentSelectionState(
                selection_mode=selection_mode if selection_mode != "none" or not persisted_selection else persisted_selection.selection_mode,
                selected_refs=selected_refs if selected_refs or not persisted_selection else persisted_selection.selected_refs,
            ),
            target_scope=target_scope,
            available_resources=available_resources,
            objective=objective,
            constraints=constraints,
            current_findings=findings,
            current_risks=risks,
            revision_state=RevisionState(
                revision_index=revision_index if revision_index != 0 else (persisted_revision.revision_index if persisted_revision is not None else 0),
                based_on_intent_id=persisted_revision.based_on_intent_id if persisted_revision is not None else None,
                based_on_patch_id=persisted_revision.based_on_patch_id if persisted_revision is not None else None,
                prior_rejection_reasons=prior_rejection_reasons or (persisted_revision.prior_rejection_reasons if persisted_revision is not None else ()),
                retry_reason=retry_reason if retry_reason is not None else (persisted_revision.retry_reason if persisted_revision is not None else None),
                user_corrections=user_corrections or (persisted_revision.user_corrections if persisted_revision is not None else ()),
                last_control_action=persisted_revision.last_control_action if persisted_revision is not None else None,
                last_terminal_status=persisted_revision.last_terminal_status if persisted_revision is not None else None,
                attempt_history=persisted_revision.attempt_history if persisted_revision is not None else (),
            ),
            approval_state=approval_state,
            conversation_context=ConversationContext(
                user_request_text=request_text.strip(),
                clarified_interpretation=(
                    None
                    if fresh_cycle_from_committed_baseline
                    else (persisted_conversation.clarified_interpretation if persisted_conversation is not None else None)
                ),
                unresolved_questions=(
                    ()
                    if fresh_cycle_from_committed_baseline
                    else (persisted_conversation.unresolved_questions if persisted_conversation is not None else ())
                ),
                explicit_user_preferences=(
                    persisted_conversation.explicit_user_preferences if persisted_conversation is not None else ()
                ),
            ),
            notes=notes,
        )

    def _build_working_save_reality(self, artifact: WorkingSaveModel | CommitSnapshotModel | None) -> WorkingSaveReality:
        if artifact is None:
            return WorkingSaveReality(mode="empty_draft")
        circuit = artifact.circuit
        nodes = tuple((node.get('id') or node.get('node_id') or '') for node in circuit.nodes)
        edges = tuple(f"{edge.get('from') or edge.get('from_node')}->{edge.get('to') or edge.get('to_node')}" for edge in circuit.edges)
        outputs = tuple(item.get('name', '') for item in circuit.outputs)
        prompts = tuple(sorted(artifact.resources.prompts.keys()))
        providers = tuple(sorted(artifact.resources.providers.keys()))
        plugins = tuple(sorted(artifact.resources.plugins.keys()))
        summary = f"{len(nodes)} node(s), {len(edges)} edge(s), {len(outputs)} output(s)"
        validity = "draft"
        if getattr(artifact, 'runtime', None) is not None:
            validity = getattr(artifact.runtime, 'status', 'draft')
        savefile_ref = getattr(artifact.meta, 'working_save_id', None) or getattr(artifact.meta, 'commit_id', None) or artifact.meta.name or 'artifact'
        return WorkingSaveReality(
            mode="existing_draft",
            savefile_ref=savefile_ref,
            current_revision=getattr(artifact.meta, 'updated_at', None),
            circuit_summary=summary,
            node_list=nodes,
            edge_list=edges,
            output_list=outputs,
            prompt_refs=prompts,
            provider_refs=providers,
            plugin_refs=plugins,
            draft_validity_status=validity,
        )

    def _build_available_resources(self, artifact: WorkingSaveModel | CommitSnapshotModel | None) -> AvailableResources:
        if artifact is None:
            return AvailableResources()
        return AvailableResources(
            prompts=tuple(ResourceAvailability(id=rid, availability_status="available") for rid in sorted(artifact.resources.prompts.keys())),
            providers=tuple(ResourceAvailability(id=rid, availability_status="available") for rid in sorted(artifact.resources.providers.keys())),
            plugins=tuple(ResourceAvailability(id=rid, availability_status="available") for rid in sorted(artifact.resources.plugins.keys())),
        )

    def _build_findings(self, artifact: WorkingSaveModel | CommitSnapshotModel | None) -> CurrentFindingsState:
        if artifact is None:
            return CurrentFindingsState(finding_summary="No draft findings available.")
        if getattr(artifact, 'runtime', None) is not None:
            errors = getattr(artifact.runtime, 'errors', []) or []
            messages = tuple(str(e) for e in errors)
            return CurrentFindingsState(
                blocking_findings=messages,
                finding_summary=f"{len(messages)} runtime error(s) visible in current draft." if messages else "No blocking findings recorded.",
            )
        return CurrentFindingsState(finding_summary="No blocking findings recorded.")

    def _build_risks(self, artifact: WorkingSaveModel | CommitSnapshotModel | None) -> CurrentRisksState:
        if artifact is None:
            return CurrentRisksState(severity_summary="No known risks.")
        unresolved = ()
        return CurrentRisksState(
            risk_flags=unresolved,
            severity_summary="No high risks currently surfaced.",
            unresolved_high_risks=unresolved,
        )

    def _default_scope_mode(self, storage_role: str) -> str:
        if storage_role == WORKING_SAVE_ROLE:
            return "existing_circuit"
        if storage_role == COMMIT_SNAPSHOT_ROLE:
            return "read_only"
        return "new_circuit"

    def _stable_id(self, prefix: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}-{digest}"




    def _apply_committed_summary_exposure_policy(self, notes: dict[str, Any]) -> dict[str, Any]:
        cleaned = {
            key: value
            for key, value in notes.items()
            if key not in {
                "committed_summary_primary",
                "committed_summary_recent_history",
                "committed_summary_primary_priority",
                "committed_summary_history_priority",
                "committed_summary_exposed_history_count",
                "committed_summary_interpretation_policy",
                "committed_summary_exposure_applied",
            }
        }
        history = cleaned.get("commit_summary_history")
        if not isinstance(history, list) or not history:
            return cleaned
        normalized_history = [dict(item) for item in history if isinstance(item, dict)]
        if not normalized_history:
            return cleaned
        primary = dict(normalized_history[0])
        recent_history = [dict(item) for item in normalized_history[1:1 + _COMMITTED_SUMMARY_EXPOSED_HISTORY_LIMIT]]
        cleaned.update({
            "committed_summary_primary": primary,
            "committed_summary_recent_history": recent_history,
            "committed_summary_primary_priority": "high",
            "committed_summary_history_priority": "low",
            "committed_summary_exposed_history_count": len(recent_history),
            "committed_summary_interpretation_policy": "latest_primary_history_reference_only",
            "committed_summary_reference_resolution_policy": "latest_auto_second_latest_when_explicit_exact_commit_id_match_otherwise_clarify_nonlatest",
            "committed_summary_auto_resolution_modes": ["latest_summary", "second_latest_when_explicit", "exact_commit_id_match"],
            "committed_summary_clarification_required_modes": ["older_change_without_anchor", "nonlatest_reference_without_exact_match"],
            "committed_summary_target_resolution_policy": "single_touched_node_auto_explicit_conflict_clarify_multi_target_clarify",
            "committed_summary_target_auto_resolution_modes": ["single_touched_node_when_no_explicit_target"],
            "committed_summary_target_clarification_required_modes": ["multiple_touched_nodes_without_explicit_target", "explicit_target_conflicts_with_referenced_summary", "referenced_summary_without_touched_nodes"],
            "committed_summary_exposure_applied": True,
        })
        return cleaned

    def _prepare_notes_for_fresh_cycle_from_committed_baseline(
        self,
        notes: dict[str, Any],
        *,
        previous_request_text: str | None,
    ) -> dict[str, Any]:
        archived = archive_latest_mixed_referential_reason_notes(
            notes,
            retention_state="fresh_cycle_history",
            request_text=previous_request_text,
        )
        cleaned = {
            key: value
            for key, value in archived.items()
            if not (key.startswith("fresh_cycle_") or key.startswith("resume_commit_candidate_") or key.startswith("active_baseline_"))
        }
        return cleaned

    def _should_start_fresh_cycle_from_committed_baseline(
        self,
        *,
        request_text: str,
        persisted_card: DesignerSessionStateCard | None,
        persisted_approval: Any | None,
    ) -> bool:
        if persisted_approval is None or persisted_approval.current_stage != "committed":
            return False
        if not request_text.strip():
            return False
        if persisted_card is None:
            return False
        previous_request = persisted_card.conversation_context.user_request_text.strip()
        return previous_request != request_text.strip()
