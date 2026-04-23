
DOCUMENT
runtime_flow.md

Purpose
This document explains the internal execution flow of the Nexa runtime so that developers and AI coding agents understand how circuits are executed.

HIGH LEVEL FLOW

User CLI
↓
Engine Initialization
↓
Circuit Load
↓
Dependency Graph Build
↓
Execution Planning
↓
Node Execution Runtime
↓
Provider / Plugin Invocation
↓
Artifact Write
↓
Trace Record
↓
Execution Complete


ENTRYPOINT

Execution starts from CLI:

nexa run examples/hello_circuit.yaml


ENGINE INITIALIZATION

File:
src/engine/engine.py

Responsibilities
- initialize runtime
- load providers and plugins
- start circuit execution


CIRCUIT LOADING

Circuit config example:

examples/hello_circuit.yaml

Responsibilities
- validate circuit
- register nodes
- determine dependencies


DEPENDENCY GRAPH

Nodes are organized as:

Circuit → Nodes → Dependencies

Rules:
- no cycles
- dependency-first execution


EXECUTION PLAN

Execution config example:

node = {
  "config_id": "...",
  "node_id": "..."
}


NODE EXECUTION RUNTIME

File:
src/engine/node_execution_runtime.py

Stages:

Node Start
↓
Prompt Preparation
↓
Provider Call
↓
Plugin Processing
↓
Artifact Creation
↓
Trace Logging
↓
Node Complete


PROVIDER

Providers generate responses from prompts.

Examples:
OpenAI
Anthropic
Echo provider


PLUGIN SYSTEM

Plugins extend runtime behavior.

Write namespace restriction:

plugin.<plugin_id>.*


ARTIFACTS

Example artifact:

{
  "node": "hello_node",
  "output": "Hello Nexa"
}

Rule:
Artifacts are append-only.


TRACE

Example events:

node_started
provider_called
artifact_written
node_completed


ARCHITECTURAL GUARANTEES

1. Node is the only execution unit
2. Execution follows dependency graph
3. Artifact append-only
4. Plugin namespace restricted
5. Deterministic execution
6. Trace reflects actual runtime events


AI CODING AGENT WORKFLOW

Before modifying runtime:

1. Read repo_map.md
2. Read runtime_flow.md
3. Identify execution stage
4. Preserve architecture invariants
