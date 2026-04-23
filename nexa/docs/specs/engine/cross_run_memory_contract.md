# Cross-Run Memory Contract v0.1

## Recommended save path
`docs/specs/engine/cross_run_memory_contract.md`

## 1. Status
Deferred.

## 2. Purpose

This document defines the future contract for memory that persists across multiple runs.

## 3. Core Rule

Cross-run memory changes what a run means across time and must therefore remain explicit, bounded, and auditable.

## 4. Minimum Future Contract Areas
- memory namespace model
- write/read policy
- retention and invalidation rules
- relation to working save / commit snapshot / execution record
- privacy/safety and audit boundaries

## 5. Decision

Cross-run memory is deferred because it is an architectural shift, not just another feature.
