from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple, List, Sequence, Any

from src.utils.nexa_config import (
    get_safe_mode_enabled as _get_safe_mode_enabled,
    get_safe_mode_link_mode as _get_safe_mode_link_mode,
    get_safe_mode_reason_override,
    get_safe_mode_strict_recovery_enabled as _get_safe_mode_strict_recovery_enabled,
)


# --- SAFE_MODE linkage controls -------------------------------------------------
# Gate2 can optionally consume SAFE_MODE metadata to explain (or refine) continuity decisions.
# Modes:
#   OFF   : no extra meta (default: OFF unless HAI_SAFE_MODE_LINK_MODE is set)
#   LIGHT : small, stable meta (used/category/stage + meaning_preserved + counts)
#   FULL  : includes before/after prompt and extracted anchors (can be large)
#
# Set via env:
#   HAI_SAFE_MODE_LINK_MODE=OFF|LIGHT|FULL
# -------------------------------------------------------------------------------

_LAST_SAFE_MODE_RESULT: Optional["SafeModeResult"] = None


def get_safe_mode_link_mode() -> str:
    return _get_safe_mode_link_mode()


def get_safe_mode_strict_recovery_enabled() -> bool:
    """Whether STRICT recovery loop is enabled.

    When enabled, SAFE_MODE may perform an additional retry if a rewrite step
    appears to have dropped MUST-KEEP anchors (meaning-preservation failure).
    This is OFF by default to keep behavior stable and tests deterministic.
    """
    return _get_safe_mode_strict_recovery_enabled()

def get_last_safe_mode_result() -> Optional["SafeModeResult"]:
    """Return last SAFE_MODE result produced in this process (best-effort)."""
    return _LAST_SAFE_MODE_RESULT


def clear_last_safe_mode_result() -> None:
    global _LAST_SAFE_MODE_RESULT
    _LAST_SAFE_MODE_RESULT = None


def _set_last_safe_mode_result(r: "SafeModeResult") -> None:
    global _LAST_SAFE_MODE_RESULT
    _LAST_SAFE_MODE_RESULT = r


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
    # Optional metadata (for Gate linkage / auditing). Always keep backward compatibility.
    meta: Optional[dict] = None


def _env(key: str, default: str = "") -> str:
    v = os.environ.get(key)
    return v if v is not None else default


def _get_attr(obj: Any, *names: str) -> Optional[Any]:
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None


def classify_error(err: BaseException) -> str:
    """Best-effort categorization.

    Notes:
    - Prefer explicit env override if present (useful in tests).
    - Tries to use structured fields (status_code/code) when available.
    """
    override = get_safe_mode_reason_override()
    if override:
        return override

    status = _get_attr(err, "status", "status_code", "http_status", "code")
    try:
        status_i = int(status) if status is not None and str(status).isdigit() else None
    except Exception:
        status_i = None

    msg = f"{type(err).__name__}: {err}".lower()

    # Transient first: if it's a retry-able transport / rate limit.
    if status_i in (408, 409, 429, 500, 502, 503, 504):
        return "TRANSIENT_ERROR"
    if any(p in msg for p in ["timeout", "timed out", "rate limit", "429", "503", "502", "network", "temporarily", "try again", "connection", "overloaded", "unavailable"]):
        return "TRANSIENT_ERROR"

    # Auth / Not found (model or endpoint)
    if status_i in (401, 403, 404):
        return "INVALID_REQUEST"
    if any(p in msg for p in ["unauthorized", "forbidden", "not found", " 401", " 403", " 404", "http error 401", "http error 403", "http error 404"]):
        return "INVALID_REQUEST"


    # Too long / context window
    if status_i == 413:
        return "TOO_LONG"
    if any(p in msg for p in ["too long", "context", "token limit", "payload too large", "maximum context", "context length", "prompt is too long", "max_tokens"]):
        return "TOO_LONG"

    # Invalid request / schema / JSON issues
    if status_i == 400:
        return "INVALID_REQUEST"
    if any(p in msg for p in ["invalid", "schema", "json", "bad request", "400", "malformed", "parse", "validation", "unrecognized"]):
        return "INVALID_REQUEST"

    # Policy/safety refusal (place after invalid/transient)
    if any(p in msg for p in ["policy", "refus", "safety", "violates", "blocked", "disallowed", "content policy", "cannot comply", "not allowed"]):
        return "POLICY_REFUSAL"

    return "UNKNOWN_ERROR"


