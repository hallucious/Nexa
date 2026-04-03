# Patch Plan to Precheck Evaluation Rules v0.1

## Recommended save path
`docs/specs/designer/patch_plan_to_precheck_evaluation_rules.md`

## 1. Purpose

This document defines the canonical evaluation rules from:

- `CircuitPatchPlan`
to
- `ValidationPrecheck`

Its purpose is to ensure that a proposed circuit patch is evaluated
as an explicit future-state proposal before preview, approval, or commit.

The evaluation layer exists between:

User Request
-> Designer Session State Card
-> Session Card to Intent Mapping
-> Normalized Intent
-> Intent to Patch Mapping
-> CircuitPatchPlan
-> Patch Plan to Precheck Evaluation
-> ValidationPrecheck
-> Draft Preview
-> Approval
-> Commit

## 2. Core Decision

`ValidationPrecheck` must be produced by evaluating the proposed future state implied by `CircuitPatchPlan`.

Official rule:

- precheck does not execute the circuit
- precheck evaluates the patch as a proposed next state
- blocking findings must remain blocking
- warnings and confirmation-required risks must remain distinct
- precheck must not silently repair or normalize the patch

In short:

`ValidationPrecheck` is a structured proposal-evaluation result,
not a hidden auto-fix stage.

## 3. Mapping Principles

### 3.1 Patch is authoritative
Precheck evaluation must begin from:
- `patch_mode`
- `change_scope`
- `operations`
- `dependency_effects`
- `output_effects`
- `risk_report`
- `reversibility`
- `preview_requirements`
- `validation_requirements`

### 3.2 Precheck evaluates proposed future structure
The evaluator must reason about:
- current state
plus
- explicit patch operations
as a proposed merged future state

It must not evaluate only the current state.

### 3.3 Precheck must stay diagnostic
It may detect problems, classify severity, and recommend next actions,
but it must not silently rewrite the patch.

### 3.4 Evaluation must preserve boundaries
Precheck may not:
- bypass scope limits
- convert blocked status into pass
- reinterpret destructive operations as non-destructive
- hide resource resolution failures

### 3.5 Findings must be structured
Precheck must separate:
- blocking findings
- warning findings
- confirmation-required findings

## 4. Source and Target Objects

### 4.1 Source
`CircuitPatchPlan`

Canonical source fields:

- `patch_id`
- `patch_mode`
- `target_savefile_ref`
- `target_circuit_ref`
- `based_on_revision`
- `summary`
- `intent_ref`
- `change_scope`
- `operations`
- `dependency_effects`
- `output_effects`
- `risk_report`
- `reversibility`
- `preview_requirements`
- `validation_requirements`

### 4.2 Target
`ValidationPrecheck`

Canonical target fields:

- `precheck_id`
- `patch_ref`
- `intent_ref`
- `evaluated_scope`
- `overall_status`
- `structural_validity`
- `dependency_validity`
- `input_output_validity`
- `provider_resolution`
- `plugin_resolution`
- `safety_review`
- `cost_assessment`
- `ambiguity_assessment`
- `preview_requirements`
- `blocking_findings`
- `warning_findings`
- `confirmation_findings`
- `recommended_next_actions`
- `explanation`

## 5. Top-Level Mapping Table

### 5.1 `patch_id` -> `patch_ref`
Rule:
- copy directly

### 5.2 `intent_ref` -> `intent_ref`
Rule:
- copy directly

### 5.3 `change_scope` -> `evaluated_scope`
Rule:
- preserve scope semantics
- include touched refs and touch summary
- do not widen evaluated scope beyond the patch

### 5.4 `preview_requirements` -> `preview_requirements`
Rule:
- carry forward existing preview requirements
- strengthen them if precheck finds new structural, safety, or confirmation issues

### 5.5 `risk_report` -> `safety_review`, `cost_assessment`, `confirmation_findings`
Rule:
- existing patch risks influence these reports
- risks do not mechanically copy into one field only
- precheck may escalate severity based on concrete proposal implications

### 5.6 `validation_requirements` -> all major precheck reports
Rule:
- patch-specified validation targets guide which dimensions must be evaluated
- precheck must not ignore declared validation requirements

## 6. Future-State Construction Rules

Precheck evaluation depends on a conceptual future-state model.

### 6.1 Current-state baseline
Start from the current referenced draft or structural target.

### 6.2 Apply patch conceptually
Apply all patch operations conceptually in order to construct the proposed future state.

### 6.3 No hidden normalization
Do not repair missing fields, broken edges, unresolved outputs, or invalid references unless such repair is explicitly part of the patch.

### 6.4 Failed future-state construction
If future-state construction fails because the patch itself is incomplete or contradictory,
the result must become blocked or confirmation-required depending on severity.

## 7. Evaluated Scope Mapping Rules

### 7.1 Scope preservation
`evaluated_scope` must include:
- mode
- touched nodes
- touched edges
- touched outputs
- concise touch summary

