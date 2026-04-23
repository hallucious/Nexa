# Intent to Patch Mapping Rules v0.1

## Recommended save path
`docs/specs/designer/intent_to_patch_mapping_rules.md`

## 1. Purpose

This document defines the canonical mapping rules from:

- `NormalizedIntent`
to
- `CircuitPatchPlan`

Its purpose is to ensure that Designer AI does not jump from interpreted intent
to hidden structural mutation.

The mapping layer exists between:

User Request
-> Designer Session State Card
-> Session Card to Intent Mapping
-> Normalized Intent
-> Intent to Patch Mapping
-> Circuit Patch Plan
-> Validator Precheck
-> Draft Preview
-> Approval
-> Commit

## 2. Core Decision

`CircuitPatchPlan` must be derived from explicit `NormalizedIntent`.

Official rule:

- patch planning must be intent-driven
- every structural change must be represented as explicit patch operations
- patch generation must preserve scope, constraints, and confirmation boundaries
- missing information must remain explicit as assumptions, risks, or preview requirements

In short:

`CircuitPatchPlan` is not direct savefile mutation.
It is an explicit structural proposal derived from `NormalizedIntent`.

## 3. Mapping Principles

### 3.1 Intent is authoritative
Patch generation must begin from:
- `category`
- `target_scope`
- `objective`
- `constraints`
- `proposed_actions`
- `assumptions`
- `ambiguity_flags`
- `risk_flags`
- `requires_user_confirmation`

### 3.2 Patch must remain narrower than or equal to intent
Patch generation may narrow or simplify the change set,
but must never widen scope beyond the intent.

### 3.3 Patch must be explicit
No hidden graph mutation is allowed.
Every structural effect must correspond to one or more explicit patch operations.

### 3.4 Repair and optimize must remain distinguishable
Repair-generated patches must prioritize structural validity restoration.
Optimize-generated patches must not silently behave like broad redesign.

### 3.5 Invalid intent does not become silent patch correction
If intent is too ambiguous to produce a safe patch:
- emit minimal preview-safe patch only if possible
- otherwise stop at patch with strong risks / confirmation requirements
- never fabricate certainty

## 4. Source and Target Objects

### 4.1 Source
`NormalizedIntent`

Canonical source fields:

- `intent_id`
- `category`
- `user_request_text`
- `target_scope`
- `objective`
- `constraints`
- `proposed_actions`
- `assumptions`
- `ambiguity_flags`
- `risk_flags`
- `requires_user_confirmation`
- `confidence`
- `explanation`

### 4.2 Target
`CircuitPatchPlan`

Canonical target fields:

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

## 5. Top-Level Mapping Table

### 5.1 `intent_id` -> `intent_ref`
Rule:
- copy directly

### 5.2 `category` -> `patch_mode`
Canonical mapping:

- `CREATE_CIRCUIT` -> `create_draft`
- `MODIFY_CIRCUIT` -> `modify_existing`
- `REPAIR_CIRCUIT` -> `repair_existing`
- `OPTIMIZE_CIRCUIT` -> `optimize_existing`

Special rule:
- `EXPLAIN_CIRCUIT` and `ANALYZE_CIRCUIT` normally do not produce commit-oriented patch plans
- they may produce analysis-only or empty operation plans only if the broader flow explicitly allows proposal scaffolding
- otherwise patch generation should stop before structural patching

### 5.3 `user_request_text` + `objective` -> `summary`
Rule:
- generate concise human-readable summary
- summary must describe proposed structural change, not restate the request vaguely

### 5.4 `target_scope` -> `change_scope`
Rule:
- convert intent scope into patch touch scope
- preserve boundedness
- preserve destructive restrictions

### 5.5 `risk_flags` -> `risk_report`
Rule:
- carry forward intent risks
- enrich with patch-specific risks introduced by actual operations

### 5.6 `requires_user_confirmation` -> `preview_requirements` / `validation_requirements`
Rule:
- if confirmation is required at intent level, patch must preserve it
- patch generation must not erase confirmation

