# Session Card to Intent Mapping Rules v0.1

## Recommended save path
`docs/specs/designer/session_card_to_intent_mapping_rules.md`

## 1. Purpose

This document defines the canonical mapping rules from:

- `DesignerSessionStateCard`
to
- `NormalizedIntent`

Its purpose is to ensure that Designer AI does not invent intent structure from hidden assumptions.

The mapping layer exists between:

User Request
-> Designer Session State Card
-> Session Card to Intent Mapping
-> Normalized Intent
-> Circuit Patch Plan
-> Validator Precheck
-> Draft Preview
-> Approval
-> Commit

## 2. Core Decision

`NormalizedIntent` must be derived from explicit session-card fields.

Official rule:

- intent generation must be card-driven
- no required intent field may come from silent hidden authority
- ambiguity must remain explicit when the card does not disambiguate it
- session-card constraints and scope must bind intent generation

In short:

`NormalizedIntent` is not free-form interpretation.
It is a bounded derivation from `DesignerSessionStateCard`.

## 3. Mapping Principles

### 3.1 Card fields are authoritative
If the card explicitly defines scope, constraints, findings, risk, or forbidden authority,
the intent layer must preserve them.

### 3.2 User request alone is insufficient
`conversation_context.user_request_text` is important, but it must be interpreted through:
- current design reality
- target scope
- resource availability
- constraints
- findings
- approval state

### 3.3 Missing information becomes ambiguity, not silent assumption
If required interpretation cannot be resolved from the card,
the mapper must emit:
- `ambiguity_flags`
- `assumptions`
- `requires_user_confirmation = true` when needed

### 3.4 Mapping must preserve boundedness
The mapper must not widen the requested scope beyond what the card allows.

### 3.5 Intent is proposal-safe, not commit-safe
The mapping layer may produce intent for later patch planning,
but it must not imply commit permission or approval completion.

## 4. Source and Target Objects

### 4.1 Source
`DesignerSessionStateCard`

### 4.2 Target
`NormalizedIntent`

Canonical target fields:

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

## 5. Top-Level Mapping Table

### 5.1 `conversation_context.user_request_text` -> `user_request_text`
Rule:
- copy directly as the canonical request text
- do not replace with summary text
- if `clarified_interpretation` exists, use it only to support explanation and ambiguity resolution

### 5.2 `storage_role` -> mapping guard
Rule:
- `working_save` allows normal create/modify/repair/optimize intent generation
- `commit_snapshot` normally restricts intent generation to read-only or explicitly draft-producing flows
- if card role is `commit_snapshot` and no draft-creation path is provided, destructive intent must not be produced

### 5.3 `target_scope` -> `target_scope`
Rule:
- preserve directly
- do not widen touched scope
- if session card scope and user text conflict, session card scope wins and conflict becomes ambiguity or explanation content

### 5.4 `objective` -> `objective`
Rule:
- preserve directly
- do not silently add new primary goals
- secondary goals may be reordered for clarity, but not dropped

### 5.5 `constraints` -> `constraints`
Rule:
- preserve directly
- forbidden patterns must remain hard constraints
- preferences may shape intent, but restrictions must bind it

### 5.6 `current_risks.risk_flags` -> `risk_flags`
Rule:
- carry forward current known risks
- add new intent-level risk flags only if directly implied by the proposed category or scope
- do not delete unresolved high-risk flags during mapping

### 5.7 `current_findings` -> mapping pressure
Rule:
- findings do not map one-to-one into one target field,
  but they materially shape category choice, proposed actions, confidence, and confirmation requirements

### 5.8 `revision_state` -> explanation / confidence / assumptions
Rule:
- prior rejection reasons must affect confidence and explanation
- repeated failed interpretations should lower confidence
- user corrections must override older rejected directions

### 5.9 `approval_state` -> `requires_user_confirmation`
Rule:
- if the card says confirmation or approval is required,
  intent mapping must not silently set confirmation to false
- high-risk or destructive paths must preserve confirmation requirements

### 5.10 `forbidden_authority` -> mapping boundary
Rule:
- these fields do not copy into `NormalizedIntent`,
  but they constrain what intent may be emitted
- any intent implying forbidden authority is invalid

## 6. Category Resolution Rules

The mapper must choose exactly one primary `category`.

### 6.1 CREATE_CIRCUIT
Choose when:
- `target_scope.mode = "new_circuit"`
or
- current working save explicitly indicates `mode = "empty_draft"` and the user request is constructive

Typical signals:
- create
- make
- build
- draft a new workflow
- design a new circuit

### 6.2 MODIFY_CIRCUIT
Choose when:
- current design reality exists
- user requests structural or configuration change
- primary goal is not repair-first and not optimization-first

Typical signals:
- add node
- replace provider
- move output
- insert review stage