### 7.2 Scope compliance checks
Precheck must verify that actual patch operations do not exceed declared change scope.

### 7.3 Scope mismatch
If operations touch refs outside declared scope:
- this is at least a warning
- if material, it becomes blocking or confirmation-required depending on impact

## 8. Overall Status Resolution Rules

### 8.1 `pass`
Use only when:
- no blocking findings
- no warning findings that materially require user attention
- no confirmation-required findings

### 8.2 `pass_with_warnings`
Use when:
- no blocking findings
- warnings exist
- no user confirmation is structurally required

### 8.3 `confirmation_required`
Use when:
- no blocking findings
- at least one material ambiguity, destructive change, or sensitive risk requires explicit user decision

### 8.4 `blocked`
Use when:
- any blocking structural, resolution, or boundary violation exists

### 8.5 Status priority
If multiple statuses seem plausible, apply:

1. blocked
2. confirmation_required
3. pass_with_warnings
4. pass

## 9. Structural Validity Evaluation Rules

`structural_validity` must answer whether the proposed future graph is structurally coherent.

The evaluator should inspect at least:

- node existence for all touched refs
- edge endpoint validity
- missing required node components
- illegal delete/connect combinations
- invalid insert or replacement patterns
- impossible graph topology implied by operations
- destructive-edit boundary compliance

Typical blocking conditions:
- operation targets nonexistent object without valid creation sequence
- delete breaks required path and no replacement path is provided
- illegal structural contradictions exist across operations

Typical warning conditions:
- structurally valid but overly broad patch
- reversible but topology becomes significantly more complex

## 10. Dependency Validity Evaluation Rules

`dependency_validity` must evaluate proposed dependency behavior.

The evaluator should inspect at least:

- broken upstream/downstream paths
- cycles introduced by new edges
- unresolved fan-in/fan-out risks
- dependency effects declared by patch vs actual implied effects
- likely sequencing implications

Typical blocking conditions:
- newly introduced cycle
- disconnected required execution path
- dependency forecast and actual operation implications materially conflict

Typical warning conditions:
- dependency fan-out sharply increases
- ordering sensitivity may rise
- multi-branch merge becomes harder to inspect

## 11. Input / Output Validity Evaluation Rules

`input_output_validity` must evaluate whether the proposed future state still has valid input and output behavior.

The evaluator should inspect at least:

- output source existence
- output binding coherence after touched operations
- moved output validity
- removed output consequences
- newly added outputs completeness
- input expectations for newly inserted nodes

Typical blocking conditions:
- output source removed without replacement
- output path no longer resolves
- inserted node requires missing input with no source

Typical confirmation-required conditions:
- output behavior materially changes, but the patch is structurally valid
- output remains valid but meaning changes enough that explicit user confirmation is warranted

## 12. Provider Resolution Evaluation Rules

`provider_resolution` must inspect provider references in the proposed future state.

The evaluator should inspect at least:

- provider existence
- provider availability status
- provider compatibility with touched node intent
- provider restrictions from constraints or policy
- changed provider risk relative to prior state

Typical blocking conditions:
- provider missing
- provider forbidden by constraints
- provider replacement unresolved

Typical warning conditions:
- provider exists but may increase cost or reduce determinism
- provider switch is valid but changes behavior profile

## 13. Plugin Resolution Evaluation Rules

`plugin_resolution` must inspect plugin references in the proposed future state.

The evaluator should inspect at least:

- plugin existence
- plugin availability
- plugin restrictions
- attach/detach correctness
- new plugin dependency implications
- plugin usage compatibility with target node intent

Typical blocking conditions:
- plugin missing
- plugin forbidden
- plugin attachment operation invalid for target context

Typical warning conditions:
- plugin exists but likely increases complexity
- plugin attach is valid but may require additional review

## 14. Safety Review Evaluation Rules

`safety_review` must inspect whether the patch introduces policy, human-review, or operational safety concerns.

The evaluator should inspect at least:

- destructive edit pressure
- sensitive-domain handling requirements
- human review requirements
- hidden authority implications
- scope escalation pressure
- approval boundary integrity

Typical confirmation-required conditions:
- destructive edit allowed and meaningful
- human review is required for this proposal direction
- safety-sensitive change is valid but should not auto-advance

Typical blocking conditions:
- patch implies forbidden authority
- patch violates explicit safety restrictions
- patch would bypass required approval boundary

## 15. Cost Assessment Evaluation Rules

`cost_assessment` must evaluate expected cost implications of the proposed patch.

The evaluator should inspect at least:

- likely node count increase
- provider cost profile shifts
- plugin cost implications
- added review/branching complexity
- likely latency impact if relevant
- mismatch with declared cost limit

Typical warning conditions:
- cost likely increases beyond preference
- latency likely rises materially

Typical confirmation-required conditions:
- cost increase is large but potentially acceptable with explicit approval

Typical blocking conditions:
- declared hard cost limit is violated by the proposed structure and no compliant alternative exists inside patch scope