def apply_safe_mode_prefix(prompt: str) -> str:
    if _get_safe_mode_enabled():
        return SAFE_PREFIX + "\n\n" + prompt
    return prompt


def _policy_severity_hint(error_text: str) -> str:
    """Return a coarse severity hint for policy handling.

    - SOFT: wording/tone can be adjusted (often generic 'policy/safety' message)
    - HARD: content is disallowed; must refuse instructions and offer safe alternatives
    """
    t = (error_text or "").lower()
    hard_markers = [
        "self-harm", "suicide", "weapon", "bomb", "explosive", "terror",
        "child", "sexual", "porn", "illegal", "fraud", "hack", "malware",
        "violence", "kill", "assass", "drug", "cocaine", "meth",
        "explicit", "minors",
    ]
    if any(m in t for m in hard_markers):
        return "HARD"
    # If the provider gives no detail, treat as SOFT first.
    return "SOFT"


def preprocess_for_policy(prompt: str, *, severity: str = "SOFT") -> str:
    # Keep semantics but reduce "instructional" framing; safe rewrite wrapper.
    if severity == "HARD":
        guard = """[POLICY GUARD - HARD]
The original request appears to include disallowed content.
Do NOT provide step-by-step instructions or actionable guidance for wrongdoing.
Instead:
- Briefly explain you can't help with that request
- Provide high-level, non-actionable safety information
- Offer safe, legal alternatives (e.g., prevention, support resources, lawful education)
"""
    else:
        guard = """[POLICY GUARD - SOFT]
Rewrite your answer to be policy-compliant and neutral.
- Avoid step-by-step instructions for wrongdoing
- Prefer high-level guidance, risks, warnings
- If any part is disallowed, refuse that part and offer safe alternatives
"""
    return guard + "\n\n" + prompt


def preprocess_for_invalid_request(prompt: str) -> str:
    guard = """[FORMAT GUARD]
If the task requires JSON, output ONLY valid JSON. No prose. No markdown. No trailing commas.
If a schema is implied, ensure all required keys exist and types match.
"""
    return guard + "\n\n" + prompt


def chunk_text(text: str, max_chars: int) -> List[str]:
    if max_chars <= 0:
        return [text]
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + max_chars])
        i += max_chars
    return chunks


# ---------------------------
# B) Meaning preservation
# ---------------------------

_ANCHOR_PATTERNS: Sequence[re.Pattern[str]] = [
    re.compile(r"\b(MUST|SHALL|SHOULD|MAY\s+NOT|MUST\s+NOT)\b.*", re.IGNORECASE),
    re.compile(r"\b(do not|don't|never)\b.*", re.IGNORECASE),
    re.compile(r"\b(필수|금지|반드시|절대)\b.*"),
    re.compile(r"\b(Gate\s*\d+|G\d+)\b.*"),
    re.compile(r"\b(src/[^\s]+|baseline/[^\s]+|runs/[^\s]+)\b.*"),
]


