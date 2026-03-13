# Nexa Guide for AI Systems

## Purpose

This document is written specifically for **AI coding assistants** working on the Nexa project.

Examples include:

Claude
GPT-based coding assistants
GitHub Copilot
Cursor AI

The purpose of this document is to help AI tools understand the **architectural principles, system structure, and development rules** of Nexa.

---

# What Nexa Is

Nexa is an **AI execution engine**.

It orchestrates multiple AI systems through a structured runtime environment.

Nexa is not a simple prompt automation system.

Instead, it provides a deterministic execution framework for AI computation graphs.

---

# Core Execution Model

The fundamental execution structure of Nexa is:

Circuit
↓
Node
↓
Runtime
↓
Prompt / Provider / Plugin
↓
Artifact
↓
Trace

Key idea:

Node is the only execution unit.

---

# Critical Architectural Rules

AI tools must respect these invariants when generating code.

1. Node is the only execution unit.

2. Circuits define topology but do not execute logic.

3. Execution must follow dependency resolution.

4. Artifacts are immutable.

5. Runtime behavior must remain deterministic.

6. Plugins must operate within restricted namespaces.

Violating these rules breaks the architecture.

---

# Plugin Write Restrictions

Plugins may only write to:

plugin.<plugin_id>.*

Plugins must never modify unrelated runtime domains.

---

# Artifact Model

Artifacts represent outputs produced during execution.

Artifacts are append-only.

Existing artifacts must never be modified.

New outputs must create new artifacts.

---

# Runtime Guarantees

The Nexa runtime guarantees:

deterministic execution
traceable execution
contract compliance
immutable artifacts

AI-generated code must not break these guarantees.

---

# Repository Structure

Core project layout:

src/

engine
runtime
plugins
contracts
cli

docs/

ARCHITECTURE.md
CONCEPTS.md
DEVELOPMENT.md
FOUNDATION_RULES.md
ARCHITECTURE_CONSTITUTION.md
VISION.md

tests/

AI tools should respect this separation of concerns.

---

# Test Requirements

All code modifications must pass existing tests.

Run tests using:

pytest

New functionality should include new tests.

---

# Contract Driven Development

Nexa uses contract-based architecture.

Examples of contracts:

artifact schema
execution trace schema
validation rules
plugin result contracts

Code must remain compatible with existing contracts.

---

# Documentation Synchronization

When architectural changes are introduced, documentation must be updated.

Relevant documents may include:

ARCHITECTURE.md
CONCEPTS.md
FOUNDATION_RULES.md
specification documents

Documentation and implementation must remain synchronized.

---

# Development Priority

Nexa development follows this order:

Engine
Runtime
Core architecture
Developer tools
User interface

User interfaces must not compromise engine stability.

---

# Summary

When generating code for Nexa, AI systems must prioritize:

architectural consistency
deterministic execution
contract compliance
artifact immutability
test reliability

Following these rules ensures the long-term stability of the Nexa engine.

---

End of Nexa AI Guide
