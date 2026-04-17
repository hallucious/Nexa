# Plugin Namespace Policy Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_namespace_policy_contract.md`

## 1. Purpose

This document defines the canonical namespace policy contract for plugins in Nexa.

Its purpose is to make explicit:
- what namespaces a plugin may read
- what namespaces a plugin may write
- how requested namespace access is declared
- how namespace access is validated by the Plugin Builder
- how runtime must enforce the approved namespace policy
- how future readers and future AI systems can distinguish requested access from approved access

A plugin without namespace policy is not a safe plugin candidate.

## 2. Core Decision

1. Namespace access must always be explicit.
2. Requested and approved namespace access must remain distinct.
3. Designer AI may propose namespace access requirements, but may not approve them.
4. Builder validation decides whether requested namespace access is acceptable.
5. Runtime must enforce approved policy rather than trusting plugin self-declaration.
6. No plugin may receive effectively unlimited namespace access by accident or omission.

## 3. Non-Negotiable Boundaries

- Proposal boundary: Designer-originated requests are proposal-space only.
- Builder boundary: Builder owns namespace policy validation and approval outcome emission.
- Runtime boundary: Runtime enforces approved namespace access.
- Savefile boundary: policy metadata may be referenced, but text alone does not replace enforcement.
- Trust boundary: approved scope must be builder-governed and runtime-enforced.

## 4. Design Goals

Safety, extensibility, efficiency, clarity, composability.

## 5. Core Vocabulary

- Namespace
- Requested Access
- Approved Access
- Denied Access
- Read Access
- Write Access
- Namespace Scope
- Least-Authority Principle

## 6. Policy Model Overview

Three layers must remain distinct:
1. requested namespace policy
2. approved namespace policy
3. runtime enforced namespace policy

## 7. Requested Namespace Policy Object

RequestedNamespacePolicy
- requested_read_scopes: list[NamespaceScopeRequest]
- requested_write_scopes: list[NamespaceScopeRequest]
- requested_external_read_targets: list[string]
- requested_external_write_targets: list[string]
- policy_sensitivity: enum("low", "medium", "high", "restricted", "unknown")
- rationale: string | null
- unresolved_questions: list[string]

NamespaceScopeRequest
- namespace_family: string
- scope_mode: enum(
    "specific_fields",
    "declared_subtree",
    "family_limited",
    "full_family",
    "unknown"
  )
- field_paths: list[string]
- reason: string | null

Unknown scope must never auto-promote to full authority.

## 8. Approved Namespace Policy Object

ApprovedNamespacePolicy
- policy_id: string
- read_scopes: list[ApprovedNamespaceScope]
- write_scopes: list[ApprovedNamespaceScope]
- external_read_targets: list[string]
- external_write_targets: list[string]
- denied_scopes: list[DeniedNamespaceScope]
- enforcement_mode: enum("strict", "strict_with_logging", "compatibility_limited")
- rationale_summary: string
- issued_by_stage: string
- policy_version: string

Approved policy must never contain `unknown` scope.

## 9. Runtime Enforcement

RuntimeNamespaceEnforcementPolicy
- approved_policy_ref: string
- read_filter_mode: enum("allow_list")
- write_filter_mode: enum("allow_list")
- violation_mode: enum("block_and_record", "block_warn_and_record")
- trace_violations: bool

Core rule:
Runtime must operate on allow-list semantics, not deny-list semantics.

## 10. Read Policy Rules

- Read access must be purpose-bound.
- Read scope should prefer specific or bounded subtree access.
- Full-family read should be exceptional.
- External reads must be separately declared.

## 11. Write Policy Rules

- Write access is higher risk than read access.
- Writes must normally be limited to plugin-governed result/output subtrees and explicitly allowed emission targets.
- Silent writes into unrelated namespaces are forbidden.
- Full-family write access is presumed disallowed.

## 12. External Target Policy

External reads and writes are policy surfaces that must remain explicit and builder-visible.

## 13. Validation Responsibilities

Builder validation must perform at minimum:
- requested-vs-purpose consistency check
- least-authority check
- forbidden scope check
- unknown-scope rejection
- external target review
- result emission when access is narrowed, denied, or blocked

## 14. Verification Responsibilities

Verification may additionally include:
- smoke checks under approved scope
- denied write attempts fail
- manifest/policy declarations align
- generated code does not obviously violate policy

## 15. Runtime Responsibilities

Runtime must enforce:
- read filtering
- write filtering
- violation recording
- no silent widening
- policy-linked traceability

## 16. Trace and Audit Model

Namespace policy must be auditable. The system should be able to answer:
- what was requested
- what was approved
- what was denied
- what was attempted at runtime
- whether a violation occurred

## 17. Relationships

- Intake Contract asks what is being asked for.
- Namespace Policy Contract asks what is allowed, denied, and enforced.
- Builder Spec Contract asks which stage owns evaluation.

## 18. Canonical Findings Categories

Examples:
- NAMESPACE_SCOPE_TOO_BROAD
- NAMESPACE_UNKNOWN_SCOPE
- NAMESPACE_FORBIDDEN_WRITE_TARGET
- NAMESPACE_EXTERNAL_TARGET_UNDECLARED
- NAMESPACE_REQUEST_PURPOSE_MISMATCH
- NAMESPACE_RUNTIME_VIOLATION_ATTEMPT

## 19. Explicitly Forbidden Patterns

- implicit global access
- policy by convention only
- runtime-only policy invention
- hidden cross-namespace writes
- “temporary” unlimited access without explicit governance

## 20. Canonical Summary

- Namespace access is an explicit governed contract boundary.
- Requested and approved policy must remain separate.
- Builder validation owns approval decisions.
- Runtime enforcement owns actual access control and violation blocking.
- Least-authority and allow-list semantics are the default.

## 21. Final Statement

A plugin in Nexa is not defined only by what code it contains.

It is also defined by what data spaces it is allowed to touch.

That is the canonical meaning of Plugin Namespace Policy in Nexa.
