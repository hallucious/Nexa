Spec ID: circuit_savefile_contract
Version: 1.0.0
Status: Partial
Category: misc
Depends On:


# Circuit Savefile Contract

Version: 1.0.0

This specification defines the persistent save format for a Circuit.

A Circuit Savefile represents a fully serializable description of
a graph that can be executed by GraphExecutionRuntime.

This contract guarantees that circuits can be:

- saved
- versioned
- shared
- deterministically replayed

---

# 1. Purpose

The Circuit Savefile is the **portable representation of an AI workflow**.

It contains:

- nodes
- edges
- execution references
- metadata

The savefile does **not contain runtime state**.

---

# 2. Savefile Location

Typical storage:

circuits/
  my_circuit.json

or

project/
  circuits/
    assistant.json

---

# 3. Root Schema

A Circuit Savefile MUST contain:

{
  "version": "1.0.0",
  "nodes": [],
  "edges": []
}

Optional:

{
  "metadata": {}
}

---

# 4. Node Structure

Each node represents a runtime execution unit.

Example:

{
  "id": "node_1",
  "execution_config_ref": "answer.basic"
}

Fields:

id (string)  
Unique identifier of the node.

execution_config_ref (string)  
Reference to ExecutionConfig stored in registry.

Optional:

inputs (dict)  
Static inputs bound to the node.

metadata (dict)

---

# 5. Edge Structure

Edges define data flow between nodes.

Example:

{
  "from": "node_1",
  "to": "node_2"
}

Fields:

from (string)  
source node id

to (string)  
target node id

Optional:

condition (string)  
conditional edge execution

priority (integer)

---

# 6. Example Circuit

{
  "version": "1.0.0",
  "nodes": [
    {
      "id": "n1",
      "execution_config_ref": "answer.basic"
    },
    {
      "id": "n2",
      "execution_config_ref": "reasoning.chain"
    }
  ],
  "edges": [
    {
      "from": "n1",
      "to": "n2"
    }
  ]
}

---

# 7. Runtime Execution Flow

Circuit Savefile
↓
GraphExecutionRuntime
↓
NodeSpecResolver
↓
ExecutionConfigRegistry
↓
NodeExecutionRuntime
↓
ProviderExecutor

---

# 8. Determinism Rules

The savefile must guarantee deterministic structure.

Requirements:

node ids must be unique  
edges must reference existing nodes  
cycles must follow engine policy

---

# 9. Validation

Before execution the following validations must run:

node id uniqueness  
edge node existence  
execution_config_ref existence

Failures must raise CircuitValidationError.

---

# 10. Versioning

The savefile uses semantic versioning.

Example:

1.0.0

Future schema changes must maintain backward compatibility.

---

# 11. Future Extensions

The savefile format allows future additions:

subgraphs  
module imports  
visual editor metadata  
runtime hints
