# Nexa — Traceable AI execution for debugging, diffing, and replay

Nexa is an **AI execution engine** for running circuits, capturing execution state, and explaining why one run diverged from another.

It does **not** make model outputs deterministic.
It makes the **execution envelope around non-deterministic AI calls** reproducible, inspectable, diffable, and debuggable.

---

## What is currently implemented

- Circuit execution with dependency-based scheduling
- Savefile-based `.nex` execution
- ExecutionConfig registry and validation
- Provider support for:
  - OpenAI / GPT
  - Codex
  - Anthropic Claude
  - Google Gemini
  - Perplexity
- Execution diff / regression tooling
- Audit pack export and replay
- Provider / runtime observability contracts
- Explicit environment guidance for missing `.env`, missing `python-dotenv`, and missing provider API keys

Current verified baseline:

```text
934 passed, 3 skipped
```

---

## Official demo kept in the repository

The repository currently keeps **one official demo**:

```text
examples/real_ai_bug_autopsy_multinode/
```

This demo shows how a very small wording change can cascade through a multi-node AI execution and flip a downstream decision.

Run it with:

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff run_a.json run_b.json
```

---

## Quick start

### 1. Create and activate a virtual environment

#### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 2. Configure provider keys

Nexa supports both shell environment variables and a project-root `.env` file.

Example `.env`:

```dotenv
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
PERPLEXITY_API_KEY=your_perplexity_key
```

Provider-specific aliases supported by the current code:

- Perplexity also accepts `PPLX_API_KEY`

### 3. Run the official demo

```bash
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_A.nex --out run_a.json
nexa run examples/real_ai_bug_autopsy_multinode/investment_demo_B.nex --out run_b.json
nexa diff run_a.json run_b.json
```

---

## Environment guidance behavior

When a provider is initialized from the environment, Nexa now distinguishes three setup failures explicitly:

1. **No `.env` file found**
2. **`python-dotenv` is not installed**
3. **The required provider API key is missing or empty**

This behavior is implemented for:

- OpenAI / GPT
- Codex
- Claude
- Gemini
- Perplexity

That means setup failures now tell you whether you need to:

- create `.env`
- install `python-dotenv`
- add the missing provider key

---

## CLI surface currently implemented

```text
nexa run <circuit>
nexa compare <run_a> <run_b>
nexa diff <left> <right> [--json] [--regression]
nexa export <run.json> --out <audit_pack.zip>
nexa replay <audit_pack.zip> [--strict]
nexa info
nexa task generate <feature>
nexa task prompt <feature> <step_id>
```

---

## Why Nexa exists

AI systems are hard to debug because output drift is usually observed only at the end.

Nexa makes it possible to inspect:

- which node changed
- which provider output changed
- how state changed across the run
- whether the final decision/regression is acceptable

---

## Repository status before GitHub release

- Official retained demo consolidated to `real_ai_bug_autopsy_multinode`
- Obsolete demo-coupled tests removed
- Provider env guidance unified across all supported provider families
- Documentation synchronized to the current public baseline

---

## Development

For architecture, contracts, and development workflow, start with:

- `docs/INDEX.md`
- `docs/BLUEPRINT.md`
- `docs/DEVELOPMENT.md`
- `docs/PROVIDER_SYSTEM.md`

