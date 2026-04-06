from __future__ import annotations

from pathlib import Path

import pytest

from src.designer.models import (
    ActionSpec,
    AmbiguityAssessmentReport,
    AmbiguityFlag,
    ApprovalPolicy,
    AssumptionPreview,
    AssumptionSpec,
    BehaviorChangePreview,
    ChangeScope,
    CircuitDraftPreview,
    CircuitPatchPlan,
    ConfirmationPreview,
    ConstraintSet,
    CostAssessmentReport,
    CostPreview,
    DecisionPoint,
    DependencyEffectReport,
    DesignerApprovalFlowState,
    DesignerIntent,
    EdgeChangeCard,
    EdgeChangePreview,
    EdgeSummary,
    EvaluatedScope,
    GraphViewModel,
    NodeChangeCard,
    NodeChangePreview,
    ObjectiveSpec,
    OutputChangeCard,
    OutputChangePreview,
    OutputEffectReport,
    PatchOperation,
    PatchRiskReport,
    PrecheckFinding,
    PatchPreviewRequirements,
    PreviewRequirements,
    ResolutionReport,
    ReversibilitySpec,
    RiskFlag,
    RiskPreview,
    StructuralPreview,
    SummaryCard,
    TargetScope,
    UserDecision,
    ValidationPrecheck,
    ValidationRequirements,
    ValidityReport,
)

BASE = Path(__file__).resolve().parents[2]


def make_target_scope(mode: str = "existing_circuit") -> TargetScope:
    return TargetScope(mode=mode, savefile_ref="ws-1" if mode != "new_circuit" else None)


def make_objective() -> ObjectiveSpec:
    return ObjectiveSpec(primary_goal="Build a safer review circuit")


def make_intent(category: str = "MODIFY_CIRCUIT", *, mode: str = "existing_circuit") -> DesignerIntent:
    return DesignerIntent(
        intent_id="intent-1",
        category=category,
        user_request_text="Insert a review node before final output.",
        target_scope=make_target_scope(mode),
        objective=make_objective(),
        constraints=ConstraintSet(human_review_required=True),
        proposed_actions=(
            ActionSpec(
                action_type="add_review_gate",
                target_ref="node.final",
                rationale="Human review is required before final output.",
            ),
        ),
        explanation="This proposal inserts a human review boundary.",
    )



def make_patch_plan() -> CircuitPatchPlan:
    return CircuitPatchPlan(
        patch_id="patch-1",
        patch_mode="modify_existing",
        target_savefile_ref="ws-1",
        summary="Insert a review node before final output.",
        intent_ref="intent-1",
        change_scope=ChangeScope(
            scope_level="bounded",
            touch_mode="structural_edit",
            touched_nodes=("node.final", "node.review"),
            touched_edges=("edge.before_final",),
        ),
        operations=(
            PatchOperation(
                op_id="op-1",
                op_type="create_node",
                target_ref="node.review",
                payload={"kind": "provider"},
                rationale="Create the review node before final output.",
            ),
            PatchOperation(
                op_id="op-2",
                op_type="insert_node_between",
                target_ref="edge.before_final",
                payload={"insert": "node.review"},
                rationale="Insert the review node into the final path.",
                depends_on_ops=("op-1",),
            ),
        ),
        dependency_effects=DependencyEffectReport(newly_created_paths=("node.review -> node.final",)),
        output_effects=OutputEffectReport(modified_outputs=("final_answer",)),
        risk_report=PatchRiskReport(risks=("Slight latency increase",), requires_confirmation=True),
        reversibility=ReversibilitySpec(reversible=True, destructive_ops_present=False),
        preview_requirements=PatchPreviewRequirements(required_preview_areas=("summary", "risk", "output_change")),
        validation_requirements=ValidationRequirements(required_checks=("structure", "provider_resolution")),
    )



