# Operations Decision Output and Runbook Integration Specification

## Recommended save path
`docs/specs/ops/ops_decision_output_and_runbook_integration_spec.md`

## 1. Purpose

This document defines how the AI-assisted operations layer must present recommendations and how those recommendations must connect to runbooks.

## 2. Scope

This specification governs:

1. machine-readable decision outputs,
2. severity and confidence structure,
3. evidence presentation,
4. runbook mapping,
5. operator-facing recommendation form.

## 3. Decision output shape

Each recommendation must be representable in structured form.

Minimum fields:

1. `issue_type`
2. `severity`
3. `confidence`
4. `affected_scope`
5. `probable_root_cause`
6. `recommended_next_action`
7. `required_approval_level`
8. `linked_runbook`
9. `evidence_bundle_ref`
10. `urgency_rank`

These fields must exist even if a UI later renders them differently.

## 4. Severity model

Minimum severity levels:

1. `info`
2. `warning`
3. `high`
4. `critical`

Severity must describe operational impact, not just model confidence.

## 5. Confidence model

Minimum confidence levels:

1. `low`
2. `medium`
3. `high`

Confidence must describe belief in the diagnosis or recommendation.
It must not be inferred solely from the presence of many signals.

## 6. Recommendation structure

Recommendations must be specific enough to act on.

A recommendation should answer:

1. what happened,
2. why the system thinks this happened,
3. what should happen next,
4. who must approve or act,
5. what runbook applies,
6. what evidence supports the recommendation.

## 7. Runbook linking rule

Every non-trivial operational recommendation must link to an explicit runbook or policy procedure if one exists.

The recommendation must not merely name the runbook.
It should identify the relevant entry point or step group within that runbook where practical.

## 8. Evidence rule

A recommendation without evidence is not action-grade.

At minimum, every action-affecting recommendation must link:

1. one or more evidence sources,
2. source freshness,
3. source tier,
4. summary rationale.

## 9. Contradiction handling

If available evidence supports multiple competing recommendations:

1. show the alternatives,
2. show confidence for each,
3. prefer safer action paths,
4. do not collapse ambiguity into a single overconfident statement.

## 10. Operator-facing form

The operator-facing form should be short, direct, and layered.

Recommended presentation:

1. one-line diagnosis,
2. one-line impact summary,
3. one-line recommended next action,
4. expandable evidence,
5. linked runbook,
6. approval requirement if relevant.

## 11. Acceptance criteria

A conforming implementation satisfies this specification only if:

1. recommendation outputs are structured,
2. severity and confidence are distinct,
3. recommendations link to evidence,
4. recommendations link to runbooks where applicable,
5. ambiguous situations are represented honestly,
6. action-grade recommendations are not evidence-free.
