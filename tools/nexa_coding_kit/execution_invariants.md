DOCUMENT
execution_invariants.md

Purpose

This document defines the non-negotiable architectural invariants of Nexa.

These invariants must NEVER be violated by code changes, refactoring,
feature additions, or AI-generated patches.

Any change that breaks these rules must be rejected.

AI coding agents must read this document before modifying the codebase.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. EXECUTION UNIT INVARIANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Node is the ONLY execution unit in Nexa.

Rules

1. Circuits never execute logic.
2. Circuits only define connections.
3. All runtime work must occur inside Nodes.

Violation example

Introducing logic execution inside Circuit objects.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. DEPENDENCY EXECUTION MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Execution order must be determined by the dependency graph.

Rules

1. Nodes execute only after dependencies complete.
2. No implicit execution ordering.
3. No pipeline-style sequential execution model.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. PIPELINE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The pipeline architecture is permanently deprecated.

Rules

1. No pipeline abstractions.
2. No pipeline terminology.
3. No pipeline-style execution code.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. ARTIFACT STORAGE RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artifacts must follow an append-only rule.

Rules

1. Existing artifacts must never be overwritten.
2. New outputs are appended as new records.
3. Runtime must never mutate artifact history.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. PLUGIN NAMESPACE RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plugins may only write to their own namespace.

Allowed namespace

plugin.<plugin_id>.*

Forbidden actions

- writing to core runtime state
- modifying node configuration
- modifying circuit structure


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. DETERMINISTIC EXECUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nexa runtime must remain deterministic.

Rules

1. Node execution order must be reproducible.
2. Same inputs must produce the same execution plan.
3. Runtime behavior must not depend on implicit state.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. TRACE INTEGRITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Trace must accurately represent runtime events.

Rules

1. Every node execution must produce trace events.
2. Trace must follow actual runtime order.
3. Trace must not omit execution stages.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. CONTRACT-DRIVEN ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nexa architecture is defined by contracts.

Rules

1. Contracts must not be silently broken.
2. Contract changes require spec updates.
3. Contract versions must stay synchronized.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. RUNTIME ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Runtime must remain isolated from external side effects.

Rules

1. Providers must be invoked through defined interfaces.
2. Plugins must not bypass runtime APIs.
3. Direct provider calls outside runtime are forbidden.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. CODE MODIFICATION RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before modifying code:

1. Identify which invariant may be affected.
2. Confirm the invariant remains preserved.
3. Update tests if behavior changes.
4. Document architectural changes.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
11. VIOLATION POLICY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If a change violates any invariant:

1. The change must be rejected.
2. The architecture must be restored.
3. The violation must be documented.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END