# Designer AI Input Redaction Rules v0.1

## Recommended save path
`docs/specs/designer/designer_ai_input_redaction_rules.md`

## 1. Purpose

This document defines the canonical rules for what must be hidden,
removed, masked, or downgraded before information is sent to Designer AI.

Its purpose is to protect:
- authority boundaries
- engine invariants
- secrets and environment data
- unnecessary internal noise
- user safety and review boundaries

## 2. Core Decision

Not every available field should be sent to Designer AI.

Official rule:

- redact anything that grants hidden authority
- redact anything that is secret or environment-sensitive
- redact anything irrelevant to the current design task
- downgrade noisy internals into summaries when detailed raw content is unnecessary

In short:

Redaction is mandatory, not optional.

## 3. Mandatory Redaction Categories

The following must be redacted or replaced by safe placeholders.

### 3.1 Secrets and credentials
Redact:
- API keys
- access tokens
- credentials
- secret environment values
- hidden auth headers
- private connection strings

### 3.2 Hidden authority channels
Redact:
- direct commit handles
- internal bypass flags
- privileged override routes
- engine contract rewrite capabilities
- non-public approval shortcuts

### 3.3 Irrelevant internal engine state
Redact by default:
- low-level transient runtime internals
- non-material scheduler bookkeeping
- irrelevant parser artifacts
- raw validator internals not needed for design
- unbounded internal traces

### 3.4 Non-material UI state
Redact by default:
- panel geometry
- local visual arrangement
- transient UI-only layout state
unless the design task explicitly concerns UI continuity rules

### 3.5 Unsafe historical noise
Redact or summarize:
- giant raw transcripts
- stale rejected proposal dumps
- irrelevant run logs
- duplicate finding histories

## 4. Downgrade Instead of Delete Rules

Some data should not be passed raw,
but should still be represented safely.

### 4.1 Resource internals
Replace raw provider/plugin internals with:
- id
- status
- version
- tags
- restrictions
- safe notes

### 4.2 Validator internals
Replace raw validation payloads with:
- blocking findings
- warning findings
- confirmation findings
- reason codes
- concise summaries

### 4.3 Execution history
Replace raw execution record bodies with:
- run summary
- failure class
- affected nodes
- cost/latency summary
- top-level artifact references if relevant

## 5. Redaction by Task Mode

### 5.1 CREATE_CIRCUIT mode
Redact:
- unnecessary current-draft internal noise
- irrelevant historical run details
- irrelevant non-selected graph fragments

### 5.2 MODIFY / REPAIR / OPTIMIZE mode
Retain:
- touched-area reality
- findings and risks
- available resources
Redact:
- unrelated graph sectors if scope is narrow
- unrelated historical detail

### 5.3 EXPLAIN / ANALYZE mode
Retain enough structure for explanation or diagnosis,
but still redact secrets, hidden authority, and irrelevant engine internals.

## 6. Placeholder Rules

When redaction occurs, use explicit placeholders where useful.

Examples:
- `<redacted_secret>`
- `<non_authoritative_reference_only>`
- `<internal_engine_detail_omitted>`
- `<large_history_summarized>`

The model must be able to tell that data was intentionally withheld.

## 7. Authority Redaction Rules

The following must never appear as usable authority in Designer input:

- commit permission
- approval completion when not true
- bypass-precheck permission
- bypass-preview permission
- bypass-approval permission
- direct committed-truth mutation permission

If such concepts need to appear, they must appear only inside `forbidden_authority`.

## 8. Scope Redaction Rules

When the active scope is narrow:
- redact unrelated node details
- redact unrelated edge details
- redact unrelated outputs
- summarize graph-wide metrics only if helpful

Do not force Designer AI to reason over the full graph when only a bounded slice is relevant.

## 9. Historical Redaction Rules

### 9.1 Keep only what helps current design
Preserve:
- prior rejection reasons
- last user correction
- unresolved risk lineage
- last relevant failure summary

### 9.2 Remove repetitive past detail
Redact:
- redundant revision loops
- repeated identical rejection messages
- stale exploratory branches no longer relevant

## 10. Safety Redaction Rules

When sensitive or risky domains are involved,
retain the safety classification and required review policy,
but redact unnecessary raw sensitive content.

## 11. Redaction Failure Rule

If a payload cannot be safely exposed without leaking:
- hidden authority
- secrets
- unsafe internals

then the payload must be transformed before exposure.
Do not send it raw “just this once”.

## 12. Decision

Designer AI input redaction must protect:
- secrets
- authority boundaries
- engine internals
- scope discipline
- signal-to-noise quality

The canonical rule is:
redact first, then expose only what bounded design requires.
