# Nexa Core Concepts

## Purpose of This Document

This document explains the **core concepts of Nexa** in simple terms.

It is intended for:

* new developers
* contributors
* AI coding tools
* users exploring the system

Understanding these concepts is required before working with Nexa.

---

# What Nexa Is

Nexa is an **AI execution engine**.

It allows multiple AI systems to work together in a structured and reliable way.

Instead of calling one AI model once, Nexa allows you to create **structured AI computation graphs**.

These graphs define:

* what AI should do
* what order tasks should run
* how results should be stored

---

# Core Idea

Traditional AI usage looks like this:

User
↓
Prompt
↓
AI Model
↓
Result

Nexa changes this into a structured system:

Input
↓
Circuit
↓
Nodes
↓
AI Providers / Plugins
↓
Artifacts
↓
Final Output

This structure enables:

* automation
* reproducibility
* large-scale AI workflows

---

# Circuit

A **Circuit** is the top-level execution structure.

You can think of it as a **map of tasks**.

Example:

```
Node A → Node B → Node C
```

Or:

```
       → Node B →
Node A              → Node D
       → Node C →
```

A circuit defines:

* what nodes exist
* which nodes depend on others
* how tasks are connected

A circuit **does not perform computation itself**.

---

# Node

A **Node** is where actual work happens.

Every AI task in Nexa is executed inside a node.

Examples of node tasks:

* generating text
* analyzing documents
* evaluating outputs
* transforming data
* calling AI models

Nodes may use:

* prompts
* providers
* plugins

---

# Prompt

A **Prompt** is the instruction sent to an AI model.

Example:

```
Summarize the following article in three sentences.
```

Prompts may include variables.

Example:

```
Summarize the following text:

{{input.article}}
```

Prompts are rendered before being sent to the AI provider.

---

# Provider

A **Provider** is the system that connects Nexa to an AI model.

Examples:

* OpenAI
* Anthropic
* Google Gemini
* Local models

Providers handle:

* sending prompts to models
* receiving responses
* converting outputs into Nexa format

---

# Plugin

Plugins extend Nexa with additional capabilities.

Plugins perform tasks that are **not AI model calls**.

Examples:

* scoring outputs
* ranking results
* formatting data
* filtering responses
* data validation

Plugins run inside nodes.

Plugins cannot freely modify system data.

They can only write to:

```
plugin.<plugin_id>.*
```

---

# Artifact

Artifacts are the outputs produced during execution.

Examples:

* generated text
* structured JSON
* evaluation results
* intermediate data

Artifacts are **immutable**.

Once created, artifacts must never be modified.

New results must be written as new artifacts.

---

# Execution Trace

A **Trace** records what happened during execution.

Trace contains:

* node execution order
* resources executed
* artifacts produced
* timestamps
* runtime metadata

Trace allows:

* debugging
* auditing
* execution replay

---

# Working Context

Working Context is the shared data space used during execution.

All nodes read and write through this context.

Example values:

```
input.story
prompt.expand.rendered
provider.openai.output
plugin.rank.result
output.final_script
```

This shared context allows nodes to exchange information.

---

# Example: Simple Nexa Circuit

Imagine a user provides a short story.

Nexa could run a circuit like this:

Node 1
Expand the story into a full script

Node 2
Generate images for the scenes

Node 3
Evaluate the story quality

Node 4
Prepare the final output

Execution:

```
Input Story
   ↓
Node 1 (expand script)
   ↓
Node 2 (generate images)
   ↓
Node 3 (evaluate)
   ↓
Node 4 (final result)
```

Each step produces artifacts.

---

# Why Nexa Exists

Direct AI calls are difficult to scale and reproduce.

Problems include:

* inconsistent outputs
* lack of traceability
* hard debugging
* poor orchestration

Nexa solves this by introducing:

* structured execution
* deterministic runtime
* artifact tracking
* execution tracing

---

# Summary

Key concepts in Nexa:

Circuit
execution graph

Node
execution unit

Prompt
AI instructions

Provider
AI model interface

Plugin
data processing extension

Artifact
immutable execution output

Trace
execution history

Together, these components form the **Nexa AI execution engine**.

---

End of Concepts Document
