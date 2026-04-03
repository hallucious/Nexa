from __future__ import annotations

from typing import Literal

DesignerIntentCategory = Literal[
    "CREATE_CIRCUIT",
    "MODIFY_CIRCUIT",
    "EXPLAIN_CIRCUIT",
    "ANALYZE_CIRCUIT",
    "REPAIR_CIRCUIT",
    "OPTIMIZE_CIRCUIT",
]
TargetScopeMode = Literal[
    "new_circuit",
    "existing_circuit",
    "subgraph_only",
    "node_only",
    "read_only",
]
ChangeScopeLevel = Literal["minimal", "bounded", "broad"]
TouchMode = Literal["read_only", "append_only", "structural_edit", "destructive_edit"]
AssumptionSeverity = Literal["low", "medium", "high"]
RiskSeverity = Literal["low", "medium", "high"]
PatchMode = Literal["create_draft", "modify_existing", "repair_existing", "optimize_existing"]
PrecheckOverallStatus = Literal["pass", "pass_with_warnings", "confirmation_required", "blocked"]
PreviewMode = Literal[
    "draft_create",
    "patch_modify",
    "repair_preview",
    "optimize_preview",
    "analysis_only",
]
SummaryProposalType = Literal["create", "modify", "repair", "optimize", "analyze"]
SummaryOverallStatus = Literal[
    "safe_to_preview",
    "warning_present",
    "confirmation_required",
    "blocked",
]
NodeChangeType = Literal[
    "created",
    "deleted",
    "provider_changed",
    "prompt_changed",
    "plugin_changed",
    "parameter_changed",
    "role_changed",
    "unchanged_contextually",
]
NodeCriticality = Literal["low", "medium", "high"]
DecisionOutcome = Literal[
    "approve",
    "reject",
    "request_revision",
    "narrow_scope",
    "choose_interpretation",
    "abort",
]
ApprovalStage = Literal[
    "awaiting_precheck",
    "awaiting_preview",
    "awaiting_decision",
    "ready_to_commit",
    "rejected",
    "aborted",
    "committed",
]
ApprovalFinalOutcome = Literal[
    "pending",
    "approved_for_commit",
    "rejected",
    "revision_requested",
    "aborted",
]

DESIGNER_INTENT_CATEGORIES = {
    "CREATE_CIRCUIT",
    "MODIFY_CIRCUIT",
    "EXPLAIN_CIRCUIT",
    "ANALYZE_CIRCUIT",
    "REPAIR_CIRCUIT",
    "OPTIMIZE_CIRCUIT",
}
TARGET_SCOPE_MODES = {
    "new_circuit",
    "existing_circuit",
    "subgraph_only",
    "node_only",
    "read_only",
}
CHANGE_SCOPE_LEVELS = {"minimal", "bounded", "broad"}
TOUCH_MODES = {"read_only", "append_only", "structural_edit", "destructive_edit"}
ASSUMPTION_SEVERITIES = {"low", "medium", "high"}
RISK_SEVERITIES = {"low", "medium", "high"}
PATCH_MODES = {"create_draft", "modify_existing", "repair_existing", "optimize_existing"}
PRECHECK_OVERALL_STATUSES = {"pass", "pass_with_warnings", "confirmation_required", "blocked"}
PREVIEW_MODES = {
    "draft_create",
    "patch_modify",
    "repair_preview",
    "optimize_preview",
    "analysis_only",
}
SUMMARY_PROPOSAL_TYPES = {"create", "modify", "repair", "optimize", "analyze"}
SUMMARY_OVERALL_STATUSES = {
    "safe_to_preview",
    "warning_present",
    "confirmation_required",
    "blocked",
}
NODE_CHANGE_TYPES = {
    "created",
    "deleted",
    "provider_changed",
    "prompt_changed",
    "plugin_changed",
    "parameter_changed",
    "role_changed",
    "unchanged_contextually",
}
NODE_CRITICALITIES = {"low", "medium", "high"}

ACTION_TYPES = {
    "create_node",
    "delete_node",
    "update_node",
    "connect_nodes",
    "disconnect_nodes",
    "insert_node_between",
    "replace_provider",
    "attach_plugin",
    "detach_plugin",
    "set_prompt",
    "set_parameter",
    "add_review_gate",
    "remove_review_gate",
    "define_output",
    "rename_component",
}
PATCH_OPERATION_TYPES = {
    "create_node",
    "delete_node",
    "update_node_metadata",
    "replace_node_component",
    "set_node_prompt",
    "set_node_provider",
    "attach_node_plugin",
    "detach_node_plugin",
    "connect_nodes",
    "disconnect_nodes",
    "insert_node_between",
    "move_output_binding",
    "define_output_binding",
    "remove_output_binding",
    "set_parameter",
    "rename_node",
    "annotate_node",
    "create_subgraph",
    "delete_subgraph",
}

APPROVAL_STAGES = {
    "awaiting_precheck",
    "awaiting_preview",
    "awaiting_decision",
    "ready_to_commit",
    "rejected",
    "aborted",
    "committed",
}
DECISION_OUTCOMES = {
    "approve",
    "reject",
    "request_revision",
    "narrow_scope",
    "choose_interpretation",
    "abort",
}
APPROVAL_FINAL_OUTCOMES = {
    "pending",
    "approved_for_commit",
    "rejected",
    "revision_requested",
    "aborted",
}