def make_precheck(status: str = "confirmation_required") -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="precheck-1",
        patch_ref="patch-1",
        intent_ref="intent-1",
        evaluated_scope=EvaluatedScope(
            mode="existing_circuit_patch",
            savefile_ref="ws-1",
            touched_nodes=("node.final", "node.review"),
            touch_summary="Adds one review node and rewires one edge.",
        ),
        overall_status=status,
        structural_validity=ValidityReport(status="valid", summary="Structure is valid."),
        dependency_validity=ValidityReport(status="valid", summary="Dependencies are valid."),
        input_output_validity=ValidityReport(status="warning", summary="Final output semantics will change."),
        provider_resolution=ResolutionReport(status="resolved", summary="Provider refs resolved."),
        plugin_resolution=ResolutionReport(status="resolved", summary="No plugin changes."),
        safety_review=ValidityReport(status="warning", summary="Review node introduces a manual step."),
        cost_assessment=CostAssessmentReport(status="warning", summary="Expected latency increase."),
        ambiguity_assessment=AmbiguityAssessmentReport(status="confirmation_required", summary="User must confirm manual review."),
        preview_requirements=PreviewRequirements(required_sections=("summary", "confirmation")),
        confirmation_findings=(PrecheckFinding(issue_code="CONFIRM_REVIEW", message="Manual review must be confirmed."),)
        if status == "confirmation_required"
        else (),
        blocking_findings=(PrecheckFinding(issue_code="BLOCKED", message="Broken structure."),) if status == "blocked" else (),
        warning_findings=(PrecheckFinding(issue_code="WARN_1", message="Latency will increase.", severity="low"),),
        recommended_next_actions=("Show preview", "Ask for confirmation"),
        explanation="The proposal is structurally valid but requires confirmation.",
    )



def make_preview() -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-1",
        intent_ref="intent-1",
        patch_ref="patch-1",
        precheck_ref="precheck-1",
        preview_mode="patch_modify",
        summary_card=SummaryCard(
            title="Insert a review node",
            one_sentence_summary="Adds one review node before final output.",
            proposal_type="modify",
            change_scope="bounded",
            touched_node_count=1,
            touched_edge_count=1,
            touched_output_count=1,
            overall_status="confirmation_required",
            user_action_hint="Confirm the manual review step to continue.",
        ),
        structural_preview=StructuralPreview(
            before_exists=True,
            before_node_count=3,
            after_node_count=4,
            before_edge_count=2,
            after_edge_count=3,
            added_nodes=("node.review",),
            modified_nodes=("node.final",),
            added_edges=(EdgeSummary(from_node="node.review", to_node="node.final"),),
            changed_outputs=("final_answer",),
            structural_delta_summary="A review node is inserted before the final node.",
        ),
        node_change_preview=NodeChangePreview(
            cards=(
                NodeChangeCard(
                    node_ref="node.review",
                    change_type="created",
                    after_summary="New manual review node.",
                    why_it_changed="A human review gate is required.",
                    expected_effect="Improves auditability before final output.",
                    criticality="medium",
                ),
            )
        ),
        edge_change_preview=EdgeChangePreview(
            cards=(EdgeChangeCard(from_node="node.review", to_node="node.final", change_type="created"),)
        ),
        output_change_preview=OutputChangePreview(
            cards=(
                OutputChangeCard(
                    output_ref="final_answer",
                    change_type="modified",
                    before_summary="Direct final answer.",
                    after_summary="Final answer after manual review.",
                ),
            )
        ),
        behavior_change_preview=BehaviorChangePreview(
            summary="The circuit pauses for review before final output.",
            expected_effects=("Higher confidence",),
            possible_regressions=("Longer runtime",),
        ),
        risk_preview=RiskPreview(summary="Manual review adds latency.", risks=("Longer turnaround time",), requires_confirmation=True),
        cost_preview=CostPreview(cost_summary="One additional provider-like step.", estimated_cost_change="low increase"),
        assumption_preview=AssumptionPreview(assumptions=("A reviewer will be available.",), default_choices=("Use existing reviewer pool",)),
        confirmation_preview=ConfirmationPreview(required_confirmations=("manual review insertion",), auto_commit_allowed=False),
        graph_view_model=GraphViewModel(node_count=4, edge_count=3),
        explanation="The preview makes the new review boundary explicit.",
    )