### 6.3 EXPLAIN_CIRCUIT
Choose when:
- `target_scope.mode = "read_only"`
and
- the request is explanatory, not analytical with change pressure

Typical signals:
- explain
- what does this do
- why is this node here

### 6.4 ANALYZE_CIRCUIT
Choose when:
- `target_scope.mode = "read_only"`
and
- the request is evaluative without immediate change commitment

Typical signals:
- analyze risk
- evaluate gaps
- identify weaknesses
- estimate cost

### 6.5 REPAIR_CIRCUIT
Choose when:
- current findings include blocking structural problems
or
- user intent is to fix a broken/invalid structure
or
- minimal restoration is the primary goal

Typical signals:
- fix
- repair
- make it valid
- resolve broken connection

### 6.6 OPTIMIZE_CIRCUIT
Choose when:
- current structure is broadly valid enough
and
- the goal is to improve cost, speed, quality, or reliability without changing the core product intent

Typical signals:
- make it cheaper
- improve reliability
- reduce latency
- improve quality without broad redesign

### 6.7 Conflict resolution
If multiple categories seem plausible, use this priority:

1. explicit scope restriction
2. explicit objective
3. current findings severity
4. clarified interpretation
5. original user request wording

If ambiguity remains after these rules:
- set ambiguity flag
- choose the safest bounded category
- require confirmation if category changes the structural direction materially

## 7. Target Scope Mapping Rules

### 7.1 Direct preservation
The mapper must preserve:
- `mode`
- touched refs
- `touch_budget` or equivalent scope tightness
- destructive edit allowance

### 7.2 Scope narrowing is allowed
The mapper may narrow scope if:
- the user correction narrows it
- the current selection narrows it
- prior rejection reasons explicitly say the last proposal was too broad

### 7.3 Scope widening is forbidden
The mapper must not widen:
- node set
- edge set
- output set
- destructive permissions

unless the card explicitly authorizes it.

### 7.4 Selection-aware mapping
`current_selection` should be used as a strong hint only when it does not conflict with explicit scope.

Example:
- selected node = reviewer
- scope = node_only reviewer
- request = improve review quality

Result:
- map to reviewer-bounded modify or optimize intent

## 8. Objective Mapping Rules

### 8.1 Primary goal
`objective.primary_goal` maps directly.

### 8.2 Secondary goals
`objective.secondary_goals` map directly.

### 8.3 Success criteria
`objective.success_criteria` must be preserved.

### 8.4 Preferred behavior
`objective.preferred_behavior` should shape:
- proposed action boundedness
- confidence framing
- assumption aggressiveness

Example:
- preferred_behavior = bounded minimal patch
- result = avoid broad replacement actions in intent

## 9. Constraint Mapping Rules

### 9.1 Hard constraints
The following must behave as hard constraints:
- forbidden patterns
- provider restrictions
- plugin restrictions
- safety level when restrictive
- human review requirement when mandatory
- explicit output requirements

### 9.2 Preference constraints
The following are directional but not absolute unless the card says otherwise:
- provider preferences
- plugin preferences
- speed priority
- quality priority
- determinism preference

### 9.3 Cost and latency shaping
If cost_limit is low:
- proposed actions should prefer smaller, more local change patterns
- confidence should drop if only high-cost paths appear feasible

If speed_priority is high:
- proposed actions should avoid unnecessary stage expansion

If quality_priority is high:
- the mapper may preserve reviewer/checkpoint additions if still within scope

## 10. Proposed Action Derivation Rules

`proposed_actions` are derived, not copied from the card.

They must be derived from:
- category
- current working save structure
- selection
- objective
- constraints
- current findings
- current risks
- user request text

### 10.1 Action boundedness
Actions must remain within `target_scope`.

### 10.2 Findings-aware action shaping
If blocking findings exist:
- repair-oriented actions should dominate
- optimization-only actions should not hide the need for repair

### 10.3 Resource-aware action shaping
The mapper must not propose actions that require unavailable provider/plugin bindings as if they were ready.

### 10.4 Minimality bias
When the card or revision history indicates prior over-broad proposals,
derive the smallest action set that can plausibly satisfy the primary goal.

## 11. Assumption Mapping Rules

### 11.1 Explicit-only bias
Assumptions should be produced only when needed.

### 11.2 Safe default assumptions
Safe defaults may be emitted only when:
- they do not widen scope
- they do not increase destructive impact
- they do not imply unavailable resources
- they are user-visible

### 11.3 Assumption severity
Use:
- low: wording/parameter clarification only
- medium: affects component choice or local structure
- high: affects category, broad scope, or destructive direction

### 11.4 High-severity assumptions
High-severity assumptions must usually imply:
- ambiguity flag
- confirmation requirement

## 12. Ambiguity Flag Mapping Rules