### 5.7 `constraints` -> operation shaping
Rule:
- constraints do not usually copy one-to-one,
  but they strongly shape operation selection, operation count, and touch mode

## 6. Patch Mode Resolution Rules

### 6.1 `create_draft`
Use when category is `CREATE_CIRCUIT`.

Expected characteristics:
- no destructive edit against existing approved structure
- operations likely begin with `create_node`, `connect_nodes`, `define_output_binding`

### 6.2 `modify_existing`
Use when category is `MODIFY_CIRCUIT`.

Expected characteristics:
- bounded edits against existing draft
- may include insert, replace, attach, disconnect, reconnect

### 6.3 `repair_existing`
Use when category is `REPAIR_CIRCUIT`.

Expected characteristics:
- restore structural validity
- fix invalid binding, missing dependency, broken output path, invalid node config
- minimality bias is strong

### 6.4 `optimize_existing`
Use when category is `OPTIMIZE_CIRCUIT`.

Expected characteristics:
- quality, cost, latency, or reliability improvement
- avoid unnecessary broad structural churn
- preserve original product intent

## 7. Change Scope Mapping Rules

### 7.1 Direct mapping
Map from intent scope into patch scope:

Intent:
- allowed refs
- touch budget
- destructive allowance

Patch:
- `scope_level`
- `touch_mode`
- `touched_nodes`
- `touched_edges`
- `touched_outputs`
- `touched_metadata`

### 7.2 Scope level mapping
Recommended mapping:

- `minimal` -> `minimal`
- `bounded` -> `bounded`
- `broad` -> `broad`

### 7.3 Touch mode mapping
Recommended mapping rules:

- no structural change allowed -> no patch for commit
- additive local change -> `append_only`
- bounded structural replacement -> `structural_edit`
- deletion / replacement with removals -> `destructive_edit`

### 7.4 Destructive edit restriction
If intent or card forbids destructive edit:
- patch must not emit delete or destructive replace operations
- if goal cannot be satisfied without destruction, that must become risk + confirmation pressure, not hidden mutation

## 8. Operation Derivation Rules

`operations` are derived from `proposed_actions` plus structural context.

### 8.1 Explicit operation requirement
Each operation must have:
- `op_id`
- `op_type`
- target reference
- parameters
- rationale

### 8.2 Supported operation families
Patch generation may use operations such as:

- `create_node`
- `delete_node`
- `update_node_metadata`
- `replace_node_component`
- `set_node_prompt`
- `set_node_provider`
- `attach_node_plugin`
- `detach_node_plugin`
- `connect_nodes`
- `disconnect_nodes`
- `insert_node_between`
- `move_output_binding`
- `define_output_binding`
- `remove_output_binding`
- `set_parameter`
- `rename_node`
- `annotate_node`
- `create_subgraph`
- `delete_subgraph`

### 8.3 Minimality bias
Prefer the smallest operation set that satisfies the primary goal and respects constraints.

### 8.4 No hidden composite edits
If one high-level action implies multiple structural effects,
emit multiple operations explicitly.

Example:
"insert review node before final output"
should not become a single hidden mutation.
It should expand into explicit operations such as:
- create_node
- connect_nodes
- disconnect_nodes if needed
- move or define output binding if affected

### 8.5 Read-only categories
For `EXPLAIN_CIRCUIT` and `ANALYZE_CIRCUIT`,
do not emit normal structural operations unless the flow explicitly requests a proposal sketch.
Default behavior is no structural patch.

## 9. Proposed Action to Operation Mapping Rules

### 9.1 `create_node`
Maps to:
- `create_node`
and usually one or more:
- `connect_nodes`
- `set_node_prompt`
- `set_node_provider`
- `attach_node_plugin`

### 9.2 `delete_node`
Maps to:
- `delete_node`
and usually:
- `disconnect_nodes`
- possible output rebinding operations