def make_approval_state(final_outcome: str = "approved_for_commit", **overrides: object) -> DesignerApprovalFlowState:
    base = dict(
        approval_id="approval-1",
        intent_ref="intent-1",
        patch_ref="patch-1",
        precheck_ref="precheck-1",
        preview_ref="preview-1",
        current_stage="ready_to_commit" if final_outcome == "approved_for_commit" else "awaiting_decision",
        approval_policy=ApprovalPolicy(policy_name="manual_review", allow_auto_commit=False),
        required_decision_points=(DecisionPoint(decision_id="confirm-review", label="Confirm review node insertion"),),
        current_decision_point_id=None,
        user_decisions=(UserDecision(decision_point_id="confirm-review", outcome="approve"),),
        final_outcome=final_outcome,
        precheck_status="confirmation_required",
        blocking_finding_count=0,
        confirmation_finding_count=1,
        confirmation_resolved=True,
        validated_scope_ref="scope-a",
        approved_scope_ref="scope-a",
        scope_revalidated=False,
        destructive_edit_present=False,
        major_output_semantic_change=False,
        critical_provider_replacement=False,
    )
    base.update(overrides)
    return DesignerApprovalFlowState(**base)


# intent

def test_designer_intent_constructs_for_modify_flow() -> None:
    intent = make_intent()
    assert intent.category == "MODIFY_CIRCUIT"
    assert intent.target_scope.mode == "existing_circuit"


@pytest.mark.parametrize(
    ("category", "mode"),
    [
        ("CREATE_CIRCUIT", "existing_circuit"),
        ("EXPLAIN_CIRCUIT", "existing_circuit"),
        ("ANALYZE_CIRCUIT", "node_only"),
        ("MODIFY_CIRCUIT", "read_only"),
        ("REPAIR_CIRCUIT", "new_circuit"),
        ("OPTIMIZE_CIRCUIT", "read_only"),
    ],
)
def test_designer_intent_rejects_scope_category_mismatch(category: str, mode: str) -> None:
    with pytest.raises(ValueError):
        make_intent(category=category, mode=mode)



def test_designer_intent_requires_confirmation_for_ambiguity() -> None:
    with pytest.raises(ValueError):
        DesignerIntent(
            intent_id="intent-2",
            category="MODIFY_CIRCUIT",
            user_request_text="Do something maybe.",
            target_scope=make_target_scope(),
            objective=make_objective(),
            ambiguity_flags=(AmbiguityFlag(type="multiple_targets", description="Two nodes could be changed."),),
            requires_user_confirmation=False,
        )



def test_designer_intent_requires_confirmation_for_high_risk() -> None:
    with pytest.raises(ValueError):
        DesignerIntent(
            intent_id="intent-3",
            category="MODIFY_CIRCUIT",
            user_request_text="Replace provider.",
            target_scope=make_target_scope(),
            objective=make_objective(),
            risk_flags=(RiskFlag(type="provider_change", severity="high", description="Critical provider replacement."),),
            requires_user_confirmation=False,
        )


@pytest.mark.parametrize("bad_value", ["", "BAD_ACTION"])
def test_action_spec_validates_action_type(bad_value: str) -> None:
    with pytest.raises(ValueError):
        ActionSpec(action_type=bad_value, rationale="Needed")


# patch

def test_patch_plan_constructs() -> None:
    patch = make_patch_plan()
    assert patch.patch_mode == "modify_existing"
    assert len(patch.operations) == 2



def test_patch_plan_rejects_duplicate_op_ids() -> None:
    operation = PatchOperation(op_id="dup", op_type="create_node", rationale="Create")
    with pytest.raises(ValueError):
        CircuitPatchPlan(
            patch_id="patch-dup",
            patch_mode="modify_existing",
            target_savefile_ref="ws-1",
            summary="bad patch",
            intent_ref="intent-1",
            change_scope=ChangeScope(scope_level="bounded", touch_mode="structural_edit"),
            operations=(operation, operation),
        )



