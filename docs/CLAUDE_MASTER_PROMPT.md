# Nexa Claude Master Prompt

You are contributing code to the Nexa project.

Before writing or modifying code, you must understand the architectural rules and development constraints of the system.

This project follows strict architectural principles and contract-driven design.

---

# Project Context

Nexa is an **AI execution engine** designed to orchestrate AI systems in a deterministic and traceable way.

The execution structure of Nexa is:

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

Node is the only execution unit in the system.

---

# Critical Architectural Rules

You must never violate the following rules.

1. Node is the only execution unit.

2. Circuits define execution topology but do not execute logic.

3. Execution must follow dependency resolution.

4. Artifacts are immutable.

5. Runtime execution must remain deterministic.

6. Plugins may only write to:

plugin.<plugin_id>.*

7. Code must respect system contracts.

If a requested implementation violates these rules, you must explain why it cannot be implemented safely.

---

# Development Environment

Language:

Python 3.11+

Testing framework:

pytest

All code changes must pass existing tests.

---

# Repository Structure

Core directories:

src/

engine
runtime
plugins
contracts
cli

docs/

ARCHITECTURE.md
CONCEPTS.md
FOUNDATION_RULES.md
ARCHITECTURE_CONSTITUTION.md

tests/

Maintain clear separation between system components.

---

# Code Generation Rules

When writing code:

* produce clear and deterministic logic
* avoid unnecessary complexity
* avoid hidden side effects
* avoid global mutable state
* prefer explicit data flow

Never introduce implicit execution order dependencies.

---

# Contract Driven Development

Nexa relies on explicit contracts.

Examples include:

artifact schema
execution trace schema
validation rule catalog

Code must not violate existing contracts.

---

# Test Requirements

All new functionality must include tests.

Tests must:

* validate deterministic behavior
* verify artifact correctness
* ensure contract compliance

All tests must pass before changes are considered valid.

---

# Documentation Synchronization

When modifying architecture or system behavior, documentation must be updated.

Relevant documents may include:

ARCHITECTURE.md
CONCEPTS.md
FOUNDATION_RULES.md
spec documents

Code and documentation must remain synchronized.

---

# AI Safety Rules

If you are uncertain about:

* architectural constraints
* system contracts
* execution model

you must ask for clarification instead of guessing.

Hallucinated implementations are not allowed.

---

# Development Priority

Development order in Nexa is:

Engine
Runtime
Core architecture
Developer tools
User interfaces

Engine stability must always take priority.

---

# Output Requirements

When producing code:

* follow the existing repository structure
* ensure compatibility with current architecture
* ensure tests pass
* avoid introducing architectural violations

Explain reasoning briefly when implementing non-trivial changes.

---

End of Claude Master Prompt
