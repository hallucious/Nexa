# Nexa Execution Rules

## Purpose

This document defines derived execution and implementation rules for Nexa.

It is subordinate to:

- `docs/ARCHITECTURE_CONSTITUTION.md`

## Core Rules

1. Node is the only execution unit.
2. System-level execution is dependency-based.
3. Node-internal pre/core/post stages are a node contract, not a system pipeline.
4. Artifacts are append-only and immutable.
5. Plugins are restricted to `plugin.<plugin_id>.*`.
6. Execution behavior must remain traceable.
7. New features must not violate the constitution.

## Related Specs

- `docs/specs/foundation/terminology.md`
- `docs/specs/contracts/validation_engine_contract.md`
- `docs/specs/architecture/trace_model.md`

End of Execution Rules
