# Engine Savefile Contract
Spec ID: ENGINE-SAVEFILE
Version: 0.2.0
Status: Draft (Engine-rooted)

---

## 1. Scope

This contract defines the `.hai` savefile format for storing an entire Engine instance.
The savefile root unit is the Engine.

A savefile MUST represent:

- Engine definition (circuits, nodes, edges)
- Engine-level configuration
- Optional execution record (NOT checkpoint resume)
- Contract linkage
- Registry-linked execution references
- Prompt / provider linkage by reference only

This contract is cumulative and extends the earlier engine-rooted savefile model to align with the current runtime architecture:

GraphExecutionRuntime
↓
NodeSpecResolver
↓
ExecutionConfigRegistry
↓
PromptRegistry
↓
ProviderExecutor
↓
NodeExecutionRuntime

---

## 2. Container Format

- Extension: `.hai`
- Container: ZIP
- Encoding: UTF-8
- Binary payloads allowed only under `/artifacts`

---

## 3. Required Top-Level Files

.hai (zip)
├─ manifest.json
├─ definition.json
├─ runtime.json (optional, record-only)
├─ refs.json (optional)
├─ checksums.json (required)
└─ artifacts/ (optional)

---

## 4. manifest.json (Engine Header – REQUIRED)

Minimum fields:

{
  "spec_id": "ENGINE-SAVEFILE",
  "spec_version": "0.2.0",
  "root_kind": "ENGINE",

  "engine": {
    "engine_id": "string",
    "engine_version": "string",
    "created_at_utc": "ISO8601",
    "updated_at_utc": "ISO8601"
  },

  "contracts": {
    "node_execution_contract": { "spec_id": "NODE-EXEC", "spec_version": "1.0.0" },
    "graph_execution_contract": { "spec_id": "GRAPH-EXEC", "spec_version": "1.0.0" },
    "execution_config_schema_contract": { "spec_version": "1.0.0" },
    "execution_config_registry_contract": { "spec_version": "1.0.0" },
    "prompt_contract": { "spec_version": "1.0.0" },
    "provider_contract": { "spec_version": "1.0.0" },
    "circuit_savefile_contract": { "spec_version": "1.0.0" }
  },

  "content_index": {
    "definition": "definition.json",
    "runtime": "runtime.json",
    "refs": "refs.json",
    "checksums": "checksums.json"
  },

  "security": {
    "no_secrets": true,
    "no_code": true,
    "zip_safety_required": true
  }
}

---

## 5. definition.json (Engine Definition – REQUIRED)

Represents the canonical Engine definition.

Must include:

- circuits[]
- nodes[]
- edges[]
- engine-level metadata
- registry-linked execution references
- prompt/provider references only (no secrets, no embedded provider code)

Each node MUST include either:

### 5.1 Registry-linked node form (recommended)

{
  "node_id": "string",
  "execution_config_ref": "string"
}

### 5.2 Expanded node form (allowed for export / debug only)

{
  "node_id": "string",
  "execution_config": {
    "config_id": "string",
    "version": "string",
    "prompt_ref": "string",
    "prompt_version": "string",
    "provider_ref": "string"
  }
}

Rules:

- Production savefiles SHOULD prefer `execution_config_ref`
- Embedded `execution_config` MUST still validate against ExecutionConfig contracts
- Prompt content itself SHOULD NOT be embedded unless explicitly exporting a self-contained package

---

## 6. refs.json (Reference Index – OPTIONAL)

`refs.json` records all external references used by the savefile.

Example:

{
  "execution_configs": [
    { "config_id": "answer.basic", "version": "1.0.0" }
  ],
  "prompts": [
    { "prompt_id": "g1_design", "version": "v1" }
  ],
  "providers": [
    { "provider_id": "provider.openai" }
  ],
  "plugins": [
    { "plugin_id": "plugin.guard.basic" }
  ]
}

Rules:

- refs.json is optional but recommended
- It is an index only, not an authority over definition.json
- If present, it MUST be consistent with definition.json

---

## 7. runtime.json (Execution Record – OPTIONAL)

This file is record-only and MUST NOT be treated as a checkpoint resume mechanism.

Allowed content:

- execution metadata
- trace summary
- observability summary
- run ids
- timestamps
- deterministic replay references

Forbidden content:

- provider secrets
- executable code
- mutable checkpoint state intended for hot resume

---

## 8. checksums.json (REQUIRED)

The savefile MUST contain checksums for every top-level payload except binary artifacts that are explicitly excluded by policy.

Example:

{
  "manifest.json": "sha256:...",
  "definition.json": "sha256:...",
  "runtime.json": "sha256:..."
}

---

## 9. Circuit Relationship

A `.hai` savefile is engine-rooted, but internally it may contain one or more circuit definitions.

Relationship:

Engine Savefile
↓
definition.json
↓
circuits[]
↓
Circuit Savefile-compatible structure
↓
nodes / edges / execution_config_ref

This contract therefore incorporates the Circuit Savefile Contract by reference.

---

## 10. Determinism Rules

The savefile must guarantee deterministic structure.

Requirements:

- node ids must be unique
- edge endpoints must reference existing nodes
- all `execution_config_ref` values must be resolvable or intentionally externalized
- prompt and provider references must be explicit
- savefile ordering should be canonical where possible

Given identical input definition, savefile generation MUST produce equivalent semantic content.

---

## 11. Security Rules

The savefile MUST NOT contain:

- API keys
- OAuth tokens
- provider secrets
- executable plugin code
- arbitrary Python code
- unsafe ZIP structures

Allowed:

- IDs
- references
- metadata
- trace summaries
- binary artifacts under `/artifacts` when policy allows

---

## 12. Load Algorithm

Engine load MUST follow this sequence:

1. Open ZIP safely
2. Validate required top-level files
3. Validate checksums
4. Parse manifest.json
5. Parse definition.json
6. Validate circuit/node/edge structure
7. Resolve execution references
8. Construct Engine / Circuit objects
9. Optionally attach runtime record

---

## 13. Save Algorithm

Engine save MUST follow this sequence:

1. Export current engine definition
2. Canonicalize nodes / edges / references
3. Write manifest.json
4. Write definition.json
5. Optionally write runtime.json
6. Optionally write refs.json
7. Generate checksums.json
8. Package as `.hai`

---

## 14. Versioning

The savefile uses semantic versioning.

Current version:

0.2.0

Version bump policy:

- MAJOR: incompatible container or root schema changes
- MINOR: backward-compatible structural extensions
- PATCH: wording / clarification / non-structural fixes

This document is a MINOR extension of the prior 0.1.2 draft because it adds reference-aware runtime linkage without invalidating the earlier engine-rooted container model.

---

## 15. Future Extensions

The savefile format allows future additions:

- subgraphs
- module imports
- visual editor metadata
- runtime hints
- signed savefiles
- portable self-contained export bundles

All extensions must remain backward compatible unless a MAJOR version bump is declared.
