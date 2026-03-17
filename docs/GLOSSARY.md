# Nexa Glossary

---

## Circuit

A directed acyclic graph (DAG) of nodes defining the computation topology.

Circuit defines structure only — it does not execute logic.

---

## Node

The smallest execution unit in Nexa. All computation occurs inside nodes.

Within a node, resources may execute through pre, core, and post phases (node-internal contract).

---

## Node Execution Phases (Pre / Core / Post)

Internal execution phases within a single node:

* **Pre**: validation, prompt resolution, plugin data preparation. No AI calls.
* **Core**: AI provider call. Plugin tool calls also allowed.
* **Post**: output validation, persistence, trace emission. No AI calls.

These phases are the **node's internal execution contract** — not a system-level pipeline.

---

## Runtime

The system responsible for dependency-based node scheduling, working context management, artifact creation, and trace recording.

---

## Dependency-Based Execution

The system-level execution model of Nexa. A node executes when all its upstream dependencies are satisfied. Execution order is determined dynamically by the runtime scheduler.

---

## ExecutionConfig

A versioned, schema-validated, canonical configuration object defining a node's resource execution behavior. Identified by a canonical hash. Nodes reference ExecutionConfig by ID, not inline logic.

---

## Prompt

Instructions rendered for an AI model. Variables resolved before sending to a provider.

---

## Provider

An interface to an AI model service (OpenAI, Anthropic, Gemini, etc.). Handles model invocation and result normalization.

---

## Plugin

An extension module for non-AI computation (transformation, ranking, validation, etc.).

Plugins write only to `plugin.<plugin_id>.*`.

---

## Artifact

An immutable, append-only execution output. Artifacts are hashed and never modified. New results create new artifacts.

---

## Execution Trace

An immutable complete record of runtime behavior. Contains per-node status, phase status, artifact lineage, and runtime metadata.

---

## Working Context

Shared data space used during execution. Key schema: `<context-domain>.<resource-id>.<field>`.

---

## Contract

A versioned rule defining expected behavior between system components. Enforced by tests.

---

## Deterministic Execution

Execution that produces identical results given identical inputs and configuration.

---

## RegressionResult

Structured output of regression detection comparing two execution runs. Contains node, artifact, and context regressions with typed reason codes and severity levels.

---

## PolicyDecision

Output of policy evaluation against a RegressionResult. Status: PASS, WARN, or FAIL with human-readable trigger lines.

---

End of Glossary
