from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple, List


SAFE_PREFIX = """[SAFE MODE ENABLED]
You must comply with platform safety policies.

If the original request asks for disallowed actions, do NOT provide instructions.
Instead, provide:
- High-level principles
- Risks and warnings
- Safe alternatives

Always stay within allowed content.
"""


@dataclass
class SafeModeResult:
    text: str
    used: bool
    stage: str
    category: str


def _env(key: str, default: str = "") -> str:
    v = os.environ.get(key)
    return v if v is not None else default


def classify_error(err: BaseException) -> str:
    """Best-effort categorization. Prefer explicit env override if present."""
    override = _env("HAI_SAFE_MODE_REASON", "")
    if override:
        return override

    msg = f"{type(err).__name__}: {err}".lower()
    if any(p in msg for p in ["policy", "refus", "safety", "violates", "blocked"]):
        return "POLICY_REFUSAL"
    if any(p in msg for p in ["too long", "context", "token limit", "payload too large", "maximum context"]):
        return "TOO_LONG"
    if any(p in msg for p in ["timeout", "rate limit", "429", "503", "502", "network", "temporarily", "try again"]):
        return "TRANSIENT_ERROR"
    if any(p in msg for p in ["invalid", "schema", "json", "bad request", "400"]):
        return "INVALID_REQUEST"
    return "UNKNOWN_ERROR"


def apply_safe_mode_prefix(prompt: str) -> str:
    if _env("HAI_SAFE_MODE", "0") == "1":
        return SAFE_PREFIX + "\n\n" + prompt
    return prompt


def preprocess_for_policy(prompt: str) -> str:
    # Keep semantics but reduce "instructional" framing; generic safe rewrite wrapper.
    guard = """[POLICY GUARD]
Rewrite your answer to be policy-compliant.
- Do not provide step-by-step instructions for wrongdoing.
- If the request is disallowed, provide safe alternatives and general info.
"""
    return guard + "\n\n" + prompt


def preprocess_for_invalid_request(prompt: str) -> str:
    # Nudge model to output strict JSON when schemas are involved.
    guard = """[FORMAT GUARD]
If the task requires JSON, output ONLY valid JSON. No prose. No markdown. No trailing commas.
"""
    return guard + "\n\n" + prompt


def chunk_text(text: str, max_chars: int) -> List[str]:
    if max_chars <= 0:
        return [text]
    if len(text) <= max_chars:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+max_chars])
        i += max_chars
    return chunks


def chunk_and_aggregate(
    original_prompt: str,
    call_fn: Callable[[str], str],
    *,
    max_chunk_chars: int = 12000,
) -> str:
    """Generic TOO_LONG strategy.
    1) Ask model to extract constraints/facts per chunk
    2) Ask model to produce final answer using extracted notes
    This is not perfectly lossless, but preserves key constraints deterministically.
    """
    chunks = chunk_text(original_prompt, max_chunk_chars)
    notes = []
    for idx, ch in enumerate(chunks, start=1):
        p = (
            f"[CHUNK {idx}/{len(chunks)}]\n"
            "Extract ALL constraints, requirements, interface details, and any MUST/SHOULD rules. "
            "Output as bullet points. Do not add new ideas.\n\n"
            + ch
        )
        notes.append(call_fn(p))
    agg_prompt = (
        "[AGGREGATE]\n"
        "You are given extracted notes from chunks of a longer prompt. "
        "Produce the final answer to the ORIGINAL task. "
        "Respect all constraints. If there is ambiguity, state it.\n\n"
        "=== EXTRACTED NOTES ===\n"
        + "\n\n".join(notes)
        + "\n\n=== ORIGINAL TASK (for reference) ===\n"
        + original_prompt[:2000]
    )
    return call_fn(agg_prompt)


def run_safe_mode(
    prompt: str,
    call_fn: Callable[[str], str],
    *,
    retries_transient: int = 2,
    backoff_seconds: float = 1.0,
    fallback_call_fn: Optional[Callable[[str], str]] = None,
) -> SafeModeResult:
    """One-stop safe execution wrapper implementing:
    1) POLICY_REFUSAL rewrite retry
    2) INVALID_REQUEST formatting retry
    3) TOO_LONG chunk+aggregate
    4) TRANSIENT retries + optional fallback model
    """
    used = False
    stage = "NORMAL"
    category = "OK"

    def _try(fn: Callable[[str], str], p: str) -> Tuple[bool, str, str]:
        try:
            return True, fn(p), "OK"
        except Exception as e:  # noqa: BLE001
            return False, str(e), classify_error(e)

    # Stage 0: normal
    ok, out, cat = _try(call_fn, apply_safe_mode_prefix(prompt))
    if ok:
        return SafeModeResult(text=out, used=False, stage=stage, category=category)

    used = True
    category = cat

    # Stage 1: transient retry
    if category == "TRANSIENT_ERROR":
        stage = "TRANSIENT_RETRY"
        for _ in range(retries_transient):
            time.sleep(max(0.0, backoff_seconds))
            ok, out, cat = _try(call_fn, apply_safe_mode_prefix(prompt))
            if ok:
                return SafeModeResult(text=out, used=True, stage=stage, category=category)

        if fallback_call_fn is not None:
            stage = "FALLBACK_MODEL"
            ok, out, cat = _try(fallback_call_fn, apply_safe_mode_prefix(prompt))
            if ok:
                return SafeModeResult(text=out, used=True, stage=stage, category=category)

    # Stage 2: policy rewrite
    if category == "POLICY_REFUSAL":
        stage = "POLICY_REWRITE"
        ok, out, cat = _try(call_fn, apply_safe_mode_prefix(preprocess_for_policy(prompt)))
        if ok:
            return SafeModeResult(text=out, used=True, stage=stage, category=category)

        if fallback_call_fn is not None:
            stage = "FALLBACK_MODEL"
            ok, out, cat = _try(fallback_call_fn, apply_safe_mode_prefix(preprocess_for_policy(prompt)))
            if ok:
                return SafeModeResult(text=out, used=True, stage=stage, category=category)

    # Stage 3: invalid request format retry
    if category == "INVALID_REQUEST":
        stage = "FORMAT_RETRY"
        ok, out, cat = _try(call_fn, apply_safe_mode_prefix(preprocess_for_invalid_request(prompt)))
        if ok:
            return SafeModeResult(text=out, used=True, stage=stage, category=category)

    # Stage 4: too long chunk/aggregate
    if category == "TOO_LONG":
        stage = "CHUNK_AGGREGATE"
        try:
            out = chunk_and_aggregate(prompt, lambda p: call_fn(apply_safe_mode_prefix(p)))
            return SafeModeResult(text=out, used=True, stage=stage, category=category)
        except Exception as e:  # noqa: BLE001
            if fallback_call_fn is not None:
                try:
                    out = chunk_and_aggregate(prompt, lambda p: fallback_call_fn(apply_safe_mode_prefix(p)))
                    return SafeModeResult(text=out, used=True, stage="CHUNK_AGGREGATE_FALLBACK", category=category)
                except Exception:
                    pass
            raise

    # If we reach here, propagate last failure as RuntimeError
    raise RuntimeError(f"SAFE_MODE failed: category={category}; last_error={out}")
