DOCUMENT
repo_map.md

Purpose

This document provides a high-level structural map of the Nexa repository.

It is designed for AI coding agents (Claude, GPT, etc.) to quickly understand:

- project architecture
- directory responsibilities
- execution flow
- key files

The goal is to prevent hallucinated structures and incorrect file modifications.

AI agents must read this file before performing any modification.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. PROJECT OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nexa is a deterministic AI execution engine.

Core concept:

AI systems are constructed as circuits.

Circuit
→ Node
→ Execution Runtime
→ Prompt / Provider / Plugin
→ Artifact
→ Trace

Node is the only execution unit.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. ROOT DIRECTORY STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Repository structure:

src/
tests/
docs/
examples/
tools/


Explanation

src
core implementation of Nexa runtime

tests
pytest test suite

docs
architecture documentation and specs

examples
example circuits

tools
development tools (coding kit, utilities)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. SOURCE CODE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/

engine/
circuit/
platform/
contracts/


3.1 engine

Engine runtime implementation.

Key responsibilities:

node execution
artifact creation
trace generation
runtime orchestration


Important files

src/engine/engine.py
main execution entrypoint

src/engine/node_execution_runtime.py
node runtime executor


3.2 circuit

Circuit and node abstraction.

Responsibilities

node definition
dependency graph
node execution stages


Key files

src/circuit/node.py
src/circuit/node_execution.py


3.3 platform

External integration layer.

Responsibilities

AI provider integration
plugin system
platform utilities


Example files

src/platform/provider_registry.py
src/platform/plugin_registry.py


3.4 contracts

Contract definitions.

Responsibilities

schema definitions
spec version sync
contract enforcement


Key file

src/contracts/spec_versions.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. DOCUMENTATION STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

docs/

BLUEPRINT.md
system architecture overview

CODING_PLAN.md
step-by-step implementation roadmap

specs/
contract documentation


spec categories

architecture
policies
validation


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. TEST STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tests/

Test suite is pytest-based.

Categories

engine tests
contract tests
execution tests
step tests


Naming pattern

test_stepXXX_*.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. EXECUTION FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Runtime execution sequence

User CLI
↓
Engine
↓
Circuit load
↓
Dependency resolution
↓
Node execution
↓
Provider / Plugin call
↓
Artifact write
↓
Trace record


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. KEY ARCHITECTURE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI coding agents must respect these invariants.

1. Node is the only execution unit

2. Circuit defines dependencies only

3. Artifact storage is append-only

4. Plugin write namespace is restricted

plugin.<plugin_id>.*

5. No pipeline architecture reintroduction

6. Execution must remain deterministic


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. FILE MODIFICATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before modifying any file:

1. Identify relevant module
2. Confirm directory responsibility
3. Avoid cross-layer coupling
4. Update tests if behavior changes
5. Ensure documentation sync


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. AI CODING AGENT WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI agents must follow this order.

1. Read repo_map.md
2. Inspect repository structure
3. Identify affected files
4. Propose change plan
5. Implement changes
6. Update tests
7. Validate with pytest


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. COMMON FAILURE MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI coding agents often fail due to:

hallucinated directories
incorrect runtime assumptions
modifying unrelated modules
breaking architecture invariants


This document exists to prevent those failures.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END