def test_patch_plan_rejects_unknown_dependencies() -> None:
    with pytest.raises(ValueError):
        CircuitPatchPlan(
            patch_id="patch-deps",
            patch_mode="modify_existing",
            target_savefile_ref="ws-1",
            summary="bad patch",
            intent_ref="intent-1",
            change_scope=ChangeScope(scope_level="bounded", touch_mode="structural_edit"),
            operations=(
                PatchOperation(
                    op_id="op-1",
                    op_type="create_node",
                    rationale="Create node.",
                    depends_on_ops=("missing",),
                ),
            ),
        )


@pytest.mark.parametrize("touch_mode", ["bad", ""]) 
def test_change_scope_validates_touch_mode(touch_mode: str) -> None:
    with pytest.raises(ValueError):
        ChangeScope(scope_level="bounded", touch_mode=touch_mode)



def test_destructive_patch_operation_requires_rationale() -> None:
    with pytest.raises(ValueError):
        PatchOperation(op_id="op-delete", op_type="delete_node")



def test_patch_risk_report_requires_confirmation_for_blocking_risks() -> None:
    with pytest.raises(ValueError):
        PatchRiskReport(blocking_risks=("Breaks output contract",), requires_confirmation=False)



def test_reversibility_spec_requires_strategy_when_irreversible_and_destructive() -> None:
    with pytest.raises(ValueError):
        ReversibilitySpec(reversible=False, destructive_ops_present=True)


# precheck

def test_validation_precheck_constructs() -> None:
    precheck = make_precheck()
    assert precheck.overall_status == "confirmation_required"
    assert precheck.can_proceed_to_preview is True



def test_validation_precheck_rejects_blocked_without_blocking_findings() -> None:
    with pytest.raises(ValueError):
        ValidationPrecheck(
            precheck_id="p1",
            patch_ref="patch-1",
            intent_ref="intent-1",
            evaluated_scope=EvaluatedScope(mode="existing_circuit_patch"),
            overall_status="blocked",
        )



def test_validation_precheck_rejects_confirmation_required_without_confirmation_findings() -> None:
    with pytest.raises(ValueError):
        ValidationPrecheck(
            precheck_id="p2",
            patch_ref="patch-1",
            intent_ref="intent-1",
            evaluated_scope=EvaluatedScope(mode="existing_circuit_patch"),
            overall_status="confirmation_required",
        )



def test_validation_precheck_rejects_blocking_findings_with_nonblocked_status() -> None:
    with pytest.raises(ValueError):
        ValidationPrecheck(
            precheck_id="p3",
            patch_ref="patch-1",
            intent_ref="intent-1",
            evaluated_scope=EvaluatedScope(mode="existing_circuit_patch"),
            overall_status="pass_with_warnings",
            blocking_findings=(PrecheckFinding(issue_code="BLOCKED", message="bad"),),
        )


# preview

def test_preview_constructs() -> None:
    preview = make_preview()
    assert preview.preview_mode == "patch_modify"
    assert preview.summary_card.proposal_type == "modify"


@pytest.mark.parametrize("bad_mode", ["create", "modify", "analysis", ""])
def test_preview_rejects_bad_preview_mode(bad_mode: str) -> None:
    with pytest.raises(ValueError):
        CircuitDraftPreview(
            preview_id="preview-bad",
            intent_ref="intent-1",
            patch_ref="patch-1",
            precheck_ref="precheck-1",
            preview_mode=bad_mode,
            summary_card=SummaryCard(
                title="Bad mode",
                one_sentence_summary="Preview mode must match contract.",
                proposal_type="modify",
                change_scope="bounded",
                touched_node_count=0,
                touched_edge_count=0,
                touched_output_count=0,
            ),
            structural_preview=StructuralPreview(before_exists=True),
        )



def test_preview_summary_card_validates_enums() -> None:
    with pytest.raises(ValueError):
        SummaryCard(
            title="x",
            one_sentence_summary="y",
            proposal_type="bad",
            change_scope="bounded",
            touched_node_count=0,
            touched_edge_count=0,
            touched_output_count=0,
        )
    with pytest.raises(ValueError):
        SummaryCard(
            title="x",
            one_sentence_summary="y",
            proposal_type="modify",
            change_scope="huge",
            touched_node_count=0,
            touched_edge_count=0,
            touched_output_count=0,
        )
    with pytest.raises(ValueError):
        SummaryCard(
            title="x",
            one_sentence_summary="y",
            proposal_type="modify",
            change_scope="bounded",
            touched_node_count=0,
            touched_edge_count=0,
            touched_output_count=0,
            overall_status="ready",
        )



