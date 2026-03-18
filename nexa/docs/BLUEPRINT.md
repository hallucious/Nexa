# BLUEPRINT

Version: 1.6.0

────────────────
Architecture Reference
────────────────

Nexa follows an Execution Engine-based architecture.

All architectural rules are defined in:

- `docs/ARCHITECTURE_CONSTITUTION.md`
- `docs/architecture/EXECUTION_RULES.md`

This document does not redefine architectural rules.
It provides the current architectural reference points and active specification links.

Any implementation that violates the Constitution or the Execution Rules
is considered a violation of the Nexa architecture.

## 1. Foundation Layer

The foundational design of this project is governed by:

- `docs/ARCHITECTURE_CONSTITUTION.md`
- `docs/architecture/EXECUTION_RULES.md`
- `docs/CODING_PLAN.md`

When performing structure changes or contract changes, the Constitution layer and the active specification layer MUST both be checked.

## 2. Active Specifications

Active specifications synchronized with code.

Source of Truth:
`docs/specs/_active_specs.yaml`

Representative active specifications include:

- `docs/specs/foundation/terminology.md`
- `docs/specs/contracts/validation_engine_contract.md`
- `docs/specs/architecture/trace_model.md`

This document does not duplicate the active spec list.
The YAML file above is authoritative.

## 3. ExecutionConfig Architecture

There is no Node type specialization.

A Node is a common execution container,
and behavioral diversity is expressed only through ExecutionConfig composition.

- Node = execution container
- Behavior = ExecutionConfig composition
- NodeSpec = ExecutionConfig reference
- ExecutionConfig identity = canonical hash

Execution layer:

Engine
→ GraphExecutionRuntime
→ NodeSpec
→ NodeSpecResolver
→ ExecutionConfigRegistry
→ ExecutionConfig Schema Validation
→ NodeExecutionRuntime

## 4. Regression Policy Architecture

`src/contracts/regression_reason_codes.py`  (single source of truth)
  ↓
`src/engine/execution_regression_detector.py`  (RegressionResult)
  ↓
`src/engine/execution_regression_policy.py`   (PolicyDecision: PASS/WARN/FAIL)
  ↓
formatter / CLI

Policy rules (default):
- HIGH severity regression → FAIL
- MEDIUM severity regression → WARN
- LOW severity / no regression → PASS
