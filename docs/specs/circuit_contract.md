# Circuit Contract (Node Circuit Definition Language)
Version: 1.1.0

Purpose:
Defines the canonical JSON schema for Node-based AI collaboration circuits.

Core Concepts:
- Node (ai_task | subgraph)
- Edge (next | conditional | on_fail)
- Exit Policy
- Deterministic Canonicalization
- Strict Validation

This document formalizes the circuit definition language as the single source of truth for **orchestration definition**.
Execution/orchestration enforcement is performed by the Engine/Runtime layer.

See BLUEPRINT.md for architectural context.
