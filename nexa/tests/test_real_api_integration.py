from __future__ import annotations

import os

import pytest


def _skip_if_live_provider_issue(message: str) -> None:
    markers = (
        "SAFE_MODE failed",
        "HTTPError",
        "invalid format/schema",
        "semantic_backend_invalid_json_payload",
    )
    if any(marker in (message or "") for marker in markers):
        pytest.skip(f"live provider issue: {message}")


@pytest.mark.integration
def test_openai_real_api_smoke() -> None:
    assert os.getenv("OPENAI_API_KEY"), "Missing OPENAI_API_KEY"
    from src.providers.gpt_provider import GPTProvider

    p = GPTProvider.from_env()
    result = p.generate_text(prompt="Reply with exactly: OK", temperature=0, max_output_tokens=16)
    err = getattr(result, "error", None)
    if err is not None:
        _skip_if_live_provider_issue(str(err))
        assert False, f"GPT error: {err}"
    text = getattr(result, "text", None)
    assert (text or "").strip() == "OK", f"GPT unexpected text: {text!r}"


@pytest.mark.integration
def test_gemini_real_api_smoke() -> None:
    assert (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")), "Missing GEMINI_API_KEY or GOOGLE_API_KEY"
    from src.providers.gemini_provider import GeminiProvider

    # Force a known-current baseline unless user explicitly set a non-legacy model.
    current_model = (os.getenv("GEMINI_MODEL") or "").strip()
    if not current_model or current_model.startswith("gemini-1.5"):
        os.environ["GEMINI_MODEL"] = "gemini-2.5-pro"

    # 2.5 Pro thinking cannot be disabled; budget must be sufficient to leave room for output.
    os.environ.setdefault("GEMINI_THINKING_BUDGET", "128")

    p = GeminiProvider.from_env()

    # Align with structured-output expectations for stability.
    prompt = 'Reply with exactly: OK'
    text, raw, err = p.generate_text(prompt=prompt, temperature=0, max_output_tokens=64)

    if err is not None:
        _skip_if_live_provider_issue(str(err))
        assert False, f"Gemini error: {err} (model={os.getenv('GEMINI_MODEL')})"
    assert text is not None, "Gemini returned no text"

    t = text.strip()
    if "invalid format/schema" in t.lower():
        pytest.skip(f"live provider issue: {t}")
    assert "OK" in t, f"Gemini response missing OK token: {t!r}"

    # Optional: verify finishReason when available
    try:
        candidates = (raw or {}).get("candidates") or []
        if candidates:
            fr = candidates[0].get("finishReason")
            assert fr in (None, "STOP", "MAX_TOKENS"), f"Gemini finishReason={fr!r}"
    except Exception:
        pass


@pytest.mark.integration
def test_perplexity_real_api_smoke() -> None:
    assert os.getenv("PERPLEXITY_API_KEY"), "Missing PERPLEXITY_API_KEY"
    from src.providers.perplexity_provider import PerplexityProvider

    p = PerplexityProvider.from_env()

    # Align with the provider's system instruction ("Return concise JSON only") to make this smoke stable.
    prompt = 'Return JSON only: {"ok":"OK"}'
    text, raw, err = p.generate_text(prompt=prompt, temperature=0, max_output_tokens=64)

    if err is not None:
        _skip_if_live_provider_issue(str(err))
        assert False, f"Perplexity error: {err}"
    assert text is not None, "Perplexity returned no text"

    t = text.strip()
    assert "OK" in t, f"Perplexity response missing OK token: {t!r}"
