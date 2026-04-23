# Context Key Schema

## Recommended save path
`docs/specs/architecture/context_key_schema.md`

## 1. Purpose

This document preserves the historical architecture-side entry point for the Nexa context key schema.

Its purpose is to keep older references resolvable while making the authoritative boundary explicit.

## 2. Canonical Rule

The authoritative contract for context-key structure is:

- `docs/specs/contracts/context_key_schema_contract.md`

That document defines the contract-level rules for:
- domain naming
- key shape
- read/write expectations
- compatibility constraints

## 3. Architectural Interpretation

The context key schema is not only a formatting rule.
It is one of the engine invariants that protects deterministic context exchange between:
- input
- prompt
- provider
- plugin
- system
- output

The architecture meaning is therefore:
- all runtime exchange happens through a bounded key namespace
- resources do not communicate through hidden side channels
- key shape is shared vocabulary, not arbitrary string convention

## 4. Canonical Key Form

Canonical key form:

`<domain>.<resource_or_slot>.<field>`

Representative domains:
- `input`
- `prompt`
- `provider`
- `plugin`
- `system`
- `output`

## 5. Relationship to Other Documents

Normative contract:
- `docs/specs/contracts/context_key_schema_contract.md`

Related architecture references:
- `docs/specs/architecture/execution_model.md`
- `docs/specs/contracts/execution_environment_contract.md`
- `docs/specs/contracts/plugin_contract.md`

## 6. Decision

This file exists as the architecture-side alias entry.
The contract file remains the authoritative specification.
