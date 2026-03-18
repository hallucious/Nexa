import pytest

from src.providers.safe_mode import run_safe_mode


class CallCounter:
    def __init__(self):
        self.n = 0
        self.prompts = []

    def wrap(self, fn):
        def inner(p: str):
            self.n += 1
            self.prompts.append(p)
            return fn(p)
        return inner


def test_safe_mode_policy_refusal_rewrite_then_success():
    counter = CallCounter()

    def call_impl(p: str) -> str:
        # First call simulates a policy refusal; second call succeeds.
        if counter.n == 1:
            raise RuntimeError("policy refusal: blocked by safety")
        return "OK"

    res = run_safe_mode("ORIGINAL PROMPT", counter.wrap(call_impl), fallback_call_fn=None)
    assert res.text == "OK"
    assert res.used is True
    assert res.stage in ("POLICY_REWRITE", "FALLBACK_MODEL", "NORMAL")  # should be POLICY_REWRITE on success
    assert res.stage == "POLICY_REWRITE"
    assert counter.n == 2


def test_safe_mode_invalid_request_format_retry_then_success():
    counter = CallCounter()

    def call_impl(p: str) -> str:
        if counter.n == 1:
            raise RuntimeError("invalid request: json schema error")
        return "{\"ok\": true}"

    res = run_safe_mode("NEED JSON", counter.wrap(call_impl), fallback_call_fn=None)
    assert res.text == "{\"ok\": true}"
    assert res.used is True
    assert res.stage == "FORMAT_RETRY"
    assert counter.n == 2


def test_safe_mode_transient_retries_then_success():
    counter = CallCounter()

    def call_impl(p: str) -> str:
        # First two calls transient fail, third succeeds.
        if counter.n in (1, 2):
            raise RuntimeError("timeout while calling api")
        return "RECOVERED"

    res = run_safe_mode(
        "PROMPT",
        counter.wrap(call_impl),
        retries_transient=2,
        backoff_seconds=0.0,
        fallback_call_fn=None,
    )
    assert res.text == "RECOVERED"
    assert res.used is True
    assert res.stage == "TRANSIENT_RETRY"
    assert counter.n == 3


def test_safe_mode_transient_fallback_model_used():
    counter_main = CallCounter()
    counter_fb = CallCounter()

    def main_impl(p: str) -> str:
        raise RuntimeError("503 temporarily unavailable")

    def fb_impl(p: str) -> str:
        return "FALLBACK_OK"

    res = run_safe_mode(
        "PROMPT",
        counter_main.wrap(main_impl),
        retries_transient=1,
        backoff_seconds=0.0,
        fallback_call_fn=counter_fb.wrap(fb_impl),
    )
    assert res.text == "FALLBACK_OK"
    assert res.used is True
    assert res.stage == "FALLBACK_MODEL"
    assert counter_main.n >= 2  # initial + retry
    assert counter_fb.n == 1


def test_safe_mode_too_long_chunk_aggregate_path():
    counter = CallCounter()

    def call_impl(p: str) -> str:
        # First call fails with TOO_LONG. Subsequent calls (chunk extraction/aggregate) succeed.
        if counter.n == 1:
            raise RuntimeError("too long: maximum context exceeded")
        # For chunk extraction prompts, return deterministic bullets
        if p.startswith("[CHUNK"):
            return "- MUST keep A\n- MUST keep B"
        if p.startswith("[AGGREGATE"):
            return "FINAL ANSWER"
        return "OK"

    # Use small chunks to force multiple chunk calls during the test
    res = run_safe_mode(
        "X" * 25000,
        counter.wrap(call_impl),
        fallback_call_fn=None,
    )
    assert res.text == "FINAL ANSWER"
    assert res.used is True
    assert res.stage in ("CHUNK_AGGREGATE", "CHUNK_AGGREGATE_FALLBACK")
    assert res.stage == "CHUNK_AGGREGATE"
    assert counter.n >= 3  # initial fail + at least 1 chunk + aggregate
