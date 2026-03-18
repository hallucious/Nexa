# Nexa Claude Master Prompt

You are contributing code to the Nexa project.

Before writing or modifying code, understand these rules.

---

# Project Context

Nexa is an **AI execution engine** — deterministic, traceable, contract-enforced.

It is NOT a pipeline orchestrator, workflow tool, or step-list system.

```
Circuit → Node → Runtime → (Prompt/Provider/Plugin) → Artifact → Trace
```

**Node is the only execution unit.**

**Execution order is determined by dependency resolution, not a fixed pipeline.**

---

# Two-Level Execution Model

**System level (circuit/runtime):**
- Nodes execute when all upstream dependencies are satisfied
- Runtime schedules dynamically
- Parallel execution possible

**Node-internal contract:**
- Within a node: pre → core → post phases (optional)
- pre: validation, prompt resolution, plugin data prep
- core: AI call (only here)
- post: output validation, persistence, trace
- This is NOT a system-level pipeline

---

# Non-Negotiable Rules

1. **Node is the only execution unit**
2. **Circuits define topology only** — no execution logic
3. **System-level execution is dependency-driven** — no fixed global order
4. **Artifacts are immutable** — append-only, never modified
5. **Determinism is required** — same input → same output
6. **Plugins write only to `plugin.<plugin_id>.*`**
7. **All code must respect contracts** in `docs/specs/`

---

# Environment

Language: Python 3.11+
Test framework: pytest
All changes must pass: `python -m pytest`

---

# Code Generation Rules

* Clear, deterministic logic
* No hidden side effects
* No global mutable state
* Explicit data flow
* No implicit execution order dependencies

---

# Hallucination Guard

If uncertain about any constraint or API: **ask, do not guess**.

Never invent files, APIs, or behaviors. Never force tests to pass by weakening assertions.

---

End of Claude Master Prompt
