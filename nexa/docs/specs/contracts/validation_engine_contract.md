# Validation Engine Contract

Spec ID: validation_engine_contract  
Version: 2.0.0  
Status: Official Contract  
Category: contracts  

---

# 1. Purpose

Validation Engine defines the **execution contract gate** of Nexa.

Validation is NOT a safety check.

It is a **deterministic execution enforcement system**.

Execution MUST be rejected if validation fails.

---

# 2. Validation Scope

Validation MUST verify:

## 2.1 Structural Layer
- EngineStructure integrity
- Entry node existence
- DAG constraint
- Node uniqueness
- Channel reference integrity

## 2.2 Determinism Layer
- Determinism configuration presence
- Node-level execution reproducibility requirements

---

# 3. Validation Target Model

Validation operates on:

```
Engine
→ EngineStructure
→ meta.node_specs
```

## 3.1 node_specs Contract

Each node MAY define:

```
node_specs[node_id] = {
    "provider_ref": str,
    "model": str,
    "temperature": float,
    "seed": int,
    "prompt_ref": str
}
```

---

# 4. Rule Catalog (Authoritative)

## 4.1 ENGINE

- ENG-001: entry_node_id must exist
- ENG-003: graph must be DAG

## 4.2 NODE / CHANNEL

- NODE-001: node_id must be unique
- CH-001: channels must reference valid nodes

## 4.3 DETERMINISM

- DET-001: determinism config must exist
- DET-002: provider_ref required
- DET-003: model required
- DET-004: temperature required
- DET-007: temperature must be 0 ≤ t ≤ 2
- DET-005: seed required
- DET-006: prompt_ref required

---

# 5. Output Contract

Validation MUST return:

```
ValidationResult = {
  "success": bool,
  "engine_revision": str,
  "structural_fingerprint": str,
  "applied_rule_ids": List[str],
  "violations": List[Violation]
}
```

Violation:

```
{
  "rule_id": str,
  "rule_name": str,
  "severity": "ERROR",
  "location_type": "engine" | "node",
  "location_id": str | null,
  "message": str
}
```

---

# 6. Success Condition

```
success = True
ONLY IF no violation with severity == ERROR
```

---

# 7. Execution Dependency

If:

```
validation.success == False
```

Then:

- Engine MUST NOT execute any node
- Execution MUST be rejected

---

# 8. Determinism Contract

Validation enforces:

```
Reproducibility = function(provider, model, temperature, seed, prompt)
```

Missing ANY component → ERROR

---

# 9. Validation Philosophy

Validation Engine is:

```
NOT a defensive system
BUT a deterministic execution contract enforcer
```

It guarantees:

- Reproducibility precondition
- Structural correctness
- Execution legitimacy

---

# 10. Contract Supremacy

Validation contract overrides:

- Execution logic
- Runtime behavior
- Node scheduling

If validation fails:

- Execution is invalid
- Revision must not be accepted

---

# End of Validation Engine Contract v2.0.0
