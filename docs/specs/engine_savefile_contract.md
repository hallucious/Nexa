# Engine Savefile Contract
Spec ID: ENGINE-SAVEFILE
Version: 0.1.2
Status: Draft (Engine-rooted)

---

## 1. Scope

This contract defines the `.hai` savefile format for storing an entire Engine instance.
The savefile root unit is the Engine.

A savefile MUST represent:

- Engine definition (circuits, nodes, edges)
- Engine-level configuration
- Optional execution record (NOT checkpoint resume)
- Contract linkage (NODE-EXEC, CT-TRACE)

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
  "spec_version": "0.1.2",
  "root_kind": "ENGINE",

  "engine": {
    "engine_id": "string",
    "engine_version": "string",
    "created_at_utc": "ISO8601",
    "updated_at_utc": "ISO8601"
  },

  "contracts": {
    "node_execution_contract": { "spec_id": "NODE-EXEC", "spec_version": "1.0.0" },
    "circuit_trace_contract": { "spec_id": "CT-TRACE", "spec_version": "1.0.0" }
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
- provider configuration (no secrets)
- plugin registry (IDs only)
- prompt definitions or references

Each node MUST include:

{
  "node_id": "string",
  "execution_contract": {
      "spec_id": "NODE-EXEC",
      "spec_version": "1.0.0"
  }
}

---

## 6. runtime.json (Execution Record – OPTIONAL, NOT CHECKPOINT)

Purpose:

runtime.json is a record of what happened during execution.
It is NOT a resumable checkpoint.

The loader MUST NOT assume that runtime.json allows execution resume.

Allowed contents:

- execution_id
- started_at_utc
- finished_at_utc
- last_node_id
- node_results_summary
- selected_edges_summary
- reason_codes
- trace_summary_reference

Forbidden:

- hidden secrets
- external credentials
- direct execution stack snapshots
- provider internal mutable state
- guarantees of resumability

---

## 7. checksums.json (REQUIRED)

Format:

{
  "algorithm": "sha256",
  "files": {
    "definition.json": "hash",
    "manifest.json": "hash",
    "runtime.json": "hash or null"
  }
}

All files except artifacts MUST be hashed.

---

## 8. ZIP Security Requirements (MANDATORY)

Loader MUST:

1. Reject absolute paths
2. Reject paths containing ".."
3. Reject symlinks / junctions
4. Enforce maximum total uncompressed size
5. Enforce per-file size limit
6. Validate checksums before load
7. Reject duplicate filenames

---

## 9. Determinism Notes

Savefile guarantees structural determinism.
AI nondeterminism is out of scope unless replay metadata is explicitly supported in a future version.

---

## 10. Non-Goals

- Execution resume from runtime.json
- Tool-calling save semantics
- Distributed engine state
- Secret storage
- Embedded executable code

---

End of ENGINE-SAVEFILE v0.1.2
