Nexa AI Coding Policy

Purpose
This document defines the rules AI coding tools must follow when working in the Nexa repository.

These rules apply to:

* GitHub Copilot
* Claude
* ChatGPT
* any AI-assisted coding system

AI must follow these rules strictly.

────────────────

1. Project Identity
   ────────────────

Project: Nexa

Nexa is an **execution engine**, not a workflow automation tool.

Core execution structure

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
2. Architecture Constitution
────────────────

All code must follow the Nexa Architecture Constitution.

Reference

docs/FOUNDATION_RULES.md

Key invariants

* Node is the only execution unit
* Circuit connects nodes only
* Execution must be dependency-based
* Artifact storage is append-only
* Execution must remain deterministic
* Plugin write access is restricted
* Contract-driven architecture must be preserved

Violating these rules is not allowed.

────────────────
3. Forbidden Patterns
────────────────

AI must NOT introduce the following patterns.

pipeline execution engines

prompt → provider → plugin fixed pipelines

step-list workflow models

mutable artifact storage

plugins modifying unrelated namespaces

undocumented runtime state mutation

────────────────
4. Repository Structure
────────────────

AI must respect the existing project structure.

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

AI must NOT invent new folders without instruction.

────────────────
5. Coding Rules
────────────────

Language: Python
Testing framework: pytest

General rules

* prefer minimal modifications
* do not break existing architecture
* do not invent APIs
* do not modify unrelated modules
* do not remove existing behavior unless instructed

Code output rules

AI must output **complete files**.

Partial code snippets are not allowed when modifying files.

────────────────
6. Contract System
────────────────

Nexa uses contract-driven architecture.

Important contracts

artifact contract
plugin result contract
execution trace schema
validation engine contract
spec-version registry

Code changes must not violate contracts.

────────────────
7. Artifact Rules
────────────────

Artifacts are immutable.

Allowed

artifact.append()

Forbidden

artifact.update()
artifact.replace()

────────────────
8. Plugin Rules
────────────────

Plugins may only write to their namespace.

Allowed

plugin.<plugin_id>.*

Forbidden

prompt.*
provider.*
output.*
artifact.*

────────────────
9. Documentation Sync
────────────────

Documentation must stay synchronized with code.

Relevant documents

docs/BLUEPRINT.md
docs/CODING_PLAN.md
docs/specs/

If a feature changes architecture or behavior, documentation must be updated.

────────────────
10. Spec Version Sync
────────────────

Spec version changes require updating

src/contracts/spec_versions.py

Contract tests must remain valid.

────────────────
11. Testing Rules
────────────────

All changes must pass pytest.

Requirements

* existing tests must not break
* new features require tests
* contract tests must pass

Important test groups

artifact immutability tests
execution trace tests
spec-version sync tests

────────────────
12. Development Workflow
────────────────

Standard workflow

Design
↓
Implementation
↓
Tests
↓
Verification

AI must not implement large features without explicit instructions.

────────────────
13. Hallucination Guard
────────────────

AI must avoid the following behaviors.

inventing project files
inventing APIs
guessing architecture
forcing tests to pass

If required information is missing, AI must request clarification.

────────────────
End of Policy
────────────────
