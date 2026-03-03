# AI Provider Contract
Version: 1.1.0

- Spec ID: AI-PROVIDER
- Status: Active
- Scope: Provider-level text generation API used by Node Core execution.
- Related Specs: NODE-EXEC@1.1.0, (optional) CT-TRACE@1.0.0

---

## 1. Purpose
This contract standardizes the interface between the Engine/Node runtime and any AI Provider.
It guarantees a stable result envelope, consistent error taxonomy, and minimal metrics for observability.

---

## 2. Terminology
- Provider: A component that produces model-generated text given a prompt and generation settings.
- ProviderRequest: The input payload to the provider.
- ProviderResult: The standardized output payload from the provider.
- reason_code: Platform-wide taxonomy key that classifies failures consistently across providers.

---

## 3. Contract Invariants
1. A Provider MUST return a `ProviderResult` envelope for every call (success or failure).
2. Provider MUST NOT raise unhandled exceptions to the caller; exceptions MUST be captured into `ProviderResult`.
3. Provider MUST measure and return `latency_ms`.
4. Provider MAY return `tokens_used` when available; otherwise it MUST be `null`.
5. `raw` MUST be a JSON-serializable object (dict) and MUST NOT contain secrets.
6. The caller (Node runtime) is responsible for enforcing NODE-EXEC (AI calls occur only in Core).
7. A Provider MUST expose a stable `fingerprint()` string that changes when provider configuration changes (model, endpoint, major runtime flags).

---

## 4. ProviderRequest (Input Contract)
ProviderRequest MUST include:

- `prompt: string` (required)
- `temperature: number` (required)
- `max_output_tokens: integer` (required)

ProviderRequest MAY include:

- `stop: array[string] | null`
- `seed: integer | null` (not required for v1.0.0 determinism)
- `model: string | null` (provider-specific hint)
- `metadata: object | null` (caller-provided, must be JSON-serializable, must not contain secrets)

---

## 5. ProviderResult (Output Contract)

### 5.1 Schema (minimum fields)
ProviderResult MUST include:

- `success: boolean` (required)
- `text: string | null` (required)
- `raw: object` (required, JSON-serializable)
- `error: string | null` (required)
- `reason_code: string | null` (required)
- `metrics: object` (required)
  - `latency_ms: integer` (required)
  - `tokens_used: integer | null` (optional/nullable)

### 5.2 Semantics
- If `success == true`:
  - `text` MUST be a non-empty string (unless the provider explicitly supports empty output; if so, document it in provider-specific notes)
  - `error` MUST be null
  - `reason_code` MUST be null
- If `success == false`:
  - `text` MUST be null
  - `error` MUST be a human-readable message (no stack traces required, but allowed if sanitized)
  - `reason_code` MUST be non-null

---

## 6. reason_code Mapping Rules (Minimum)
A Provider MUST map failures to reason_code using the following minimum set:

- `AI.timeout` — provider call exceeded caller timeout budget
- `AI.provider_error` — upstream provider error (HTTP error, SDK error, unexpected response)
- `AI.policy_refusal` — provider refused due to policy/safety
- `SYSTEM.unexpected_exception` — any uncategorized exception

Notes:
- Additional reason codes MAY be introduced later, but the above MUST be supported for v1.0.0 compatibility.
- Providers SHOULD avoid leaking sensitive provider internals in `error`.

---

## 7. Node Integration Rules (ProviderResult → NodeResult)
When a Node Core step uses a provider:

1. Node runtime MUST call provider and obtain `ProviderResult`.
2. Node runtime MUST convert to the platform NodeResult contract:
   - `NodeResult.success = ProviderResult.success`
   - On success:
     - `NodeResult.output` MUST include at minimum `{ "text": ProviderResult.text }`
   - On failure:
     - `NodeResult.output = null`
     - `NodeResult.error = ProviderResult.error`
     - `NodeResult.reason_code = ProviderResult.reason_code`
3. Node runtime SHOULD propagate `metrics.latency_ms` and `metrics.tokens_used` into NodeResult metrics.

---

## 8. Security Requirements
1. Provider MUST NOT store or emit secrets in `raw`, `error`, or `metadata`.
2. Provider SHOULD redact keys/tokens if present in upstream SDK responses.
3. Provider MUST treat prompts as potentially sensitive data; downstream logging must follow platform policy.

---

## 9. Observability Requirements (Minimum)
- Provider MUST report `latency_ms`.
- Provider SHOULD report `tokens_used`.
- Provider MAY report additional metrics (e.g., model name, request id) in `raw` if non-sensitive.

---

## 10. Compatibility and Versioning
- This spec uses SemVer.
- Backward incompatible changes MUST bump MAJOR.
- Additive fields or expanded reason_code set MAY bump MINOR.
- Clarifications MAY bump PATCH.

---

## 11. Provider Fingerprint (v1.1.0)
A Provider MUST implement `fingerprint() -> string` (sha256 recommended).

Fingerprint input MUST exclude secrets and prompts. Recommended fields:
- provider name
- API family (e.g., openai.responses, anthropic.messages)
- endpoint base URL
- model name
- timeout settings
- SAFE_MODE enabled flag

Fingerprint MUST be deterministic (canonical JSON + sha256).

---

## 12. Non-Goals (v1.1.0)
- Tool-calling semantics
- Multi-modal inputs/outputs
- Streaming protocol contract
- Full determinism/replay guarantees

---

End of AI-PROVIDER v1.1.0