Must respect destructive rules.

### 9.3 `update_node`
Maps to one or more of:
- `set_parameter`
- `update_node_metadata`
- `set_node_prompt`
- `set_node_provider`
- `attach_node_plugin`
- `detach_node_plugin`

### 9.4 `connect_nodes`
Maps directly to:
- `connect_nodes`

### 9.5 `disconnect_nodes`
Maps directly to:
- `disconnect_nodes`

### 9.6 `insert_node_between`
Maps to:
- `create_node`
- `disconnect_nodes`
- `connect_nodes`
- optional parameter/provider/prompt operations

### 9.7 `replace_provider`
Maps to:
- `set_node_provider`

### 9.8 `attach_plugin`
Maps to:
- `attach_node_plugin`

### 9.9 `detach_plugin`
Maps to:
- `detach_node_plugin`

### 9.10 `set_prompt`
Maps to:
- `set_node_prompt`

### 9.11 `define_output`
Maps to:
- `define_output_binding`
or
- `move_output_binding` if rebinding existing output

### 9.12 `add_review_gate`
Typically maps to:
- `create_node`
- `set_node_prompt`
- `set_node_provider`
- `connect_nodes`
- possibly `insert_node_between`

## 10. Category-Specific Patch Strategy Rules

### 10.1 CREATE_CIRCUIT
Patch strategy:
- initialize the minimal runnable draft
- prefer append-only semantics
- define at least one coherent path from input to output
- avoid premature complexity unless explicitly requested

### 10.2 MODIFY_CIRCUIT
Patch strategy:
- preserve existing stable structure where possible
- confine touch set to requested area
- avoid turning modify into repair unless findings demand it

### 10.3 REPAIR_CIRCUIT
Patch strategy:
- prioritize validity restoration over feature expansion
- do not smuggle optimization under repair
- prefer local fix over broad redesign unless local fix is impossible

### 10.4 OPTIMIZE_CIRCUIT
Patch strategy:
- preserve product intent
- favor bounded local improvements
- avoid destructive changes unless explicitly allowed and justified

## 11. Dependency Effects Mapping Rules

`dependency_effects` must summarize how operations affect graph structure.

The patch generator should identify at least:

- newly added dependencies
- removed dependencies
- potentially risky dependency breaks
- fan-in / fan-out changes when relevant
- likely execution-order implications

This report is not the final validator output,
but a proposal-level dependency impact forecast.

## 12. Output Effects Mapping Rules

`output_effects` must summarize how outputs are affected.

The patch generator should identify at least:

- unchanged outputs
- moved output source
- newly defined outputs
- removed outputs
- outputs at risk due to touched nodes/edges

If an operation touches a path that feeds an output,
`output_effects` must not remain empty.

## 13. Reversibility Mapping Rules

`reversibility` must reflect how safely the patch could be rolled back conceptually.

### 13.1 Append-only patches
Usually high reversibility.

### 13.2 Structural edit patches
Medium reversibility.

### 13.3 Destructive edit patches
Require stronger reversibility notes.

Recommended fields:
- reversible: bool
- rollback_complexity: low | medium | high
- irreversible_points: list
- user_confirmation_needed: bool

## 14. Preview Requirements Mapping Rules

Patch generation must explicitly state what preview must show.

Typical preview requirements:
- changed nodes
- changed edges
- changed outputs
- destructive changes
- risk hotspots
- assumption-dependent branches

If the patch is destructive or ambiguity-dependent,
preview requirements must be stronger, not weaker.

## 15. Validation Requirements Mapping Rules

Patch generation must explicitly state what precheck must validate.

Typical validation requirements:
- touched node config validity
- edge integrity
- output binding validity
- provider resolution
- plugin resolution
- structural cycles / broken connectivity
- scope compliance
- destructive edit review
- cost/safety review when relevant

## 16. Assumption Handling Rules

### 16.1 Assumptions must affect patch conservatively
If assumptions exist, patch planning must take the safest structural path.

