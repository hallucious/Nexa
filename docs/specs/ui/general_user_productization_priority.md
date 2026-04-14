# General User Productization Priority

## Recommended save path
`docs/specs/ui/general_user_productization_priority.md`

## 1. Purpose

This document defines the implementation priority order required to turn Nexa into a product that general users can actually use.

If Beginner Shell Compression Policy v1.2 defines how Nexa should be shown,
this document defines what must exist so that a general user can complete a meaningful first success loop and continue using Nexa successfully afterward.

This document uses **circuit** as the canonical product/spec term.
That does not override the beginner-shell display rule that may show **workflow** as a beginner-facing UI label.
The distinction is:

- spec / engine / canonical term: circuit
- beginner-facing display term: workflow (when beginner-shell policy applies)

## 2. Core Decision Criterion

Priority is determined by one rule:

A general user must be able to:
- start
- understand
- run
- read the result

After that, the next priority is:

A returning general user must be able to:
- find their circuits again
- revisit prior results
- continue where they left off
- get help when blocked
- use the product without exclusionary UX gaps

Until these loops are completed reliably,
sharing, collaboration, and account/community systems remain secondary.

## 3. Preconditions

The following assumptions apply to this priority order:

- engine contracts and architecture principles remain unchanged
- Beginner Shell Compression Policy v1.2 is implemented in parallel
- deployment strategy (SaaS vs local-first) is not yet fixed
- later stages may begin only after earlier blocking conditions are sufficiently resolved, though independent work may run in parallel where rational

## 4. Stage 1 — Establish the First-Success Loop

Goal:
A general user should be able to open Nexa and complete a first meaningful run without expert assistance.

### 4.1 Beginner Shell enforcement

**Problem**
Beginner Shell Compression Policy v1.2 exists as a policy, but not yet as enforced runtime UI behavior.
Without enforcement, advanced surfaces may leak into the first session and collapse the beginner experience.

**Implementation direction**
Implement the policy-level repository mapping in actual code.

Core targets:
- `src/ui/builder_shell.py`: Designer-first empty workspace default
- `src/ui/i18n.py`: beginner-facing terminology remapping
- `src/ui/panel_coordination.py`: advanced-surface visibility gating
- `src/ui/execution_panel.py`: first-success unlock detection

**Completion criterion**
A first-session beginner is prevented from seeing advanced surfaces before first success or explicit request.

---

### 4.2 API access barrier reduction

