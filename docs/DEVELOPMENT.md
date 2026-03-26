# Nexa Development Guide

Before modifying code, read:

- `docs/BLUEPRINT.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/FOUNDATION_RULES.md`
- `docs/TRACKER.md`

---

# Development Environment

Language target: Python 3.11+

## Recommended local setup

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

If you prefer dependency pin installation first:

```bash
pip install -r requirements.txt
```

---

# Provider Environment Setup

Nexa supports provider keys from either:

1. process environment variables
2. a project-root `.env` file

Canonical variables currently used by the codebase:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `PERPLEXITY_API_KEY`

Alias also supported:

- `PPLX_API_KEY` → accepted by the Perplexity provider

Example `.env`:

```dotenv
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
PERPLEXITY_API_KEY=your_perplexity_key
```

## Current env guidance behavior

When provider initialization fails, Nexa now distinguishes:

1. no `.env` file found
2. `python-dotenv` not installed
3. provider API key missing or empty

This behavior is implemented for:

- OpenAI / GPT
- Codex
- Claude
- Gemini
- Perplexity

---

# Running the official retained demo

The repository currently keeps one official demo:

```text
examples/real_ai_bug_autopsy_multinode/
```

Run it with:

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff run_a.json run_b.json
```

---

# Running Tests

```bash
python -m pytest
pytest -q
```

Current verified baseline:

```text
1029 passed, 3 skipped
```

All tests must pass. Never ignore failures.

---

# Test Categories

**Unit Tests** — component-level verification

**Contract Tests** — spec-version sync, document accumulation, foundation map consistency

**Runtime Tests** — execution behavior verification

**Regression Tests** — prevent previously fixed bugs

**Provider Tests** — provider routing, fingerprinting, observability, env guidance

Contract tests are critical because they enforce doc/code/architecture alignment.

---

# Repository Structure

```text
src/
    artifacts/      engine/         platform/
    circuit/        models/         policy/
    cli/            providers/
    config/         utils/          contracts/

docs/
    BLUEPRINT.md            FOUNDATION_MAP.md
    TRACKER.md              CONTRIBUTING.md
    DEVELOPMENT.md          GLOSSARY.md  INDEX.md
    architecture/           strategy/           ai/
```

The legacy prompt contract package has been fully removed. Prompt execution is now documented and implemented on the canonical `src/platform/prompt_*` path.


---

# Spec-Version Synchronization

Every active spec in `docs/specs/_active_specs.yaml` must:

1. exist at that path
2. have a `Version: X.Y.Z` header
3. match the version in `src/contracts/spec_versions.py`

Verify with:

```bash
pytest tests/test_spec_version_sync_contract.py
```

---

# Architectural Constraints

- **Node is the only execution unit.**
- **System-level execution is dependency-based.** No fixed global ordering.
- **Node-internal pre/core/post phases are a node contract.** Not a system pipeline.
- **Artifacts are append-only.** Never mutate existing artifacts.
- **Plugins write only to `plugin.<plugin_id>.*`.**
- **Savefiles are the primary executable artifact.** `.nex` includes both circuit definition and state.

---

# Pull Request Requirements

- Full test suite passes
- Architectural invariants remain intact
- Contracts remain valid
- New behavior includes targeted tests
- Documentation is updated when user-visible behavior changes

---

End of Development Guide
