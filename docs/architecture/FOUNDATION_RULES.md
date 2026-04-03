# FOUNDATION_RULES

Version: 1.0.0

────────────────
Architecture Constitution
────────────────

This document defines the fundamental architectural rules of Nexa.

All systems MUST comply with these rules.

---

## 1. Execution Engine Principle

Nexa MUST be an execution engine.

Nexa MUST NOT be treated as:

- A workflow tool
- A pipeline system
- A prompt chaining system

---

## 2. Node Principle

- Node MUST be the only execution unit.
- No execution MUST occur outside a Node.

---

## 3. Circuit Principle

- Circuit MUST define only connections.
- Circuit MUST NOT execute logic.

---

## 4. Execution Model

- Execution MUST be dependency-based.
- Execution MUST follow DAG structure.
- Fixed pipeline execution MUST NOT be used.

---

## 5. Node Internal Phases

A Node MAY internally contain:

- pre phase
- core phase
- post phase

These phases:

- MUST remain internal to the Node
- MUST NOT form a system-level pipeline

---

## 6. Artifact Rule

- Artifacts MUST be append-only.
- Artifacts MUST be immutable.
- Existing artifacts MUST NOT be modified.

---

## 7. Determinism Rule

- Execution MUST be deterministic-friendly.
- Non-deterministic factors SHOULD be traceable.

---

## 8. Plugin Namespace Rule

Plugins MAY write only to:

plugin.<plugin_id>.*

Plugins MUST NOT write to:

- prompt.*
- provider.*
- output.*

---

## 9. Working Context Schema

The working context key MUST follow the canonical key family:

input.<field>
output.<field>
<context-domain>.<resource-id>.<field>

where the three-segment form is used for prompt/provider/plugin/system.

Example:

input.text  
prompt.main.rendered  
provider.openai.output  
plugin.format.result  
output.value  

---

## 10. Contract Rule

The system MUST follow a contract-driven architecture.

All components MUST comply with:

- execution contracts
- plugin contracts
- provider contracts
- prompt contracts

---

## 11. Spec Sync Rule

- Spec-version synchronization MUST be maintained.
- Spec and code MUST remain consistent.

Violation of this rule is considered a system error.

---

## 12. Violation Rule

Any violation of these rules:

- MUST be treated as an architectural violation
- MUST NOT be allowed in implementation

---

END OF FOUNDATION RULES