**Problem**
Current Nexa usage depends on raw environment-variable-based provider setup such as `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.
That is a direct beginner barrier.

**Implementation direction**
The beginner-facing product surface must not require raw environment-variable setup.

Possible implementation paths include:
- managed providers
- guided key setup UI
- another beginner-safe access path

The exact path remains open because this is not only a UI decision; it may involve product, billing, infrastructure, and policy choices.

**Related files**
- `src/providers/env_diagnostics.py`
- `src/providers/claude_provider.py`
- `src/designer/semantic_backend_presets.py`

**Completion criterion**
A beginner can begin using Nexa without needing to understand raw environment-variable-based provider setup.

---

### 4.3 Circuit template gallery

**Problem**
A first-time user may not know what Nexa can build.
A blank natural-language entry point alone is not enough for all users.

**Implementation direction**
Provide a validated starter circuit gallery connected to Designer circuit creation.

Representative categories should be covered, such as:
- summarization
- document analysis
- writing assistance
- classification / review analysis
- code review / code explanation

Template selection should connect naturally to the existing `CREATE_CIRCUIT` / proposal flow.

**Related files**
- `src/designer/proposal_flow.py`
- `src/contracts/savefile_factory.py`
- `src/ui/designer_panel.py`

**Completion criterion**
General users can choose from a representative set of validated starter circuits that clearly show what Nexa can do and allow them to reach first success quickly.

---

### 4.4 Friendly error messaging

**Problem**
Current surfaced error structures can expose engine-facing labels such as issue codes, failure points, or internal error markers that general users cannot act on.

**Implementation direction**
Apply the beginner-shell message format to error situations as well:

- status signal
- one-sentence cause
- one clear next action

Examples:
- Cannot run yet. Step 2 has no AI model selected. [Fix Step 2]
- Connection failed. Please check your internet connection. [Try Again]
- Authentication failed. Please check your connection settings. [Open Settings]

**Related files**
- `src/ui/execution_panel.py`
- `src/ui/validation_panel.py`
- `src/ui/i18n.py`

**Completion criterion**
A beginner-facing error is understandable and actionable without requiring engine knowledge.

---

### 4.5 Stronger execution result display

**Problem**
Current output summary structures such as `output_name` and `value_preview` are not sufficient for a general-user success experience.

**Implementation direction**
Result display must support at least:

- readable result presentation
- copy action
- type-aware result rendering for text, list-like content, and structured outputs

**Related files**
- `src/ui/execution_panel.py`
- `src/ui/artifact_viewer.py`

**Completion criterion**
A general user can read, understand, and immediately use the result of a successful circuit run.

---

### 4.6 External data input minimum path

**Problem**
Real general-user work is often driven by files and URLs rather than raw text alone.
A circuit system that only accepts plain text misses a large share of real-world use cases.

Examples:
- PDF documents
- spreadsheets
- images
- URLs / web pages

**Implementation direction**
Add a minimum beginner-safe external-data input path without breaking engine contracts.

Preferred initial scope:
- file upload entry
- URL input entry
- plugin-based ingestion path

This should be implemented through existing plugin / capability boundaries rather than by rewriting execution architecture.

**Related files**
- `src/platform/plugin_auto_loader.py`
- plugin namespace / plugin execution boundary
- relevant UI input surfaces in `src/ui/designer_panel.py` and `src/ui/builder_shell.py`

**Completion criterion**
A beginner can start at least one meaningful circuit using real external data such as a file or URL, not only raw text input.

## 5. Stage 2 — Reduce Execution Anxiety and Hesitation

Goal:
Reduce the fear and uncertainty a general user feels before pressing Run.

### 5.1 Cost visibility

**Problem**
Cost estimation logic exists internally, but user-facing cost visibility is not yet sufficiently surfaced.

**Implementation direction**
Surface both:

- pre-run estimated cost
- post-run actual usage/cost summary

Beginner-friendly wording may use relative phrasing first, such as:
- low expected usage
- moderate expected usage
- high expected usage

**Related files**
- `src/engine/budget_router.py`
- `src/engine/trace_intelligence.py`
- `src/ui/execution_panel.py`
- `src/designer/precheck_builder.py`

**Completion criterion**
A beginner can understand that running a circuit has a cost profile before execution and can see what was used after execution.

---

### 5.2 Execution waiting-state feedback

**Problem**
If a run appears silent for too long, general users may assume the product is broken even when the circuit is still progressing.

**Implementation direction**
Provide active waiting-state feedback during execution.

Minimum expectations:
- visible running state
- progress or checkpoint feedback when available
- recent event surface or simplified live status
- no “dead screen” during long-running operations

**Related files**
- `src/ui/execution_panel.py`
- notification / banner / toast related UI surfaces

**Completion criterion**
A user can tell that Nexa is still working and not frozen during long-running execution.

---

### 5.3 In-app contextual help

**Problem**
Specs for guided disclosure and onboarding exist, but a blocked user still needs an in-app way to understand the current problem and next action.

**Implementation direction**
Implement contextual help tied to the user’s current state.

Examples:
- why execution is blocked
- what this button does
- what to do next in the current stage
- beginner-safe explanation for current failure

This should be state-aware, not just a static FAQ surface.

**Related files**
- guided disclosure / onboarding-related UI surfaces
- validation / execution / designer panels

**Completion criterion**
A blocked beginner has an in-app route to understand the current obstacle and next step without leaving the circuit flow.

---

### 5.4 Mobile first-run minimum support

**Problem**
Responsive/mobile direction exists in spec form, but first-run mobile support is not yet an implemented product path.

**Implementation direction**
Do not aim for full mobile parity.
Only ensure that the core first-success path works on mobile:

1. enter goal
2. review preview
3. approve
4. run
5. read result

Graph editing, trace view, diff view, and deep inspection may remain deferred on mobile.

**Related files**
- `src/ui/builder_shell.py`
- `src/ui/designer_panel.py`

**Completion criterion**
A beginner can complete the minimum first-success loop from a mobile form factor.

---

### 5.5 Privacy and data-handling transparency

**Problem**
General users, especially those working with customer or company data, need to understand where their data goes when Nexa calls external providers.

**Implementation direction**
Add clear user-facing transparency around:
- what data is sent to external AI providers
- when provider calls occur
- what kind of data is stored locally
- what kind of data is not retained

This is both a trust requirement and, in many environments, a legal/compliance requirement.

**Completion criterion**
A user can understand the basic data-handling path of their inputs without reading engine code.

## 6. Stage 3 — Support Return Visits and Continued Use

Goal:
A user who already achieved first success should be able to come back and continue productively without friction.

### 6.1 Circuit list / circuit library surface

**Problem**
The underlying artifact/file model exists, but there is no sufficiently clear beginner-friendly UI surface for “my circuits”.

**Implementation direction**
Provide a user-facing circuit list/library surface that allows a returning user to:
- see their recent circuits
- reopen a circuit
- distinguish drafts vs recently run circuits
- find the correct circuit without understanding storage internals

**Completion criterion**
A returning user can easily find and reopen their prior circuits from a product-facing list surface.

---

### 6.2 Beginner-facing execution result history

**Problem**
ExecutionRecord exists structurally, but “show me what happened last time” is still too deeply tied to advanced trace/history surfaces.

**Implementation direction**
Expose a beginner-friendly result-history surface that prioritizes:
- prior result snapshots
- rerun / open result again
- last successful output
- recent execution timestamps

This must not require trace/timeline literacy.

**Completion criterion**
A returning user can reopen and understand a recent result without entering advanced trace tooling.

---

### 6.3 Onboarding continuity

**Problem**
UI continuity and workspace persistence exist in spec form, but first-run/onboarding progress continuity is not clearly established as a beginner-facing product feature.

**Implementation direction**
Persist enough onboarding progress to avoid forcing a partially onboarded user to start from zero when returning.

Examples:
- whether first success has already been achieved
- which beginner surfaces were unlocked
- whether the user was mid-way through first-run guidance

**Completion criterion**
A user who leaves during onboarding can return without losing all first-run progress context.

---

### 6.4 User feedback channel

**Problem**
There is no direct in-product route for a general user to say:
- this is confusing
- this failed unexpectedly
- I do not understand this screen

**Implementation direction**
Add a lightweight feedback/report path suitable for early product learning.

Examples:
- report confusing screen
- quick friction note
- bug report shortcut

**Completion criterion**
The product can receive structured early-user feedback without requiring external support channels.

## 7. Stage 4 — Inclusion and Product Completeness

Goal:
Remove avoidable exclusion and quality gaps for real users across language and accessibility boundaries.

### 7.1 Accessibility implementation

**Current practical state**
The current surfaced beginner / return-use product path now materially satisfies the Stage 4 accessibility line.

Implemented practical coverage includes:
- semantic labeling and surfaced section structure on shell / library / result / feedback paths
- readable surfaced status and result guidance
- non-color-only surfaced state communication
- materially accessible beginner / return-use rendering on the current product-facing path

**Completion judgment**
Closed at the `ffc479d` / `2285 passed, 14 skipped` baseline for the current surfaced beginner / return-use path.

This does not claim universal accessibility maturity for every historical or non-surfaced path.
It means the official Stage 4 product-facing accessibility line is now closed strongly enough to move on.

---

### 7.2 Localization completeness

**Current practical state**
The current surfaced Korean beginner / return-use product path now materially satisfies the Stage 4 localization line.

Implemented practical coverage includes:
- surfaced EN/KO key coverage on the current Phase 8 target UI files
- localized shell / library / result / feedback product wording
- localized builder-shell-connected help / privacy / mobile-first / starter-template surfaces
- localized action-schema labels and disabled-reason text on Korean shell/API paths
- localized product-facing terminology and metadata refinement on the current surfaced path

**Completion judgment**
Closed at the `ffc479d` / `2285 passed, 14 skipped` baseline for the current surfaced Korean beginner / return-use path.

This does not claim repository-wide exhaustive wording perfection.
It means a Korean beginner can now complete the current first-success and early return-use flows without Phase 8-blocking English leakage in critical surfaced UI copy.

## 8. Stage 5 — Product Expansion

These items become meaningful after the first-success loop and early return-use loop are stable.

### 8.1 User accounts and sessions

This becomes important if SaaS-style deployment is chosen.
If local-first deployment remains primary, the existing artifact/file-oriented model may remain sufficient for a while.

Implementation timing depends on product-distribution strategy.

### 8.2 Circuit sharing

This allows users to share circuits with others or import circuits from others.

This is a growth lever, not a first-success lever.

### 8.3 Community ecosystem

Examples:
- template marketplace
- user-generated circuit exchange
- collaborative review systems

These are downstream expansion systems, not immediate general-user blockers.

## 9. Summary Table

| Stage | Item | Current State | Completion Criterion |
|------|------|-----------|-----------|
| Stage 1 | Beginner Shell enforcement | Policy exists only | Code-level enforcement complete |
| Stage 1 | API access barrier reduction | Environment-variable oriented | Beginner-safe access path exists |
| Stage 1 | Circuit template gallery | Very limited examples | Representative validated starters exist |
| Stage 1 | Friendly error messaging | Engine-facing leakage possible | Status + cause + next action shown |
| Stage 1 | Stronger execution result display | Preview-level output only | Readable/copyable result screen exists |
| Stage 1 | External data input minimum path | Largely absent | File/URL-based first-success path exists |
| Stage 2 | Cost visibility | Internal estimation exists | Pre/post execution cost shown |
| Stage 2 | Execution waiting-state feedback | Partial runtime state only | No dead-screen execution experience |
| Stage 2 | In-app contextual help | Spec direction exists | State-aware in-app help exists |
| Stage 2 | Mobile first-run support | Spec-driven only | Core first-success loop works on mobile |
| Stage 2 | Privacy/data transparency | Largely absent | User-facing data path explanation exists |
| Stage 3 | Circuit list / library surface | Implemented server-backed library surface | Product-facing circuit list exists |
| Stage 3 | Beginner-facing result history | Implemented beginner-facing result-history surface | Simple result-history surface exists |
| Stage 3 | Onboarding continuity | Implemented server-backed onboarding continuity alignment | Return users resume beginner progress |
| Stage 3 | User feedback channel | Implemented lightweight in-product feedback channel | Product signal channel exists |
| Stage 4 | Accessibility implementation | Closed at `ffc479d` baseline | First-success path materially accessible |
| Stage 4 | Localization completeness | Closed at `ffc479d` baseline | Critical beginner flows fully localized |
| Stage 5 | User accounts/sessions | Absent | Depends on deployment decision |
| Stage 5 | Circuit sharing | File format exists | Added after Stage 1-4 stability |
| Stage 5 | Community ecosystem | Some design direction only | Added after Stage 1-4 stability |

## 10. Related Documents

- `docs/specs/ui/beginner_shell_compression_policy.md`
- `docs/specs/ui/runtime_bootstrap/core_runtime_ui_scope_lock.md`
- `docs/specs/ui/workspace_shell/08_onboarding_first_run_ux_scenarios.md`
- `docs/specs/ui/workspace_shell/10_beginner_advanced_shell_split.md`

## 11. Final Statement

Beginner Shell is about how Nexa is shown.

This document is about what must exist so that the beginner-facing Nexa is not only understandable, but actually usable, repeatable, and inclusive.

The correct first priority is not account systems or community features.

The correct first priority is completing the general-user first-success loop, then the return-use loop, then inclusion/completeness, and only after that product expansion.