from __future__ import annotations


def _assert_fingerprint(fp: str) -> None:
    assert isinstance(fp, str)
    assert fp.startswith("sha256:")
    assert len(fp) == len("sha256:") + 64


def test_provider_fingerprint_is_present_stable_and_drift_sensitive():
    # This contract test enforces a stable provider identity primitive.
    # It must not require network calls or environment variables.

    from src.providers.gpt_provider import GPTProvider
    from src.providers.codex_provider import CodexProvider
    from src.providers.gemini_provider import GeminiProvider
    from src.providers.perplexity_provider import PerplexityProvider
    from src.providers.claude_provider import ClaudeProvider

    # GPT
    g1 = GPTProvider(api_key="k", model="m1", timeout_sec=30)
    g2 = GPTProvider(api_key="k", model="m2", timeout_sec=30)
    fp1 = g1.fingerprint()
    fp1b = g1.fingerprint()
    fp2 = g2.fingerprint()
    _assert_fingerprint(fp1)
    assert fp1 == fp1b
    assert fp1 != fp2

    # Codex
    c1 = CodexProvider(api_key="k", model="m1", timeout_sec=30)
    c2 = CodexProvider(api_key="k", model="m2", timeout_sec=30)
    fpc1 = c1.fingerprint()
    fpc2 = c2.fingerprint()
    _assert_fingerprint(fpc1)
    assert fpc1 != fpc2

    # Gemini
    ge1 = GeminiProvider(api_key="k", model="m1")
    ge2 = GeminiProvider(api_key="k", model="m2")
    fpge1 = ge1.fingerprint()
    fpge2 = ge2.fingerprint()
    _assert_fingerprint(fpge1)
    assert fpge1 != fpge2

    # Perplexity (dataclass)
    p1 = PerplexityProvider(api_key="k", model="m1")
    p2 = PerplexityProvider(api_key="k", model="m2")
    fpp1 = p1.fingerprint()
    fpp2 = p2.fingerprint()
    _assert_fingerprint(fpp1)
    assert fpp1 != fpp2

    # Claude
    a1 = ClaudeProvider(api_key="k", model="m1", timeout_sec=60)
    a2 = ClaudeProvider(api_key="k", model="m2", timeout_sec=60)
    fpa1 = a1.fingerprint()
    fpa2 = a2.fingerprint()
    _assert_fingerprint(fpa1)
    assert fpa1 != fpa2
