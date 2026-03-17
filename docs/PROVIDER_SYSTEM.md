# Provider System

Providers interface Nexa with AI model services.

See contract: `docs/specs/contracts/provider_contract.md`

See architecture: `docs/specs/architecture/universal_provider_architecture.md`

---

# Supported Providers

* OpenAI (GPT models)
* Anthropic (Claude models)
* Google Gemini
* Perplexity
* Codex

All implemented under `src/providers/`.

---

# Provider Responsibilities

* Send prompts to AI models (in node core phase)
* Receive and normalize model responses
* Handle errors and retry logic
* Record `ProviderTrace`
* Return `ProviderResult` with standardized `reason_code`

---

# Provider Abstraction

All providers implement `ProviderAdapter`.

`UniversalProvider` wraps any adapter and supports:
* Fallback adapter chain
* Safe mode (prefix to prompts)
* Provider fingerprinting for determinism validation

---

# Provider Execution Scope

Providers execute **only within the core phase of a node**.

pre and post phases must not call AI providers.

---

# Provider Result Contract

```python
ProviderResult:
    success: bool
    output: str
    reason_code: str
    latency_ms: int
    provider_trace: ProviderTrace
```

---

End of Provider System Document