Emit `ambiguity_flags` when any of the following is true:

1. user request conflicts with target scope
2. multiple valid categories remain
3. multiple output branches are equally plausible
4. provider/plugin choice is materially unresolved
5. destructive change would depend on unstated preference
6. current findings indicate more than one repair path with different structural implications

Each ambiguity flag should include:
- type
- description
- why it matters structurally

## 13. Risk Flag Mapping Rules

### 13.1 Carry-through risks
Existing unresolved risks from the card must carry through.

### 13.2 New mapping-stage risks
The mapper may add new risks such as:
- scope_conflict
- destructive_edit_pressure
- unavailable_resource_dependency
- unresolved_output_target
- likely_high_cost_path
- review_required_for_sensitive_domain

### 13.3 Risk escalation
If the intent direction increases risk compared with current state,
the mapper should escalate severity and lower confidence.

## 14. Confirmation and Approval Rules

### 14.1 Confirmation derivation
Set `requires_user_confirmation = true` when:
- ambiguity materially affects structure
- destructive edit is involved
- human review is required for the chosen direction
- current approval state says confirmation_required = true
- multiple equally plausible final interpretations remain

### 14.2 Confirmation must not be silently cleared
If the card says confirmation is required,
mapping must not turn it off.

### 14.3 Approval is not implied
The mapper must never imply:
- approved
- commit-ready
- safe-to-commit

That belongs to later stages.

## 15. Confidence Mapping Rules

`confidence` is a bounded interpretation confidence score.

It should be shaped by:
- clarity of user request
- explicitness of target scope
- availability of relevant resources
- severity of current findings and risks
- revision history conflict
- unresolved ambiguity count

### 15.1 Confidence should increase when:
- scope is explicit
- clarified interpretation exists
- findings are low-severity
- required resources are clearly available
- user corrections align with target scope

### 15.2 Confidence should decrease when:
- current structure is invalid
- multiple categories are plausible
- requested change conflicts with allowed scope
- prior proposals were rejected for misunderstanding
- needed resources are unavailable or unclear

## 16. Explanation Mapping Rules

The `explanation` field should summarize:

1. why this category was chosen
2. how scope constrained the interpretation
3. what assumptions remain
4. why confirmation is or is not required
5. why confidence is high/medium/low

The explanation must be user-verifiable from the card.
It must not refer to hidden internal reasoning.

## 17. Defaulting Rules

### 17.1 Default to the narrowest safe category
If uncertain, do not choose the broadest interpretation.

### 17.2 Default to minimal structural change
When current structure exists and the request is under-specified,
prefer bounded modification over broad rebuild.

### 17.3 Default to visible assumptions
Do not hide needed assumptions.

### 17.4 Default to confirmation on structural ambiguity
If structural direction is unclear, ask by emitting confirmation requirement.

### 17.5 Default to preserving current valid structure
Do not treat every request as license to redesign the whole circuit.

## 18. Invalid Mapping Conditions

A mapping attempt is invalid if it would:

- widen scope beyond card authority
- imply forbidden authority
- erase required confirmation
- ignore blocking findings in a repair-required situation
- rely on unavailable resources without flagging ambiguity/risk
- output raw savefile mutation as intent

Invalid mapping should fail into:
- ambiguity report
- risk escalation
- reduced confidence
or
- explicit request for user confirmation downstream

## 19. Minimal Example

Example source summary:

- user_request_text: "Improve the reviewer node without changing the overall circuit"
- clarified_interpretation: "bounded reviewer-node quality upgrade only"
- target_scope.mode: "node_only"
- allowed_node_refs: ["reviewer"]
- destructive_edit_allowed: false
- primary_goal: "improve review quality"
- current_findings.warning_only
- prior_rejection_reason: "too broad"

Resulting normalized intent summary:

- category: OPTIMIZE_CIRCUIT
- user_request_text: original request preserved
- target_scope: preserved as reviewer-only bounded scope
- objective: preserved
- constraints: preserved
- proposed_actions:
  - update reviewer prompt
  - optionally adjust reviewer provider only if available and allowed
- assumptions:
  - low-severity assumption that “improve quality” means deeper critique, not broader structure change
- ambiguity_flags: none if clarified interpretation is explicit
- risk_flags:
  - quality_drift
- requires_user_confirmation: false
- confidence: medium-high
- explanation:
  chosen as optimize because the request seeks quality improvement within a preserved bounded reviewer scope and prior rejection history forbids broad edits

## 20. Decision

The canonical path from `DesignerSessionStateCard` to `NormalizedIntent`
must be explicit, bounded, and card-driven.

Intent generation must preserve:
- current design reality
- scope limits
- goals
- constraints
- findings
- risks
- approval/confirmation boundaries

No hidden widening, hidden authority, or silent structural assumption is allowed.
