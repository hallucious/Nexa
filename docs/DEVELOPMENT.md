# Nexa Development Guide

## Purpose

This document explains how to develop, test, and contribute to the Nexa project.

It is intended for:

* new developers
* open-source contributors
* AI coding tools
* maintainers

Before modifying the codebase, developers should understand the architectural rules defined in:

* `FOUNDATION_RULES.md`
* `ARCHITECTURE.md`
* `CONCEPTS.md`

---

# Development Philosophy

Nexa follows strict development principles.

Key goals:

* deterministic AI execution
* contract-driven architecture
* reproducibility
* high test reliability
* safe extensibility

The engine must remain stable as the system grows.

---

# Development Environment

Recommended environment:

Python 3.11+

Operating system:

Linux / macOS / Windows (WSL recommended)

Editor:

VS Code

Install dependencies:

```id="dev1"
pip install -r requirements.txt
```

Create virtual environment (recommended):

```id="dev2"
python -m venv .venv
source .venv/bin/activate
```

Windows:

```id="dev3"
.venv\Scripts\activate
```

---

# Running Tests

Nexa uses **pytest** as its testing framework.

Run tests:

```id="dev4"
python -m pytest
```

Quick run:

```id="dev5"
pytest -q
```

All tests must pass before committing code.

Test failures must never be ignored.

---

# Test Philosophy

Nexa uses multiple test layers.

Test categories include:

Unit Tests
component-level verification

Contract Tests
enforce system contracts

Runtime Tests
verify execution behavior

Regression Tests
prevent previously fixed bugs from returning

Contract tests are especially important because they guarantee that:

* documentation
* implementation
* architecture

remain consistent.

---

# Repository Structure

Core repository layout:

```id="dev6"
src/

engine/
runtime/
plugins/
contracts/
cli/


docs/

ARCHITECTURE.md
CONCEPTS.md
FOUNDATION_RULES.md
BLUEPRINT.md
CODING_PLAN.md


tests/
```

Separation principles:

* runtime logic in `src`
* specifications in `docs`
* validation in `tests`

---

# Code Style

General guidelines:

* write clear and readable code
* avoid unnecessary complexity
* prefer explicit logic
* document complex behaviors

Recommended style tools:

```id="dev7"
black
ruff
```

Example formatting:

```id="dev8"
black src
ruff check src
```

---

# Contribution Workflow

Typical contribution flow:

1. fork repository
2. create feature branch
3. implement changes
4. run tests
5. submit pull request

Example:

```id="dev9"
git checkout -b feature/my-feature
```

Commit changes:

```id="dev10"
git add .
git commit -m "implement feature"
```

Push branch:

```id="dev11"
git push origin feature/my-feature
```

Open a pull request on GitHub.

---

# Pull Request Requirements

A pull request must:

* pass all tests
* respect architecture rules
* avoid breaking contracts
* include tests for new functionality
* avoid unrelated refactoring

Pull requests that break architectural constraints will be rejected.

---

# AI Assisted Development

Nexa supports AI-assisted coding.

Recommended tools:

* Claude
* GitHub Copilot
* GPT-based assistants

AI tools must follow the project rules defined in:

```
.github/copilot-instructions.md
docs/CLAUDE_GUIDE.md
```

AI-generated code must still pass tests and follow architecture constraints.

---

# Architectural Constraints

Developers must respect Nexa's core invariants.

Important rules include:

Node is the only execution unit.

Execution must follow dependency-based scheduling.

Artifacts are append-only.

Plugins may only write to:

```
plugin.<plugin_id>.*
```

Execution must remain deterministic.

Violating these constraints breaks Nexa architecture.

---

# Adding New Features

When adding features:

1. check architecture rules
2. verify no contract violations
3. add tests
4. update documentation if necessary

Documentation must remain synchronized with the codebase.

---

# Debugging

Useful debugging strategies:

* inspect execution traces
* examine artifacts
* run minimal circuits
* compare deterministic outputs

Trace logs are often the fastest way to diagnose runtime behavior.

---

# Security Considerations

When interacting with AI providers:

* follow provider usage policies
* avoid unsafe prompt construction
* sanitize external inputs
* protect API credentials

Security violations must be fixed immediately.

---

# Summary

To contribute safely to Nexa:

* follow architecture rules
* respect system contracts
* maintain deterministic execution
* keep artifacts immutable
* ensure all tests pass

Following these principles ensures the stability and reliability of the Nexa engine.

---

End of Development Guide
