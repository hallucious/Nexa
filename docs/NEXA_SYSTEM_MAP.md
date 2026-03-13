# Nexa System Map

## Purpose

This document provides a high-level map of the Nexa system.

Its goal is to allow developers and AI systems to understand the overall architecture of Nexa quickly.

---

# System Overview

Nexa is an **AI execution runtime** designed to orchestrate multiple AI systems through structured computation graphs.

The system transforms AI usage from simple prompt execution into deterministic runtime computation.

Execution structure:

Input
↓
Circuit
↓
Nodes
↓
Runtime Execution
↓
Artifacts
↓
Trace

---

# Core Architecture Layers

Nexa is organized into several architectural layers.

---

## Layer 1 — Circuit

Circuit defines the structure of AI computation.

Responsibilities:

* define nodes
* define dependencies
* represent execution graph

Circuit does not execute logic.

It only describes structure.

---

## Layer 2 — Node

Node is the fundamental execution unit.

Every AI operation happens inside a node.

Nodes may contain:

Prompt
Provider
Plugin

Nodes produce artifacts.

---

## Layer 3 — Runtime

The runtime executes nodes and manages execution state.

Responsibilities:

* dependency scheduling
* node execution
* working context management
* artifact creation
* execution trace recording

---

## Layer 4 — AI Resources

These components perform the actual computation.

Prompt

Defines the instructions sent to AI models.

Provider

Connects Nexa to AI model services.

Examples:

OpenAI
Anthropic
Google Gemini

Plugin

Performs non-AI processing.

Examples:

ranking
formatting
evaluation
validation

---

## Layer 5 — Artifact System

Artifacts store execution outputs.

Examples:

generated text
evaluation scores
structured data

Artifacts are immutable.

New results create new artifacts.

---

## Layer 6 — Trace System

The trace system records runtime behavior.

Trace includes:

node execution order
resource execution events
artifact lineage
runtime metadata

Trace enables debugging and reproducibility.

---

# Working Context

Working Context is the shared runtime data space.

Components exchange data through this structure.

Example keys:

input.story
prompt.script.rendered
provider.openai.output
plugin.rank.result
output.final

This allows nodes to communicate safely.

---

# Execution Model

Nexa uses dependency-based execution.

Nodes execute only when their dependencies are satisfied.

Example:

Node A
↓
Node B
↓
Node C

Parallel execution is possible:

Node A
↓
Node B and Node C
↓
Node D

This allows scalable AI workflows.

---

# Repository Structure

High-level repository structure:

src/

engine
runtime
plugins
contracts
cli

docs/

architecture documents
system concepts
development guides

tests/

unit tests
contract tests
runtime tests

This separation ensures maintainability.

---

# Architectural Invariants

The following rules must never be violated.

Node is the only execution unit.

Artifacts are immutable.

Execution must remain deterministic.

Plugins have restricted write access.

Contracts define system behavior.

These rules are defined in:

ARCHITECTURE_CONSTITUTION.md

---

# How Everything Connects

System interaction flow:

User Input
↓
Circuit Definition
↓
Runtime Scheduler
↓
Node Execution
↓
AI Providers / Plugins
↓
Artifact Creation
↓
Trace Recording

This pipeline forms the Nexa execution engine.

---

# Recommended Reading Order

For understanding Nexa architecture:

1. README.md
2. CONCEPTS.md
3. NEXA_SYSTEM_MAP.md
4. ARCHITECTURE.md
5. ARCHITECTURE_CONSTITUTION.md

This sequence provides a complete understanding of the system.

---

# Summary

Nexa is a deterministic AI execution runtime.

It transforms AI workflows into structured computation graphs.

The architecture ensures:

reproducibility
traceability
reliable AI orchestration

The System Map provides the high-level view required to navigate the entire Nexa project.

---

End of System Map