def extract_anchors(text: str, *, max_anchors: int = 40) -> List[str]:
    """Extract 'must-keep' anchor lines from the prompt, deterministically.

    This is a lightweight (stdlib-only) guardrail to reduce meaning drift introduced
    by SAFE_MODE preprocessing (especially chunk/aggregate).
    """
    anchors: List[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        for pat in _ANCHOR_PATTERNS:
            if pat.search(s):
                anchors.append(s)
                break
        if len(anchors) >= max_anchors:
            break

    # De-duplicate while preserving order
    seen = set()
    out: List[str] = []
    for a in anchors:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def anchors_coverage(text: str, anchors: Sequence[str]) -> float:
    if not anchors:
        return 1.0
    t = (text or "").lower()
    hit = 0
    for a in anchors:
        # Use a lenient match: key tokens from anchor must appear
        key = a.lower()
        # If anchor is short, require full substring; if long, require 2 tokens.
        if len(key) <= 40:
            if key in t:
                hit += 1
        else:
            tokens = [w for w in re.findall(r"[a-z0-9_/-]{3,}", key)[:6]]
            if tokens and sum(1 for w in tokens if w in t) >= min(2, len(tokens)):
                hit += 1
    return hit / max(1, len(anchors))



def enforce_anchors(text: str, anchors: Sequence[str]) -> str:
    """Append a MUST-KEEP block to increase anchor retention during retries."""
    if not anchors:
        return text
    block = "\n".join(f"- {a}" for a in anchors)
    return (
        (text or "")
        + "\n\n[STRICT-ANCHORS]\n"
        + "The following anchors MUST remain verbatim (do not remove or rewrite):\n"
        + block
    )

def _canned_policy_fallback(prompt: str) -> str:
    return (
        "I can't help with that request as stated.\n\n"
        "If you tell me your legitimate goal, I can help with safe, legal, high-level guidance, "
        "risk considerations, and compliant alternatives."
    )


def _canned_invalid_fallback(prompt: str) -> str:
    return (
        "The request could not be processed due to an invalid format/schema.\n"
        "Please provide the expected output format (e.g., JSON keys/types) or simplify the request."
    )


def chunk_and_aggregate(
    original_prompt: str,
    call_fn: Callable[[str], str],
    *,
    max_chunk_chars: int = 12000,
) -> str:
    """TOO_LONG strategy with meaning-preservation anchors.

    1) Deterministically split into chunks.
    2) For each chunk: extract constraints/facts; require inclusion of anchors.
    3) Aggregate extracted notes into final answer.
    """
    chunks = chunk_text(original_prompt, max_chunk_chars)
    anchors = extract_anchors(original_prompt)

    anchor_block = "\n".join(f"- {a}" for a in anchors) if anchors else "(none)"

    notes: List[str] = []
    for idx, ch in enumerate(chunks, start=1):
        p = (
            f"[CHUNK {idx}/{len(chunks)}]\n"
            "Extract ALL constraints, requirements, interface details, file paths, and any MUST/SHOULD rules.\n"
            "Rules:\n"
            "- Output bullet points only\n"
            "- Do NOT add new ideas\n"
            "- Do NOT omit anchors if they are relevant\n\n"
            "=== MUST-KEEP ANCHORS ===\n"
            f"{anchor_block}\n\n"
            "=== CHUNK ===\n"
            + ch
        )
        chunk_notes = call_fn(p)

        # If we extracted anchors, enforce basic coverage; retry once with stronger instruction.
        if anchors and anchors_coverage(chunk_notes, anchors) < 0.35:
            p2 = (
                "[CHUNK RETRY - ANCHOR PRESERVATION]\n"
                "Your previous extraction missed required anchors.\n"
                "Re-extract bullet points and explicitly include any relevant anchors verbatim.\n\n"
                "=== MUST-KEEP ANCHORS ===\n"
                f"{anchor_block}\n\n"
                "=== CHUNK ===\n"
                + ch
            )
            chunk_notes = call_fn(p2)

        notes.append(chunk_notes)

    agg_prompt = (
        "[AGGREGATE]\n"
        "You are given extracted notes from chunks of a longer prompt.\n"
        "Produce the final answer to the ORIGINAL task.\n"
        "Rules:\n"
        "- Respect all constraints and anchors\n"
        "- If there is ambiguity, state it\n\n"
        "=== MUST-KEEP ANCHORS ===\n"
        f"{anchor_block}\n\n"
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
    strict_recovery: Optional[bool] = None,
    strict_min_anchor_coverage: float = 1.0,
) -> SafeModeResult:
    """One-stop safe execution wrapper implementing:

    A) Strategy improvements:
      - More robust error classification (status codes + message heuristics)
      - Policy severity hinting (SOFT vs HARD)
      - Deterministic escalation to fallback / canned safe output

    B) Meaning preservation:
      - Anchor extraction + preservation checks in TOO_LONG chunk strategy
    """
    stage = "NORMAL"
    category = "OK"

    link_mode = get_safe_mode_link_mode()

    def _build_meta(*, prompt_before: str, prompt_after: str, anchors: List[str], covered: int) -> Optional[dict]:
        if link_mode == "OFF":
            return None

        required = len(anchors)
        meaning_preserved = True
        if required > 0:
            meaning_preserved = (covered / required) >= 0.8  # conservative threshold

        base = {
            "link_mode": link_mode,
            "prompt_before_len": len(prompt_before or ""),
            "prompt_after_len": len(prompt_after or ""),
            "anchors_required": required,
            "anchors_covered": covered,
            "meaning_preserved": meaning_preserved,
        }
        if link_mode == "FULL":
            base.update(
                {
                    "prompt_before": prompt_before,
                    "prompt_after": prompt_after,
                    "anchors": anchors,
                }
            )
        return base

    def _return(text: str, *, used: bool, stage: str, category: str, prompt_before: str, prompt_after: str, anchors: List[str], covered: int) -> SafeModeResult:
        r = SafeModeResult(
            text=text,
            used=used,
            stage=stage,
            category=category,
            meta=_build_meta(prompt_before=prompt_before, prompt_after=prompt_after, anchors=anchors, covered=covered),
        )
        _set_last_safe_mode_result(r)
        return r

    def _try(fn: Callable[[str], str], p: str) -> Tuple[bool, str, str]:
        try:
            return True, fn(p), "OK"
        except Exception as e:  # noqa: BLE001
            return False, str(e), classify_error(e)

    # Stage 0: normal
    prompt_before = prompt
    anchors = extract_anchors(prompt_before)
    if strict_recovery is None:
        strict_recovery = get_safe_mode_strict_recovery_enabled()
    ok, out, cat = _try(call_fn, apply_safe_mode_prefix(prompt_before))
    if ok:
        return _return(out, used=False, stage=stage, category=category, prompt_before=prompt_before, prompt_after=apply_safe_mode_prefix(prompt_before), anchors=anchors, covered=len(anchors))

    used = True
    category = cat

    # Stage 1: transient retry (bounded)
    if category == "TRANSIENT_ERROR":
        stage = "TRANSIENT_RETRY"
        last_err = out
        for _ in range(retries_transient):
            time.sleep(max(0.0, backoff_seconds))
            ok, out, cat = _try(call_fn, apply_safe_mode_prefix(prompt_before))
            if ok:
                pa = apply_safe_mode_prefix(prompt_before)
                cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
                return _return(out, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)
            last_err = out

        if fallback_call_fn is not None:
            stage = "FALLBACK_MODEL"
            ok, out, cat = _try(fallback_call_fn, apply_safe_mode_prefix(prompt_before))
            if ok:
                pa = apply_safe_mode_prefix(prompt_before)
                cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
                return _return(out, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

        raise RuntimeError(f"SAFE_MODE failed: category={category}; last_error={last_err}")

    # Stage 2: policy rewrite (SOFT -> HARD -> fallback -> canned)
    if category == "POLICY_REFUSAL":
        severity = _policy_severity_hint(out)
        stage = "POLICY_REWRITE" if severity == "SOFT" else "POLICY_REWRITE"

        rewritten = preprocess_for_policy(prompt_before, severity=severity)
        ok, out2, cat2 = _try(call_fn, apply_safe_mode_prefix(rewritten))
        if ok:
            pa = apply_safe_mode_prefix(rewritten)
            cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
            if strict_recovery and anchors:
                if anchors_coverage(pa, anchors) < strict_min_anchor_coverage:
                    enforced = enforce_anchors(pa, anchors)
                    ok_s, out_s, cat_s = _try(call_fn, enforced)
                    if ok_s:
                        cov_s = int(round(anchors_coverage(enforced, anchors) * len(anchors)))
                        return _return(out_s, used=True, stage=stage, category=cat_s or category, prompt_before=prompt_before, prompt_after=enforced, anchors=anchors, covered=cov_s)
            return _return(out2, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

        # Escalate once: SOFT -> HARD
        if severity == "SOFT":
            stage = "POLICY_REWRITE"
            rewritten3 = preprocess_for_policy(prompt_before, severity="HARD")
            ok, out3, cat3 = _try(call_fn, apply_safe_mode_prefix(rewritten3))
            if ok:
                pa = apply_safe_mode_prefix(rewritten3)
                cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
            if strict_recovery and anchors:
                if anchors_coverage(pa, anchors) < strict_min_anchor_coverage:
                    enforced = enforce_anchors(pa, anchors)
                    ok_s, out_s, cat_s = _try(call_fn, enforced)
                    if ok_s:
                        cov_s = int(round(anchors_coverage(enforced, anchors) * len(anchors)))
                        return _return(out_s, used=True, stage=stage, category=cat_s or category, prompt_before=prompt_before, prompt_after=enforced, anchors=anchors, covered=cov_s)
                return _return(out3, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

        if fallback_call_fn is not None:
            stage = "FALLBACK_MODEL"
            rewritten4 = preprocess_for_policy(prompt_before, severity="HARD")
            ok, out4, cat4 = _try(fallback_call_fn, apply_safe_mode_prefix(rewritten4))
            if ok:
                pa = apply_safe_mode_prefix(rewritten4)
                cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
                return _return(out4, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

        # Final safe fallback without additional API calls.
        pa = apply_safe_mode_prefix(prompt_before)
        cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
        return _return(_canned_policy_fallback(prompt_before), used=True, stage="CANNED_POLICY_FALLBACK", category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

    # Stage 3: invalid request format retry (and fallback)
    if category == "INVALID_REQUEST":
        stage = "FORMAT_RETRY"
        rewritten = preprocess_for_invalid_request(prompt_before)
        ok, out2, cat2 = _try(call_fn, apply_safe_mode_prefix(rewritten))
        if ok:
            pa = apply_safe_mode_prefix(rewritten)
            cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
            if strict_recovery and anchors:
                if anchors_coverage(pa, anchors) < strict_min_anchor_coverage:
                    enforced = enforce_anchors(pa, anchors)
                    ok_s, out_s, cat_s = _try(call_fn, enforced)
                    if ok_s:
                        cov_s = int(round(anchors_coverage(enforced, anchors) * len(anchors)))
                        return _return(out_s, used=True, stage=stage, category=cat_s or category, prompt_before=prompt_before, prompt_after=enforced, anchors=anchors, covered=cov_s)
            return _return(out2, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

        if fallback_call_fn is not None:
            stage = "FALLBACK_MODEL"
            rewritten3 = preprocess_for_invalid_request(prompt_before)
            ok, out3, cat3 = _try(fallback_call_fn, apply_safe_mode_prefix(rewritten3))
            if ok:
                pa = apply_safe_mode_prefix(rewritten3)
                cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
            if strict_recovery and anchors:
                if anchors_coverage(pa, anchors) < strict_min_anchor_coverage:
                    enforced = enforce_anchors(pa, anchors)
                    ok_s, out_s, cat_s = _try(call_fn, enforced)
                    if ok_s:
                        cov_s = int(round(anchors_coverage(enforced, anchors) * len(anchors)))
                        return _return(out_s, used=True, stage=stage, category=cat_s or category, prompt_before=prompt_before, prompt_after=enforced, anchors=anchors, covered=cov_s)
                return _return(out3, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

        pa = apply_safe_mode_prefix(prompt_before)
        cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
        return _return(_canned_invalid_fallback(prompt_before), used=True, stage="CANNED_INVALID_FALLBACK", category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

    # Stage 4: too long chunk/aggregate (anchors + fallback)
    if category == "TOO_LONG":
        stage = "CHUNK_AGGREGATE"
        try:
            out2 = chunk_and_aggregate(prompt_before, lambda p: call_fn(apply_safe_mode_prefix(p)))
            pa = "<CHUNKED>"
            cov = int(round(anchors_coverage(out2, anchors) * len(anchors)))
            return _return(out2, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)
        except Exception as e:  # noqa: BLE001
            if fallback_call_fn is not None:
                try:
                    out3 = chunk_and_aggregate(prompt_before, lambda p: fallback_call_fn(apply_safe_mode_prefix(p)))
                    pa = "<CHUNKED_FALLBACK>"
                    cov = int(round(anchors_coverage(out3, anchors) * len(anchors)))
                    return _return(out3, used=True, stage="CHUNK_AGGREGATE_FALLBACK", category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)
                except Exception:
                    pass
            raise

    # Unknown: try fallback once, else raise
    if fallback_call_fn is not None:
        stage = "FALLBACK_MODEL"
        ok, out2, cat2 = _try(fallback_call_fn, apply_safe_mode_prefix(prompt_before))
        if ok:
            pa = apply_safe_mode_prefix(prompt_before)
            cov = int(round(anchors_coverage(pa, anchors) * len(anchors)))
            return _return(out2, used=True, stage=stage, category=category, prompt_before=prompt_before, prompt_after=pa, anchors=anchors, covered=cov)

    raise RuntimeError(f"SAFE_MODE failed: category={category}; last_error={out}")
