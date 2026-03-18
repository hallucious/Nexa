# Nexa

## Deterministic AI Execution Engine

Nexa is a runtime for building **deterministic, reproducible, and debuggable AI systems**.

Instead of isolated AI calls, Nexa executes **structured computation graphs (circuits)** with full traceability.

---

## Quick Start

Run the example:

```bash
nexa run examples/hello_world.nex
```

Expected output:

```json
{
  "result": {
    "state": {
      "message": "Hello Nexa",
      "hello_node": {
        "output": "Hello Nexa"
      }
    }
  }
}
```

---

## Why Nexa

Modern AI systems break at scale:

- You **cannot reproduce results**
- You **cannot debug execution**
- You **cannot trace decisions**

This makes reliable AI systems nearly impossible.

Nexa fixes this by turning AI execution into a **deterministic runtime system**.

---

## Core Model

Nexa transforms AI workflows into a structured execution pipeline:

```
Input
↓
Circuit (.nex)
↓
Nodes
↓
Providers / Plugins
↓
Artifacts
↓
Trace
```

Key principles:

- **Node is the only execution unit**
- **Artifacts are immutable**
- **Execution is deterministic**
- **Every step is traceable**

---

## Example Workflow

Input: a short story

Nexa execution:

1. Expand story into a script  
2. Generate scene images  
3. Evaluate narrative quality  
4. Produce final output  

This becomes a circuit:

```
Input
↓
expand_script
↓
generate_images
↓
evaluate_story
↓
produce_result
```

Each step produces artifacts and trace logs.

---

## Key Features

### Deterministic Execution
Same input → same output.

### Full Traceability
Every step is recorded and inspectable.

### Artifact System
Outputs are immutable and versionable.

### Multi-Provider Support
OpenAI, Anthropic, Google, local models.

### Contract-Driven Architecture
Execution rules are enforced by explicit contracts.

---

## Repository Structure

```
src/
tests/
docs/
examples/
```

---

## Status

Nexa is currently stabilizing the execution engine.

---

## Summary

Nexa is not a chatbot.

Nexa is an **execution engine for AI systems**.

It enables reliable, reproducible, and debuggable AI workflows.
