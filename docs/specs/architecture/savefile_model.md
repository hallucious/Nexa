# Savefile Model Specification (savefile_model.md)

## 1. Purpose

This document defines the **Savefile Model** for Nexa.

A savefile is the **primary artifact** of the Nexa system.
It encapsulates both:

* the **circuit definition**
* the **state**

This specification establishes the **structural, semantic, and architectural invariants** required for savefiles to be valid, portable, and compatible with both execution engines and future UI/visual editors.

---

## 2. Official Definition

A **savefile** is a self-contained artifact that includes:

> **Circuit + State**

It represents a fully reproducible execution unit.

The Nexa system **does not treat circuit-only files as primary artifacts**.
All executable artifacts MUST be represented as savefiles.

---

## 3. Scope

This specification defines:

* Savefile structure
* Required and optional sections
* Execution invariants
* External dependency rules
* UI/editor compatibility constraints

This specification does NOT define:

* Plugin implementation details
* Provider internal behavior
* Execution engine internals

---

## 4. Savefile Invariants

The following rules are **strict invariants**.

### 4.1 Self-Containment

A savefile MUST contain all information required to execute the circuit, except:

* plugin implementation code

No required execution data may exist outside the savefile.

---

### 4.2 Circuit + State Coexistence

A savefile MUST include both:

* circuit definition
* state

Separating circuit and state into different primary artifacts is not allowed.

---

### 4.3 Deterministic Structure

The structure of a savefile MUST be deterministic and parseable without ambiguity.

---

### 4.4 Node as Execution Unit

Each node MUST be an independent execution unit.

Execution is defined by **dependencies**, not pipeline ordering.

---

### 4.5 Resource Referencing

All execution resources MUST be referenced explicitly:

* prompts
* providers
* plugins

---

### 4.6 No External Execution Dependency

A savefile MUST NOT depend on:

* external execution_config files
* external prompt files

These must be embedded inside the savefile.

---

## 5. Top-Level Structure

A valid savefile MUST follow this structure:

```json
{
  "meta": {},
  "circuit": {},
  "resources": {},
  "state": {},
  "runtime": {},
  "ui": {}
}
```

---

## 6. Required Sections

### 6.1 meta

Metadata describing the savefile.

```json
"meta": {
  "name": "string",
  "version": "string",
  "description": "string"
}
```

---

### 6.2 circuit

Defines the execution graph.

#### nodes

Each node MUST define:

* id
* type
* resource reference
* inputs
* outputs

#### edges

Defines dependencies between nodes.

#### entry

Defines the starting node.

---

### 6.3 resources

Defines all execution resources.

#### prompts

* Prompt templates embedded as strings

#### providers

* Provider configuration (model, settings)

#### plugins

* Plugin entry references (not implementations)

---

### 6.4 state

Contains all execution state.

```json
"state": {
  "input": {},
  "working": {},
  "memory": {}
}
```

#### input

User-provided or initial data

#### working

Intermediate state used during execution

#### memory

Persistent or long-term state

---

## 7. Optional Sections

### 7.1 runtime

Stores execution results and artifacts.

```json
"runtime": {
  "last_run": {},
  "artifacts": []
}
```

Used for:

* debugging
* replay
* diff

---

### 7.2 ui

Used exclusively by visual editors.

```json
"ui": {
  "layout": {}
}
```

This section MUST NOT affect execution.

---

## 8. External Dependency Rules

Allowed external dependency:

* plugin implementation code

Disallowed external dependencies:

* execution config files
* prompt files
* required runtime state files

---

## 9. UI / Visual Editor Compatibility

The savefile MUST support UI systems by:

* separating concerns by top-level sections
* providing stable node identifiers
* allowing layout metadata in `ui`

Execution logic MUST remain independent of UI data.

---

## 10. Versioning and Migration

Each savefile MUST include a version field.

```json
"meta": {
  "version": "1.0"
}
```

Future changes MUST:

* preserve backward compatibility where possible
* define migration rules when breaking changes occur

---

## 11. Example (Minimal)

```json
{
  "meta": {
    "name": "Example",
    "version": "1.0"
  },
  "circuit": {
    "nodes": [],
    "edges": [],
    "entry": "node1"
  },
  "resources": {
    "prompts": {},
    "providers": {},
    "plugins": {}
  },
  "state": {
    "input": {},
    "working": {},
    "memory": {}
  }
}
```

---

## 12. Summary

The savefile is:

* the **single source of truth**
* a **self-contained execution artifact**
* a **UI-compatible structured model**

It unifies:

> **Circuit + State + Execution Context**

into one coherent system.
