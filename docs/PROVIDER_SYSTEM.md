# Provider System

Providers connect Nexa to external AI model services.

See contract:
- `docs/specs/contracts/provider_contract.md`

See architecture:
- `docs/specs/architecture/universal_provider_architecture.md`

---

# Supported Providers

Current provider families implemented under `src/providers/`:

- OpenAI / GPT
- Codex
- Anthropic Claude
- Google Gemini
- Perplexity

Perplexity currently accepts both:

- `PERPLEXITY_API_KEY`
- `PPLX_API_KEY`

---

# Current Implementation Model

Nexa currently uses two provider layers.

## 1. Runtime-facing provider contract

Defined in:

- `src/contracts/provider_contract.py`

This is the contract consumed by runtime components such as the node execution path and provider executor.

## 2. Provider-family implementation layer

Defined in:

- `src/providers/provider_contract.py`
- `src/providers/universal_provider.py`
- `src/providers/adapters/`

This layer handles:

- provider-specific HTTP/API behavior
- normalized result envelopes
- safe-mode wrapping
- routing / fallback behavior
- provider fingerprinting

---

# ProviderRequest / ProviderResult (current implementation)

The provider-family implementation layer currently uses:

```python
ProviderRequest(
    prompt: str,
    temperature: float = 0.0,
    max_output_tokens: int = 1024,
    stop: Optional[list[str]] = None,
    seed: Optional[int] = None,
    model: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
)
```

```python
ProviderResult(
    success: bool,
    text: Optional[str],
    raw: dict,
    error: Optional[str],
    reason_code: Optional[str],
    metrics: ProviderMetrics,
)
```

Where:

```python
ProviderMetrics(
    latency_ms: int,
    tokens_used: Optional[int] = None,
)
```

This envelope is also backward-compatible with older tuple-style call sites through tuple unpacking support.

---

# UniversalProvider

`UniversalProvider` is the main provider implementation wrapper currently used by Claude and Perplexity, and it defines the shared behavior expected from modern provider integrations.

Responsibilities:

- normalize provider calls into `ProviderResult`
- apply safe-mode behavior when enabled
- support adapter routing / fallback chains
- compute deterministic provider fingerprints
- map provider exceptions to standard reason codes

---

# Provider Responsibilities

Providers are responsible for:

- sending prompts to model APIs
- returning normalized success/failure envelopes
- exposing deterministic fingerprint data
- preserving observability-safe metadata in `raw`
- avoiding secret leakage in error or raw payloads

Providers are **not** responsible for graph scheduling, node ordering, or artifact mutation.

---

# Provider Execution Scope

Providers execute only within the **core phase of a node**.

Pre and post phases must not issue AI model calls.

---

# Environment Initialization

Provider initialization from environment is now standardized through:

- `src/providers/env_diagnostics.py`

The current behavior is:

1. If the required key already exists in the process environment, provider creation succeeds immediately.
2. If no key is present, Nexa checks for a `.env` file.
3. If `.env` exists but `python-dotenv` is unavailable, Nexa reports that explicitly.
4. If `.env` is present and loadable but the required key is still missing, Nexa reports the missing key explicitly.

This behavior is implemented for:

- OpenAI / GPT
- Codex
- Claude
- Gemini
- Perplexity

---

# Environment Variables Currently Used

## OpenAI family

- `OPENAI_API_KEY`

## Claude

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `ANTHROPIC_TIMEOUT_SEC`

## Gemini

- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_FALLBACK_MODEL`
- `GEMINI_THINKING_BUDGET`

## Perplexity

- `PERPLEXITY_API_KEY`
- `PPLX_API_KEY` (alias)
- `PPLX_MODEL`
- `PPLX_TIMEOUT_SEC`

---

# Provider Fingerprints

Providers expose a `fingerprint()` method used for determinism / observability tooling.

Fingerprint inputs exclude:

- API keys
- raw prompts
- secret tokens

Fingerprint inputs include only stable configuration such as:

- provider family
- endpoint
- model
- timeout
- safe-mode flag

---

End of Provider System Document
