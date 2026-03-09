# Universal Provider Architecture
Version: 1.0.0
Status: Official Contract
Spec ID: UNIV-PROVIDER

## 1. Purpose

Define the canonical architecture that enables Hyper-AI to support
multiple external AI vendors through a single Provider implementation.

This specification formalizes the separation between:

- UniversalProvider (core, platform-controlled)
- Adapter (vendor translation layer)
- External AI API (vendor endpoint)

This ensures:
- Centralized execution control
- Uniform drift detection
- Consistent trace enforcement
- Extensible vendor support without core fragmentation

---

## 2. Architectural Overview

Execution Flow:

Node
  ↓
Engine / Worker (execution enforcement)
  ↓
UniversalProvider (implements provider_contract)
  ↓
Adapter (vendor-specific translator)
  ↓
External AI API

Key Principle:
All policy, trace, and fingerprint enforcement remains in the Engine/Worker layer.
Adapters must not bypass platform enforcement.

---

## 3. UniversalProvider Responsibilities

UniversalProvider MUST:

1. Implement provider_contract fully.
2. Select adapter based on configuration.
3. Convert ProviderRequest into adapter payload.
4. Invoke adapter.send().
5. Convert adapter response into ProviderResult.
6. Generate deterministic fingerprint().
7. Remain policy-neutral (no vendor-specific logic embedded).

UniversalProvider MUST NOT:

- Perform vendor-specific payload shaping directly.
- Allow adapters to mutate Engine/Worker state.
- Allow adapters to write directly to trace.

---

## 4. Adapter Contract

Each Adapter MUST implement:

- name: str
- build_payload(request) -> dict
- send(payload) -> raw_response
- parse(raw_response) -> ProviderResult
- fingerprint_components() -> dict

Adapters MUST NOT:

- Access Engine internals
- Access Registry directly
- Write trace entries
- Modify Node or Worker state

Adapters are pure translation layers.

---

## 5. OpenAI-Compatible Adapter (Core Default)

The platform MUST include a default adapter that supports
OpenAI-compatible APIs.

This adapter enables compatibility with:

- OpenAI
- Together
- Groq
- Fireworks
- Mistral (OpenAI mode)
- Other OpenAI-compatible vendors

Configuration parameters:

- base_url
- model
- api_key
- timeout
- optional headers

---

## 6. Fingerprint Policy

UniversalProvider MUST generate fingerprint as:

sha256({
  provider: "UniversalProvider",
  adapter: adapter.name,
  model: model_name,
  endpoint: base_url,
  config_hash: sha256(sorted(config_items))
})

Fingerprint MUST:

- Change when model changes
- Change when endpoint changes
- Change when adapter changes
- Change when config changes

Worker MUST enforce fingerprint recording in trace (see Step92).

---

## 7. Drift Detection Guarantee

Any change in:

- Adapter
- Model
- Endpoint
- Config

MUST produce a different fingerprint.

This guarantees silent provider drift cannot occur.

---

## 8. Compatibility

This specification does not modify provider_contract.
UniversalProvider is a valid provider_contract implementation.

SemVer Impact:
- Independent spec v1.0.0
- No MAJOR change required

---

## 9. Enforcement

This specification is enforced by:

- Provider fingerprint contract tests
- Worker trace enforcement (Step92)
- Adapter isolation rule tests (future)

Violation of adapter boundary MUST fail CI.
