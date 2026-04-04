from __future__ import annotations

import hashlib
from typing import Any

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE, WORKING_SAVE_ROLE
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec
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
from src.designer.session_state_persistence import load_persisted_session_state_card


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
        current_working_save = self._build_working_save_reality(artifact)
        persisted_scope = persisted_card.target_scope if persisted_card is not None else None
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
        approval_state = ApprovalState(
            approval_required=scope_mode not in {"read_only"},
            approval_status=persisted_card.approval_state.approval_status if persisted_card is not None else "not_started",
            confirmation_required=bool(findings.confirmation_findings)
            or (persisted_card.approval_state.confirmation_required if persisted_card is not None else False),
            blocking_before_commit=bool(findings.blocking_findings)
            or (persisted_card.approval_state.blocking_before_commit if persisted_card is not None else False),
        )
        objective = ObjectiveSpec(primary_goal=request_text.strip())
        constraints = persisted_card.constraints if persisted_card is not None else ConstraintSet()
        persisted_selection = persisted_card.current_selection if persisted_card is not None else None
        persisted_revision = persisted_card.revision_state if persisted_card is not None else None
        persisted_conversation = persisted_card.conversation_context if persisted_card is not None else None
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
                    persisted_conversation.clarified_interpretation if persisted_conversation is not None else None
                ),
                unresolved_questions=(
                    persisted_conversation.unresolved_questions if persisted_conversation is not None else ()
                ),
                explicit_user_preferences=(
                    persisted_conversation.explicit_user_preferences if persisted_conversation is not None else ()
                ),
            ),
            notes=dict(persisted_card.notes) if persisted_card is not None else {},
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
