import os

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

def apply_safe_mode_text(text: str) -> str:
    """Prepend SAFE_PREFIX to a text field if SAFE_MODE is enabled."""
    if safe_mode_enabled():
        return SAFE_PREFIX + "\n\n" + (text or "")
    return text
