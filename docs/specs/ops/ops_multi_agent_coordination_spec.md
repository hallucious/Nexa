# Operations Multi-Agent Coordination Specification

## Recommended save path
`docs/specs/ops/ops_multi_agent_coordination_spec.md`

## 1. Purpose

This document defines how multiple AI systems may collaborate inside Nexa's operations layer without collapsing trust boundaries.

## 2. Scope

This specification governs:

1. role separation,
2. handoff structure,
3. evidence passing,
4. trust-tier separation,
5. coordination failure handling.

## 3. Role separation rule

If multiple AI systems are used, they must not all operate as one undifferentiated super-agent.

Roles should be separated explicitly.

Possible roles:

1. summarizer,
2. classifier,
3. remediation recommender,
4. human-facing explanation generator,
5. automation controller.

## 4. Trust tiers

Different models may have different trust and permission tiers.

Examples:

1. low-trust summarizer with read-only access,
2. medium-trust classifier with structured evidence access,
3. high-trust controller limited to safe-execute actions.

The system must not assume equal trust across all models.

## 5. Handoff contract

A handoff between AI systems must include:

1. structured task statement,
2. evidence bundle reference,
3. redaction status,
4. confidence context,
5. action boundary context,
6. expected output schema.

Free-form handoff without structure is not sufficient for a reliable operational system.

## 6. Evidence-passing rule

Models must pass references or structured summaries when possible, not raw sensitive payloads.

If deeper evidence is required, access must respect the same redaction and permission rules as a direct human or AI consumer.

## 7. Conflict resolution

If two AI systems disagree:

1. expose the disagreement,
2. prefer safer interpretations,
3. require human review for action-affecting decisions,
4. do not auto-average conflicting diagnoses into a false certainty.

## 8. Failure containment

A failure in one AI role should not automatically produce uncontrolled downstream action.

Every downstream role should re-check:

1. confidence,
2. evidence sufficiency,
3. capability level,
4. approval requirement.

## 9. Acceptance criteria

A conforming implementation satisfies this specification only if:

1. multi-agent roles are explicit,
2. handoffs are structured,
3. trust tiers are explicit,
4. conflicts are surfaced honestly,
5. one model failure does not create uncontrolled action execution.