## 16. Ambiguity Assessment Evaluation Rules

`ambiguity_assessment` must evaluate whether the patch remains too ambiguous to move safely toward preview/approval.

The evaluator should inspect at least:

- unresolved interpretation branches
- unresolved resource choice
- unresolved output meaning changes
- operation sequence with multiple equally plausible futures
- assumptions that materially affect structure

Typical confirmation-required conditions:
- ambiguity remains but bounded preview is still meaningful

Typical blocking conditions:
- ambiguity is so severe that no stable proposed future state can be evaluated coherently

## 17. Findings Classification Rules

### 17.1 Blocking findings
A finding is blocking when it prevents safe or coherent progression to approval/commit.

Examples:
- invalid structural merge
- unresolved provider/plugin
- broken output path
- forbidden destructive behavior
- scope violation
- cycle introduction

### 17.2 Warning findings
A finding is warning-level when the patch remains evaluable and potentially acceptable,
but user attention is still warranted.

Examples:
- cost drift
- complexity increase
- broader-than-ideal touch set
- determinism reduction risk
- review depth increase with latency impact

### 17.3 Confirmation findings
A finding is confirmation-required when:
- proposal is structurally valid
- but explicit user choice is still required

Examples:
- destructive edit with meaningful tradeoff
- output meaning change
- cost/safety tradeoff
- ambiguity between two still-valid structural directions

## 18. Recommended Next Actions Mapping Rules

`recommended_next_actions` should be derived from findings.

Typical actions include:
- approve
- reject
- request revision
- narrow scope
- choose interpretation
- provide missing resource
- relax conflicting constraint
- request safer alternative
- keep current structure unchanged

Rules:
- recommendations must reflect the actual status
- blocked proposals must not recommend direct approval
- confirmation-required proposals should make the needed decision explicit

## 19. Explanation Mapping Rules

The `explanation` field should summarize:

1. what future state was evaluated
2. why status became pass / warning / confirmation_required / blocked
3. what the main structural/resource/output issues are
4. what the user must do next if anything

The explanation must be user-verifiable from the patch and findings.
It must not refer to hidden internal reasoning.

## 20. Strengthening Rules

Precheck may strengthen, but not weaken, patch safety requirements.

It may:
- escalate risk severity
- add preview requirements
- add confirmation requirements
- add validation findings

It must not:
- erase existing confirmation needs
- downgrade blocking structural errors to warnings
- pretend unresolved resource problems are solved

## 21. Invalid Evaluation Conditions

The evaluation process is invalid if it would:

- inspect only current state and ignore patch effects
- silently repair the patch before evaluation
- hide blocking scope/resource/structure problems
- merge warning and confirmation classes into one undifferentiated status
- treat destructive edits as harmless without classification
- fabricate future-state coherence without explicit operational support

If evaluation cannot produce a stable result,
the output should lean toward:
- blocked
or
- confirmation_required with explicit ambiguity,
depending on severity

## 22. Minimal Example

Example patch summary:

- patch_mode: `modify_existing`
- summary: "Insert a bounded review node before the final output path"
- change_scope:
  - scope_level: bounded
  - touch_mode: structural_edit
  - touched_nodes: [review_node, final_node]
  - touched_edges: [old_edge, new_edges]
  - touched_outputs: [final_output]
- operations:
  1. create_node(review_node)
  2. set_node_prompt(review_node, review_prompt)
  3. set_node_provider(review_node, allowed_provider)
  4. disconnect_nodes(old_source, final_node)
  5. connect_nodes(old_source, review_node)
  6. connect_nodes(review_node, final_node)
- risk_report:
  - output_rebinding_risk
- preview_requirements:
  - show changed final path
- validation_requirements:
  - output binding validity
  - provider resolution

Resulting precheck summary:

- overall_status: `confirmation_required`
- structural_validity: pass
- dependency_validity: pass_with_minor_warning
- input_output_validity:
  - valid path preserved
  - final output meaning may change
- provider_resolution: pass
- plugin_resolution: pass
- safety_review:
  - no hard violation
  - structural edit requires explicit review
- cost_assessment:
  - low to moderate increase
- ambiguity_assessment: low
- blocking_findings: []
- warning_findings:
  - latency may increase slightly
- confirmation_findings:
  - final output path semantics changed by inserted review stage
- recommended_next_actions:
  - preview changed path
  - ask user to confirm insertion before commit
- explanation:
  the patch is structurally valid and resource-resolvable, but it changes the final output path enough that explicit user confirmation is required

## 23. Decision

The canonical path from `CircuitPatchPlan` to `ValidationPrecheck`
must be explicit, future-state-aware, and diagnostic.

Precheck evaluation must preserve:
- scope boundaries
- structural truth
- resource resolution truth
- output consequences
- safety and cost signals
- confirmation requirements

No silent repair, no hidden normalization, and no blocked-to-pass downgrading is allowed.