### 16.2 High-severity assumptions
High-severity assumptions should:
- increase confirmation pressure
- reduce patch aggressiveness
- increase preview requirements

### 16.3 Do not convert assumption into silent fixed fact
Patch may reference assumption rationale,
but must not pretend the assumption is settled truth.

## 17. Ambiguity Handling Rules

### 17.1 Structural ambiguity
If ambiguity affects structure materially,
patch must either:
- choose the narrowest safe path
or
- preserve branch uncertainty in preview/confirmation requirements

### 17.2 Resource ambiguity
If provider/plugin availability is unresolved,
patch must not present unresolved resources as ready.

### 17.3 Output ambiguity
If multiple output rebinding paths are plausible,
patch should avoid destructive output moves unless clarified.

## 18. Risk Report Mapping Rules

`risk_report` must include:

- carried-over intent risks
- patch-specific risks
- severity summary
- reasons confirmation may be required
- structurally sensitive operations

Patch-specific risks may include:
- destructive topology shift
- output rebinding risk
- validation failure risk
- unavailable resource dependency
- cost escalation risk
- scope creep risk

## 19. Confidence and Explanation Interaction

Although patch plan does not directly own `confidence`,
intent confidence should influence patch aggressiveness.

### 19.1 High confidence
May allow fuller patch expression within scope.

### 19.2 Low confidence
Should lead to:
- smaller operation set
- stronger preview requirements
- stronger confirmation pressure
- explicit rationale in summary and risk report

## 20. Invalid Patch Mapping Conditions

Patch mapping is invalid if it would:

- widen scope beyond intent
- produce destructive operations without allowance
- contradict hard constraints
- ignore required confirmation
- rely on unavailable provider/plugin resolution as if solved
- hide multi-step structural mutation inside one opaque operation
- erase touched output consequences
- treat read-only explain/analyze intent as normal structural commit patch

Invalid mapping should not be silently repaired.
It should instead produce:
- stronger risk report
- reduced reversibility confidence
- stricter preview/validation requirements
or
- explicit stop before structural patching

## 21. Minimal Example

Example source summary:

- category: `MODIFY_CIRCUIT`
- user_request_text: "Add a review node before final output"
- target_scope: bounded existing circuit
- constraints:
  - destructive edit allowed: true
  - human review required: true
- proposed_actions:
  - create review node
  - insert node before final output
- ambiguity: none
- risk_flags:
  - output_rebinding_risk
- requires_user_confirmation: true

Resulting patch summary:

- patch_mode: `modify_existing`
- summary: "Insert a bounded review stage before the current final output path"
- change_scope:
  - scope_level: bounded
  - touch_mode: structural_edit
  - touched_nodes: [new_review_node, final_output_source]
  - touched_edges: [old_edge, new_edges]
  - touched_outputs: [final_output]
- operations:
  1. create_node(review_node)
  2. set_node_prompt(review_node, review_prompt)
  3. set_node_provider(review_node, allowed_provider)
  4. disconnect_nodes(old_source, final_node)
  5. connect_nodes(old_source, review_node)
  6. connect_nodes(review_node, final_node)
- dependency_effects:
  - new intermediate dependency inserted
- output_effects:
  - final output path preserved but upstream source path changed
- risk_report:
  - output_rebinding_risk
- reversibility:
  - reversible: true
  - rollback_complexity: medium
- preview_requirements:
  - show inserted node and changed path
  - show output-path effect
- validation_requirements:
  - check edge integrity
  - check final output path validity
  - check provider resolution
  - confirm structural edit safety

## 22. Decision

The canonical path from `NormalizedIntent` to `CircuitPatchPlan`
must be explicit, bounded, and operation-based.

Patch generation must preserve:
- intent category
- scope limits
- constraints
- assumptions
- ambiguity
- risks
- confirmation requirements

No hidden savefile mutation, hidden widening, or silent destructive change is allowed.