def test_structural_preview_rejects_negative_counts() -> None:
    with pytest.raises(ValueError):
        StructuralPreview(before_exists=True, before_node_count=-1)



def test_node_change_card_validates_change_type_and_criticality() -> None:
    with pytest.raises(ValueError):
        NodeChangeCard(
            node_ref="node.review",
            change_type="modified",
            why_it_changed="Because",
            expected_effect="Effect",
        )
    with pytest.raises(ValueError):
        NodeChangeCard(
            node_ref="node.review",
            change_type="created",
            why_it_changed="Because",
            expected_effect="Effect",
            criticality="urgent",
        )



def test_preview_rejects_hidden_deleted_node() -> None:
    with pytest.raises(ValueError):
        CircuitDraftPreview(
            preview_id="preview-2",
            intent_ref="intent-1",
            patch_ref="patch-1",
            precheck_ref="precheck-1",
            preview_mode="patch_modify",
            summary_card=SummaryCard(
                title="Delete node",
                one_sentence_summary="Deletes one node.",
                proposal_type="modify",
                change_scope="bounded",
                touched_node_count=1,
                touched_edge_count=0,
                touched_output_count=0,
            ),
            structural_preview=StructuralPreview(before_exists=True),
            node_change_preview=NodeChangePreview(
                cards=(
                    NodeChangeCard(
                        node_ref="node.dead",
                        change_type="deleted",
                        before_summary="Old node",
                        why_it_changed="No longer needed.",
                        expected_effect="Simplifies flow.",
                    ),
                )
            ),
        )



def test_preview_rejects_summary_counts_smaller_than_cards() -> None:
    with pytest.raises(ValueError):
        CircuitDraftPreview(
            preview_id="preview-3",
            intent_ref="intent-1",
            patch_ref="patch-1",
            precheck_ref="precheck-1",
            preview_mode="patch_modify",
            summary_card=SummaryCard(
                title="Bad counts",
                one_sentence_summary="Counts too small.",
                proposal_type="modify",
                change_scope="bounded",
                touched_node_count=0,
                touched_edge_count=0,
                touched_output_count=0,
            ),
            structural_preview=StructuralPreview(before_exists=True),
            node_change_preview=NodeChangePreview(
                cards=(
                    NodeChangeCard(
                        node_ref="node.review",
                        change_type="created",
                        why_it_changed="Need review.",
                        expected_effect="Adds review.",
                    ),
                )
            ),
        )


# approval

def test_approval_flow_state_constructs_when_commit_eligible() -> None:
    state = make_approval_state()
    assert state.commit_eligible is True
    assert state.scope_mismatch is False



def test_approval_flow_rejects_unknown_decision_reference() -> None:
    with pytest.raises(ValueError):
        make_approval_state(user_decisions=(UserDecision(decision_point_id="unknown", outcome="approve"),))


@pytest.mark.parametrize(
    "overrides",
    [
        {"precheck_status": "blocked"},
        {"blocking_finding_count": 1},
        {"confirmation_resolved": False},
        {"user_decisions": (), "current_decision_point_id": "confirm-review"},
        {"final_outcome": "rejected", "current_stage": "rejected"},
        {"approved_scope_ref": "scope-b"},
    ],
)
def test_approval_commit_eligible_false_for_boundary_failures(overrides: dict[str, object]) -> None:
    if "final_outcome" not in overrides:
        overrides = {"final_outcome": "pending", "current_stage": "awaiting_decision", **overrides}
    state = make_approval_state(**overrides)
    assert state.commit_eligible is False



