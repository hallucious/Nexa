# Nexa Project Scope

## Purpose

This document defines the scope of the Nexa project.

---

# What Nexa Is

Nexa is an **AI execution engine**.

It provides a deterministic runtime environment for orchestrating multiple AI systems through structured computation graphs (circuits) composed of nodes.

Nexa focuses on:

* deterministic execution
* traceable AI computation
* reproducible workflows
* structured orchestration
* contract-driven reliability

---

# What Nexa Is NOT

* A general automation tool
* A chatbot framework
* A workflow automation platform (not Zapier, not n8n)
* An AI model training framework
* A pipeline orchestrator with fixed step ordering

---

# Core Responsibilities

* AI workflow orchestration via circuit DAGs
* Node-based execution with dependency scheduling
* Artifact management (append-only, immutable, hashed)
* Execution trace recording (per-node, immutable)
* Contract validation
* Deterministic runtime scheduling
* Regression detection and policy gating

---

# MVP Components (Complete)

* Circuit execution (DAG-based dependency scheduling)
* Node execution with resource execution contract
* Prompt integration (PromptRegistry, PromptSpec)
* Provider abstraction (OpenAI / GPT, Codex, Anthropic Claude, Gemini, Perplexity)
* Plugin system (restricted namespaces)
* Artifact creation and hashing
* Execution trace logging (immutable)
* Contract validation engine
* ExecutionConfig canonicalization and registry
* Regression detection, formatting, and policy evaluation (PASS/WARN/FAIL)
* CLI for run / compare / diff / export / replay / info / task flows
* Test infrastructure (1022 passed, 3 skipped)

---

# Out of Scope (Current Phase)

* Visual workflow editors
* Graphical user interfaces
* Distributed execution systems
* Multi-agent ecosystem coordination
* Plugin marketplaces
* Cloud infrastructure services

---

# Design Priorities

Engine stability over feature expansion.

Deterministic behavior over convenience.

Architectural consistency over rapid experimentation.

Traceability over opaque automation.

Contract compliance over implementation speed.

---

# Public Demo Scope

The repository currently retains one official public demo path:

* `examples/real_ai_bug_autopsy_multinode/`

Deleted demo/example assets are out of scope for the current public baseline and must not remain as hidden test dependencies.

---

End of Project Scope