"""
context_key_schema.py

Contract-level definition of the Nexa Working Context key schema.

This module belongs to the contracts layer.
It defines constants, regex, allowed domains, and a validator function
for the canonical Working Context key format:

    <context-domain>.<resource-id>.<field>

This module must not import from the runtime layer.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Canonical key format
# ---------------------------------------------------------------------------

# regex fragment for a single identifier segment (resource-id or field)
_IDENT = r"[a-z0-9_]+"

# Full canonical key regex
CONTEXT_KEY_PATTERN = re.compile(
    r"^(input|prompt|provider|plugin|system|output)\." + _IDENT + r"\." + _IDENT + r"$"
)

# Allowed top-level domains
ALLOWED_DOMAINS: frozenset[str] = frozenset(
    {"input", "prompt", "provider", "plugin", "system", "output"}
)

# Domains that plugins are NOT permitted to write into
PLUGIN_FORBIDDEN_WRITE_DOMAINS: frozenset[str] = frozenset(
    {"input", "prompt", "provider", "system", "output"}
)

# Canonical examples referenced in the spec
CANONICAL_EXAMPLES: tuple[str, ...] = (
    "input.text.value",
    "prompt.main.rendered",
    "provider.openai.output",
    "plugin.search.result",
    "system.trace.status",
    "output.summary.value",
)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def is_valid_context_key(key: str) -> bool:
    """Return True if key conforms to the canonical Working Context key schema."""
    return bool(CONTEXT_KEY_PATTERN.match(key))


def validate_context_key(key: str) -> None:
    """Raise ValueError if key does not conform to the canonical schema."""
    if not is_valid_context_key(key):
        raise ValueError(
            f"Invalid Working Context key: {key!r}. "
            f"Expected format: <domain>.<resource_id>.<field> "
            f"where domain is one of {sorted(ALLOWED_DOMAINS)}."
        )


def is_plugin_write_allowed(key: str) -> bool:
    """Return True if a plugin is permitted to write to this key.

    Plugins may only write under plugin.<plugin_id>.<field>.
    Writing to input.*, prompt.*, provider.*, system.*, or output.* is forbidden.
    """
    if not is_valid_context_key(key):
        return False
    domain = key.split(".")[0]
    return domain == "plugin"