def test_approval_commit_eligible_true_when_scope_revalidated() -> None:
    state = make_approval_state(approved_scope_ref="scope-b", scope_revalidated=True)
    assert state.commit_eligible is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"approval_policy": ApprovalPolicy(policy_name="auto", allow_auto_commit=False)},
        {"confirmation_finding_count": 1},
        {"destructive_edit_present": True},
        {"major_output_semantic_change": True},
        {"critical_provider_replacement": True},
    ],
)
def test_auto_commit_allowed_false_when_policy_or_risk_conditions_fail(overrides: dict[str, object]) -> None:
    state = make_approval_state(final_outcome="pending", current_stage="awaiting_decision", **overrides)
    assert state.auto_commit_allowed is False



def test_auto_commit_allowed_true_only_for_clean_boundary() -> None:
    state = make_approval_state(
        final_outcome="pending",
        current_stage="awaiting_decision",
        approval_policy=ApprovalPolicy(policy_name="auto", allow_auto_commit=True),
        required_decision_points=(),
        user_decisions=(),
        precheck_status="pass",
        confirmation_finding_count=0,
        confirmation_resolved=True,
    )
    assert state.auto_commit_allowed is True



def test_approval_rejects_approved_for_commit_when_not_commit_eligible() -> None:
    with pytest.raises(ValueError):
        make_approval_state(approved_scope_ref="scope-b", final_outcome="approved_for_commit")


# packaging / boundaries

def test_designer_package_exports_core_types() -> None:
    import src.designer as designer

    assert hasattr(designer, "DesignerIntent")
    assert hasattr(designer, "CircuitPatchPlan")
    assert hasattr(designer, "ValidationPrecheck")
    assert hasattr(designer, "CircuitDraftPreview")
    assert hasattr(designer, "DesignerApprovalFlowState")


@pytest.mark.parametrize(
    "relative_path",
    [
        "src/designer/models/designer_intent.py",
        "src/designer/models/circuit_patch_plan.py",
        "src/designer/models/validation_precheck.py",
        "src/designer/models/circuit_draft_preview.py",
        "src/designer/models/designer_approval_flow.py",
    ],
)
def test_designer_models_do_not_import_storage_runtime_engine_or_cli(relative_path: str) -> None:
    source = (BASE / relative_path).read_text(encoding="utf-8")
    forbidden = ["src.storage", "src.engine", "src.cli", "src.circuit"]
    assert not any(token in source for token in forbidden)



def test_designer_models_use_frozen_dataclasses() -> None:
    source = (BASE / "src/designer/models/designer_intent.py").read_text(encoding="utf-8")
    assert "@dataclass(frozen=True)" in source

from src.designer.models import (
    GroundedIntent,
    SemanticActionCandidate,
    SemanticIntent,
    SemanticResourceDescriptor,
    SemanticTargetDescriptor,
)


def test_semantic_intent_constructs_with_descriptor_candidates() -> None:
    intent = SemanticIntent(
        semantic_intent_id="semantic-1",
        user_request_text="Have the reviewer use Claude instead.",
        effective_request_text="Have the reviewer use Claude instead.",
        category="MODIFY_CIRCUIT",
        action_candidates=(
            SemanticActionCandidate(
                action_type="replace_provider",
                target_node_descriptor=SemanticTargetDescriptor(label_hint="reviewer", role_hint="review"),
                provider_descriptor=SemanticResourceDescriptor(resource_type="provider", family="claude"),
            ),
        ),
    )
    assert intent.category == "MODIFY_CIRCUIT"
    assert intent.action_candidates[0].provider_descriptor is not None
    assert intent.action_candidates[0].provider_descriptor.family == "claude"


def test_grounded_intent_constructs_from_semantic_intent() -> None:
    semantic = SemanticIntent(
        semantic_intent_id="semantic-2",
        user_request_text="Have the reviewer use Claude instead.",
        effective_request_text="Have the reviewer use Claude instead.",
        category="MODIFY_CIRCUIT",
    )
    grounded = GroundedIntent(
        grounded_intent_id="grounded-1",
        semantic_intent=semantic,
        target_scope=TargetScope(mode="node_only", savefile_ref="ws-1", node_refs=("node.reviewer",)),
        resolved_node_refs=("node.reviewer",),
        matched_provider_id="anthropic:claude-sonnet",
    )
    assert grounded.target_scope.node_refs == ("node.reviewer",)
    assert grounded.matched_provider_id == "anthropic:claude-sonnet"
