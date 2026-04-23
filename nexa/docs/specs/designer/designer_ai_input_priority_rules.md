# Designer AI Input Priority Rules v0.1

## Recommended save path
`docs/specs/designer/designer_ai_input_priority_rules.md`

## 1. Purpose

This document defines the canonical precedence rules for resolving conflicts
inside the information provided to Designer AI.

Its purpose is to ensure that contradictory signals do not produce unstable,
over-broad, or unsafe design behavior.

## 2. Core Decision

When input signals conflict, Designer AI must not guess freely.

Official rule:

- explicit bounded authority beats vague inference
- hard constraints beat preferences
- current corrected intent beats stale history
- current structural reality beats old assumptions

In short:

Priority must be rule-based, not stylistic.

## 3. Global Precedence Ladder

Use this precedence order when conflict exists:

1. forbidden authority / safety boundary
2. hard scope boundary
3. hard constraints and restrictions
4. latest explicit user correction
5. current validated design reality
6. current findings and risks
7. explicit objective
8. clarified interpretation
9. original request wording
10. preferences
11. historical context
12. UI hints and notes

## 4. Authority Priority Rules

### 4.1 Forbidden authority is absolute
If `forbidden_authority` conflicts with any other signal,
`forbidden_authority` wins.

### 4.2 Approval truth beats convenience
If approval is pending or absent,
no downstream interpretation may behave as if approval exists.

## 5. Scope Priority Rules

### 5.1 Explicit target scope beats vague request phrasing
If user wording is broad but `target_scope` is narrow,
the narrow scope wins.

### 5.2 Destructive allowance beats intention guess
If the user request sounds destructive but destructive edit is not allowed,
the prohibition wins.

### 5.3 Narrowing corrections beat older broad interpretations
If later user correction narrows the task,
the narrowed version wins.

## 6. Constraint Priority Rules

### 6.1 Hard restrictions beat preferences
Examples:
- provider restriction beats provider preference
- plugin restriction beats plugin preference
- forbidden pattern beats stylistic goal

### 6.2 Safety requirement beats speed preference
If safety and speed conflict, safety wins unless a higher-level explicit policy says otherwise.

### 6.3 Human review requirement beats autonomous simplification
If human review is required, the design flow must preserve that requirement.

## 7. User Intent Priority Rules

### 7.1 Latest explicit correction wins
Latest explicit user correction overrides:
- earlier ambiguous wording
- older rejected direction
- stale inferred interpretation

### 7.2 Clarified interpretation beats raw initial wording
If the conversation already produced a clarified interpretation,
it should outrank the earlier vague request.

### 7.3 Objective beats decorative request wording
If the request wording and stated objective differ,
the explicit objective wins.

## 8. Reality Priority Rules

### 8.1 Current Working Save beats remembered old structure
Current draft reality wins over old summary or history.

### 8.2 Current findings beat optimistic assumptions
If the draft is currently invalid, that invalidity must outrank optimistic design assumptions.

### 8.3 Current resource availability beats ideal design desire
Unavailable resources may be preferred conceptually,
but availability status wins for proposal generation.

## 9. Risk Priority Rules

### 9.1 High unresolved risk beats weak preference
A high unresolved risk outranks:
- style preference
- convenience preference
- broad optimization desire

### 9.2 Blocking findings beat optimization goals
If a design needs repair, repair pressure outranks optimization pressure.

## 10. Historical Priority Rules

### 10.1 Prior rejection reason is important but not absolute
It should influence interpretation,
but it does not override current user correction or current scope.

### 10.2 Old revision state must not overrule current explicit instruction
History informs.
It does not dominate the present instruction.

## 11. Notes Priority Rules

`notes` and UI hints are lowest-priority supportive context.
They must not override:
- authority
- scope
- constraints
- findings
- explicit user corrections

## 12. Conflict Handling Rule

If conflict cannot be resolved by the precedence ladder:
- emit ambiguity
- lower confidence
- keep the narrower safer interpretation
- require confirmation if structure would change materially

## 13. Canonical Examples

### Example 1
- user text: "redo the whole flow"
- target_scope: node_only reviewer
Result:
- node_only reviewer wins

### Example 2
- provider preference: claude
- provider restriction: claude forbidden
Result:
- restriction wins

### Example 3
- old revision reason: "too broad"
- current user correction: "yes, now change the whole circuit"
Result:
- current explicit correction wins, subject to safety and scope authority

### Example 4
- optimize request
- current blocking finding: broken output path
Result:
- repair pressure wins before pure optimization

## 14. Decision

Designer AI input priority must be governed by explicit precedence.

The canonical order is:
authority -> scope -> hard constraints -> latest explicit correction -> current reality -> findings/risks -> objective -> preferences -> history -> notes.
