Nexa Claude Development Guide

Purpose
This document explains the development rules for Claude when working on the Nexa repository.

Nexa is a contract-driven execution engine. Breaking the architecture rules is not allowed.


────────────────
1. Project Identity
────────────────

Project name: Nexa

Goal: Build a deterministic AI execution engine with contract-enforced behavior,
full observability, and reproducible execution.

Nexa is NOT a workflow tool. NOT a pipeline system.

Core execution model:

Circuit
↓
Node  (only execution unit)
↓
Runtime  (dependency scheduler)
↓
Prompt / Provider / Plugin
↓
Artifact
↓
Trace


────────────────
2. Architecture Rules
────────────────

Reference: docs/architecture/FOUNDATION_RULES.md

Critical invariants:

1. Node is the only execution unit.
2. Circuit connects nodes but does not execute logic.
3. Execution is dependency-based at the system level.
   - Nodes execute when dependencies are satisfied.
   - No fixed global execution order.
4. Node-internal phases (pre/core/post) are an internal contract of a single node.
   - They are NOT a system-level pipeline.
   - AI calls allowed only in core phase.
5. Artifact storage is append-only.
6. Execution must remain deterministic.
7. Plugin write scope is restricted to plugin.<plugin_id>.*.
8. Contract-driven architecture must be preserved.


Forbidden:

System-level fixed pipeline execution (prompt → provider → plugin)
Step-list workflow models
Mutable artifact storage
Unrestricted plugin writes
Undocumented runtime mutation


────────────────
3. Project Structure
────────────────

src/

artifacts/
circuit/
cli/
config/
contracts/
engine/
models/
platform/
policy/
prompts/
providers/
utils/


docs/

BLUEPRINT.md
TRACKER.md
FOUNDATION_MAP.md
architecture/
strategy/
ai/
specs/


tests/


Claude must never invent new project structure without instruction.


────────────────
4. Coding Rules
────────────────

Language: Python

Testing framework: pytest

General rules:

1. Do not guess missing structures.
2. Do not invent non-existent files.
3. Do not modify architecture without instruction.
4. Do not break contracts.
5. Prefer minimal changes.
6. Always output complete files.
7. Never output partial code snippets.


────────────────
5. Contract System
────────────────

Important contracts:

artifact contract
plugin result contract
execution trace schema
validation engine contract
ExecutionConfig schema
regression_reason_codes catalog
spec version registry


If a change violates a contract, the implementation must be rejected.


────────────────
6. Artifact Rules
────────────────

Allowed: artifact.append()
Forbidden: artifact.update(), artifact.replace()


────────────────
7. Plugin Rules
────────────────

Allowed: plugin.<plugin_id>.*
Forbidden: prompt.*, provider.*, output.*, artifact.*, input.*


────────────────
8. Working Context Schema
────────────────

input.<field> / output.<field> / <context-domain>.<resource-id>.<field>

Examples:
input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value


────────────────
9. Node Execution Contract
────────────────

At the SYSTEM level: dependency-based execution.
Nodes execute when their upstream dependencies are satisfied.
No fixed global order.

At the NODE-INTERNAL level: pre/core/post phases.
- pre: validation, prompt resolution, plugin data prep
- core: AI provider call (only here)
- post: output validation, persistence, trace emission

Never describe the system as a "prompt → provider → plugin pipeline".


────────────────
10. Documentation Rules
────────────────

Relevant documents:
docs/BLUEPRINT.md
docs/TRACKER.md
docs/specs/*

If a change affects system architecture, update documentation.


────────────────
11. Spec-Version Sync
────────────────

Spec version changes require updating src/contracts/spec_versions.py.

Contract tests must remain valid.


────────────────
12. Testing Requirements
────────────────

All code must pass pytest.

Requirements:
- existing tests must not break
- new features must include tests
- contract tests must pass


────────────────
13. Hallucination Guard
────────────────

Forbidden:
- inventing project files
- inventing APIs
- guessing architecture
- forcing tests to pass

If information is missing: ask for clarification.


────────────────
End of Guide
────────────────
