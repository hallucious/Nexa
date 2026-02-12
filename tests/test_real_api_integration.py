from __future__ import annotations

import os

import pytest


@pytest.mark.integration
def test_openai_real_api_smoke() -> None:
    # Fail (do not skip) if user explicitly runs integration tests but key is missing.
    assert os.getenv("OPENAI_API_KEY"), "Missing OPENAI_API_KEY"
    from src.providers.openai_provider import OpenAIProvider

    p = OpenAIProvider.from_env()
    text, raw, err = p.generate_text(prompt="Reply with exactly: OK", temperature=0, max_output_tokens=16)
    assert err is None, f"OpenAI error: {err}"
    assert (text or "").strip() == "OK", f"OpenAI unexpected text: {text!r}"


@pytest.mark.integration
def test_gemini_real_api_smoke() -> None:
    assert os.getenv("GEMINI_API_KEY"), "Missing GEMINI_API_KEY"
    from src.providers.gemini_provider import GeminiProvider

    # Gemini model identifiers change over time; older defaults (e.g. gemini-1.5-*) may return 404.
    # For integration smoke, force a known-current baseline unless the user explicitly set a non-legacy model.
    current_model = (os.getenv("GEMINI_MODEL") or "").strip()
    if not current_model or current_model.startswith("gemini-1.5"):
        os.environ["GEMINI_MODEL"] = "gemini-2.5-pro"

    # 2.5 Pro thinking cannot be disabled; budget must be sufficient to leave room for output.
    os.environ.setdefault("GEMINI_THINKING_BUDGET", "128")

    p = GeminiProvider.from_env()
    text, raw, err = p.generate_text(prompt="Reply with exactly: OK", temperature=0, max_output_tokens=16)
    assert err is None, f"Gemini error: {err} (model={os.getenv('GEMINI_MODEL')})"
    assert (text or "").strip() == "OK", f"Gemini unexpected text: {text!r}"

    # Optional: verify finishReason when available
    try:
        candidates = (raw or {}).get("candidates") or []
        if candidates:
            fr = candidates[0].get("finishReason")
            assert fr in (None, "STOP", "MAX_TOKENS"), f"Gemini finishReason={fr!r}"
    except Exception:
        # Do not fail on metadata parsing issues; content correctness already asserted.
        pass


@pytest.mark.integration
def test_perplexity_real_api_smoke() -> None:
    assert os.getenv("PERPLEXITY_API_KEY"), "Missing PERPLEXITY_API_KEY"
    from src.providers.perplexity_provider import PerplexityProvider

    p = PerplexityProvider.from_env()
    text, raw, err = p.generate_text(prompt="Reply with exactly: OK", temperature=0, max_output_tokens=16)
    assert err is None, f"Perplexity error: {err}"
    assert (text or "").strip() == "OK", f"Perplexity unexpected text: {text!r}"
