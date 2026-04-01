# Designer AI Integration Architecture v0.1

## 1. Purpose

This document defines the architectural position of Designer AI in Nexa.

Designer AI is **not** an execution resource.
Designer AI is a **proposal-producing design layer** above the Nexa execution engine.

Its job is to transform natural-language user intent into safe, reviewable circuit proposals that may later become approved structural state.

## 2. Core Decision

Designer AI must not directly mutate committed structural truth.

All Designer-originated structural changes must pass through this boundary:

`Intent -> Patch -> Precheck -> Preview -> Approval -> Commit`

## 3. Layer Placement

```text
User
-> Designer Session Layer
-> Intent Normalizer
-> Patch Planner
-> Precheck Validator
-> Preview Builder
-> Approval Flow
-> Commit Gateway
-> Savefile / Commit Snapshot
-> Execution Engine
```

## 4. Main Responsibilities

### 4.1 Designer Session Layer
- keeps conversation context
- tracks current working save
- tracks revision/retry loop
- distinguishes create vs modify vs explain vs analyze

### 4.2 Intent Normalizer
- converts natural-language request into normalized design intent
- extracts scope, objective, constraints, assumptions, ambiguity

### 4.3 Patch Planner
- converts normalized intent into explicit patch operations
- never performs hidden structural mutation

### 4.4 Precheck Validator
- evaluates whether the proposal is blocked, warning-only, or confirmation-required
- checks structure, dependencies, resources, outputs, safety, and cost

### 4.5 Preview Builder
- explains what would change
- shows structural delta, output delta, risk, assumptions, and cost

### 4.6 Approval Flow
- collects explicit user decisions
- supports approve / reject / request revision / narrow scope / choose interpretation

### 4.7 Commit Gateway
- applies approved patch to create approved structural state
- prevents unapproved direct mutation

## 5. Non-Goals

Designer AI must not:
- redefine runtime/engine contracts
- bypass approval rules
- behave as a new execution resource type
- silently rewrite committed structure

## 6. Relationship to Storage System

Designer AI interacts with all three storage layers:

- **Working Save**: editable present-state target for drafts
- **Commit Snapshot**: approval-gated structural anchor after commit
- **Execution Record**: run history generated after executing a committed structure

## 7. Initial Product Scope

The first implementation should support:

- create circuit draft
- modify existing draft
- explain circuit
- analyze risk/cost/gaps
- repair broken structure
- optimize bounded scope

## 8. Decision

Designer AI in Nexa is a proposal-producing design layer for savefile creation and mutation.
It is not an execution resource.
It must not directly cross the commit boundary.
