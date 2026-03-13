Nexa Claude Development Guide

Purpose
This document explains the development rules for Claude when working on the Nexa repository.

Claude must follow these rules when generating or modifying code.

Nexa is a contract-driven execution engine project and breaking the architecture rules is not allowed.


────────────────
1. Project Identity
────────────────

Project name: Nexa

Goal

Build an execution engine that enables reliable collaboration between AI systems while structurally reducing bug probability.

Nexa is NOT a workflow tool.

Nexa is an execution engine platform.


Core execution model

Circuit
↓
Node
↓
Execution Runtime
↓
Prompt / Provider / Plugin
↓
Artifact
↓
Trace


Node is the only execution unit.


────────────────
2. Architecture Rules
────────────────

Claude must follow the Nexa Architecture Constitution.

Reference

docs/FOUNDATION_RULES.md


Critical invariants

1. Node is the only execution unit.
2. Circuit connects nodes but does not execute logic.
3. Execution must be dependency-based.
4. Artifact storage is append-only.
5. Execution must remain deterministic.
6. Plugin write scope is restricted.
7. Contract-driven architecture must be preserved.


Forbidden patterns

pipeline execution engines
step-list workflow models
mutable artifact storage
unrestricted plugin writes
undocumented runtime mutation


────────────────
3. Project Structure
────────────────

Repository structure

src/

engine/
runtime/
plugins/
contracts/
cli/


docs/

BLUEPRINT.md
CODING_PLAN.md
FOUNDATION_RULES.md
specs/


tests/


Claude must never invent new project structure without instruction.


────────────────
4. Coding Rules
────────────────

Language

Python


Testing framework

pytest


General rules

1. Do not guess missing structures.
2. Do not invent non-existent files.
3. Do not modify architecture without instruction.
4. Do not break contracts.
5. Prefer minimal changes.


Code modification rules

Always output complete files.

Never output partial code snippets.


Multi-file changes must preserve

existing structure
public APIs
contracts


────────────────
5. Contract System
────────────────

Nexa uses contract-driven architecture.

Important contracts

artifact contract
plugin result contract
execution trace schema
validation engine contract
spec version registry


If a change violates a contract, the implementation must be rejected.


────────────────
6. Artifact Rules
────────────────

Artifacts are append-only.

Existing artifacts must never be modified.

Allowed

artifact.append()

Forbidden

artifact.update()
artifact.replace()


────────────────
7. Plugin Rules
────────────────

Plugins can only write to their own namespace.

Allowed

plugin.<plugin_id>.*

Forbidden

prompt.*
provider.*
output.*
artifact.*


────────────────
8. Working Context Schema
────────────────

Working context keys follow the schema

<context-domain>.<resource-id>.<field>

Examples

input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value


────────────────
9. Documentation Rules
────────────────

Documentation and code must stay synchronized.

Relevant documents

docs/BLUEPRINT.md
docs/CODING_PLAN.md
docs/specs/*


If a change affects system architecture, documentation must be updated.


────────────────
10. Spec-Version Sync
────────────────

Spec version changes require updating

src/contracts/spec_versions.py

Contract tests must remain valid.


────────────────
11. Testing Requirements
────────────────

All code must pass pytest.

Requirements

existing tests must not break
new features must include tests
contract tests must pass


Important test groups

artifact immutability tests
execution trace tests
spec-version sync tests


────────────────
12. Development Workflow
────────────────

Development follows this order

Design
↓
Implementation
↓
Tests
↓
Verification


Claude must not implement features without clear instructions.


────────────────
13. Hallucination Guard
────────────────

Claude must avoid the following

inventing project files
inventing APIs
guessing architecture
forcing tests to pass


If information is missing, Claude must ask for clarification.


────────────────
End of Guide
────────────────