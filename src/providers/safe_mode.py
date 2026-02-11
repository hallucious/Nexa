from __future__ import annotations

import os
import re
from typing import List

# NOTE:
# SAFE_MODE is NOT refusal evasion. It narrows scope to allowed content and safe alternatives.

SAFE_PREFIX = """[SAFE MODE ENABLED]
You must comply with platform safety policies.
If the original request asks for disallowed actions, do NOT provide disallowed content.
Instead, provide:
- High-level principles
- Risks and warnings
- Safe alternatives
Always stay within allowed content.
"""


def safe_mode_enabled() -> bool:
    return os.environ.get("HAI_SAFE_MODE") == "1"


def safe_mode_reason() -> str:
    return (os.environ.get("HAI_SAFE_MODE_REASON") or "").strip()


def safe_mode_gate() -> str:
    return (os.environ.get("HAI_SAFE_MODE_GATE") or "").strip()


def normalize_text(text: str) -> str:
    """Meaning-preserving normalization (invariant preprocess)."""
    if text is None:
        return ""
    # Remove NUL and other control chars except \n, \t, \r
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Normalize CRLF -> LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def apply_safe_mode_text(text: str) -> str:
    """Prepend SAFE_PREFIX when SAFE_MODE is enabled."""
    text = normalize_text(text or "")
    if safe_mode_enabled():
        return SAFE_PREFIX + "\n\n" + text
    return text


def split_into_chunks(text: str, *, max_chars: int) -> List[str]:
    """Deterministic chunking (lossless) by character count."""
    text = normalize_text(text or "")
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
