# Plugin Runtime Execution Binding Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_runtime_execution_binding_contract.md`

## 1. Purpose

This document defines the canonical runtime execution binding contract for plugins in Nexa.

It establishes:
- how an active plugin becomes a bound runtime execution resource
- how runtime represents plugin execution identity
- how a bound plugin connects to Node Runtime and Working Context
- how approved namespace policy is enforced during actual execution
- how PluginExecutor participates in runtime execution
- how bound plugin execution connects to trace, artifacts, and failure handling

## 2. Core Decision

1. A loaded or active plugin is not yet sufficient by itself.
2. Runtime must bind an active plugin into an explicit execution object.
3. Bound execution must remain compatible with Node as sole execution unit, dependency-based execution, Working Context rules, approved policy, and trace/artifact truth.
4. Plugins must execute through controlled runtime binding and executor paths.
5. Runtime execution binding must remain explicit, inspectable, and policy-enforced.

## 3. Non-Negotiable Boundaries

- Node boundary
- Working Context boundary
- Executor boundary
- Policy boundary
- Trace boundary

## 4. Core Vocabulary

- Bound Plugin
- Binding
- PluginExecutor
- Execution Instance
- Bound Policy

## 5. Canonical Lifecycle Position

Artifact
-> Installed
-> Loaded
-> Active
-> Bound for Runtime Execution
-> Execution Instance
-> Result / Artifact / Trace / Failure Outcome

## 6. Canonical Bound Runtime Object

BoundPluginRuntime
- binding_id: string
- plugin_id: string
- artifact_ref: string
- manifest_ref: string
- installation_ref: string
- target_runtime_ref: string
- executor_ref: string
- bound_policy_ref: string
- working_context_contract_ref: string
- read_declarations: list[string]
- write_declarations: list[string]
- external_target_bindings: list[string]
- runtime_constraints: BoundPluginRuntimeConstraints
- activation_status: enum("bound_inactive", "bound_ready", "bound_suspended", "binding_failed")
- notes: string | null

## 7. Binding Preconditions

Runtime may create a BoundPluginRuntime only if:
- plugin is installed
- plugin is loaded
- plugin is active or eligible
- artifact and manifest resolve consistently
- approved namespace policy is resolvable
- runtime can enforce required policy restrictions
- PluginExecutor path is available
- Working Context declarations are bindable
- dependency/environment posture is acceptable

## 8. Relationship to Node Runtime and Working Context

- Node remains the sole execution unit.
- Plugin participates as a capability resource within node execution.
- Plugin must interact through Working Context.
- Binding must transform abstract upstream contracts into execution-ready context access rules.

## 9. Relationship to Namespace Policy

Binding must produce a bound policy form that is:
- resolvable from approved policy
- enforceable in runtime
- attached to one bound execution object
- traceable during execution

A bound plugin must never execute with looser access than approved policy allows.

## 10. Relationship to PluginExecutor

- runtime binding must resolve one executor path
- execution must flow through PluginExecutor
- executor must receive bound policy and Working Context declarations
- executor must not ignore those declarations

PluginExecutor is the execution path.
BoundPluginRuntime is the execution-ready object attached to that path.

## 11. External Target Binding and Runtime Constraints

External targets and runtime constraints such as timeout, retry, cancellation, determinism, and failure escalation must be attached explicitly at binding time.

## 12. Execution Instance Model

PluginExecutionInstance
- execution_instance_id: string
- binding_ref: string
- node_execution_ref: string
- run_ref: string
- status: enum("queued", "running", "completed", "failed", "cancelled", "partial")
- started_at: string | null
- completed_at: string | null
- input_context_refs: list[string]
- output_context_refs: list[string]
- artifact_refs: list[string]
- trace_event_refs: list[string]
- failure_code: string | null
- notes: string | null

## 13. Failure, Timeout, and Cancellation Rules

These must be reflected in execution instance state and trace. Partial outcomes must remain distinguishable from complete success.

## 14. Trace and Artifact Integration

A bound plugin execution must link to:
- node execution identity
- runtime binding identity
- produced artifacts
- trace events
- output context refs
- policy violation attempts if any

## 15. Explicitly Forbidden Patterns

- active but unbound execution
- direct raw invocation bypass
- policy-free bound execution
- context overexposure
- silent side-effect routing
- trace-free execution

## 16. Canonical Findings Categories

Examples:
- BINDING_INSTALLATION_REQUIRED
- BINDING_LOAD_REQUIRED
- BINDING_POLICY_UNRESOLVABLE
- BINDING_CONTEXT_DECLARATION_INCOMPLETE
- BINDING_EXECUTOR_UNAVAILABLE
- EXECUTION_CONTEXT_READ_DENIED
- EXECUTION_CONTEXT_WRITE_DENIED
- EXECUTION_TIMEOUT_REACHED
- EXECUTION_CANCELLED
- EXECUTION_RUNTIME_FAILURE

## 17. Relationship to Existing PRE / CORE / POST Stage Structure

This document does not delete the existing PRE / CORE / POST execution-stage model used elsewhere in the current plugin direction.

Interpretation rule:
- PRE / CORE / POST remains execution-stage vocabulary
- this Binding contract describes how an already-accepted plugin becomes a runtime-bound execution resource
- both models must be read as compatible unless and until an explicit migration document says otherwise

## 18. Relationship to Current Codebase Alignment

This document describes the target binding contract shape.
Current code may still use thinner executor/binding layers than the fully explicit objects described here.

Implementation must therefore treat this document as partially aligned / migration-required where current executor and runtime code are thinner than the target model.

## 19. Relationship to Existing Plugin Contract v1.1.0

This document should be read as a cumulative refinement of the existing plugin direction centered on deterministic capability components, Node Runtime, Working Context, and PluginExecutor.

It is not intended as a silent replacement-by-omission of that earlier direction.

## 20. Canonical Summary

- A plugin is not truly executable in Nexa merely because it is active.
- Runtime must bind an active plugin into an explicit execution-ready object.
- Bound execution must flow through PluginExecutor and Working Context.
- Approved namespace policy must remain enforceable during actual execution.

## 21. Final Statement

A plugin in Nexa should not execute as anonymous loaded code.

It should execute only as a bound runtime resource with explicit context access, policy enforcement, executor routing, and traceable outcomes.

That is the canonical meaning of Plugin Runtime Execution Binding in Nexa.
