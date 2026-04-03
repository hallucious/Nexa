"""
context_key_schema.py

Contract-level definition of the Nexa Working Context key schema.

This module belongs to the contracts layer.
It defines constants, regex, allowed domains, and validator helpers
for the canonical Working Context key family:

    input.<field>
    output.<field>
    <context-domain>.<resource-id>.<field>

where the three-segment form is used for prompt/provider/plugin/system.

This module must not import from the runtime layer.
"""
from __future__ import annotations

import re
from typing import FrozenSet

_IDENT = r"[a-z0-9_]+"

TWO_SEGMENT_DOMAINS: FrozenSet[str] = frozenset({"input", "output"})
THREE_SEGMENT_DOMAINS: FrozenSet[str] = frozenset({"prompt", "provider", "plugin", "system"})
ALLOWED_DOMAINS: FrozenSet[str] = frozenset(TWO_SEGMENT_DOMAINS | THREE_SEGMENT_DOMAINS)

CONTEXT_KEY_PATTERN = re.compile(
    rf"^(?:"
    rf"(?:input|output)\.{_IDENT}"
    rf"|"
    rf"(?:prompt|provider|plugin|system)\.{_IDENT}\.{_IDENT}"
    rf")$"
)

PLUGIN_FORBIDDEN_WRITE_DOMAINS: FrozenSet[str] = frozenset(ALLOWED_DOMAINS - {"plugin"})

RESOURCE_ALLOWED_WRITE_DOMAINS: dict[str, FrozenSet[str]] = {
    "prompt": frozenset({"prompt"}),
    "provider": frozenset({"provider"}),
    "plugin": frozenset({"plugin"}),
    "runtime": frozenset({"system", "output"}),
}

CANONICAL_EXAMPLES: tuple[str, ...] = (
    "input.text",
    "prompt.main.rendered",
    "provider.openai.output",
    "plugin.search.result",
    "system.trace.status",
    "output.value",
)


def is_valid_context_key(key: str) -> bool:
    return bool(CONTEXT_KEY_PATTERN.match(key))


def validate_context_key(key: str) -> None:
    if not is_valid_context_key(key):
        raise ValueError(
            f"Invalid Working Context key: {key!r}. "
            f"Expected canonical forms: input.<field>, output.<field>, or "
            f"<domain>.<resource_id>.<field> for domains in {sorted(THREE_SEGMENT_DOMAINS)}."
        )


def get_context_key_domain(key: str) -> str | None:
    if not is_valid_context_key(key):
        return None
    return key.split(".", 1)[0]


def is_plugin_write_allowed(key: str) -> bool:
    return is_resource_write_allowed("plugin", key)


def is_resource_write_allowed(resource_type: str, key: str) -> bool:
    if not is_valid_context_key(key):
        return False
    allowed_domains = RESOURCE_ALLOWED_WRITE_DOMAINS.get(resource_type)
    if allowed_domains is None:
        return False
    domain = key.split('.', 1)[0]
    return domain in allowed_domains


def validate_resource_write_key(resource_type: str, key: str) -> None:
    if not is_resource_write_allowed(resource_type, key):
        allowed_domains = RESOURCE_ALLOWED_WRITE_DOMAINS.get(resource_type)
        if allowed_domains is None:
            raise ValueError(f"Unknown resource_type for write-boundary validation: {resource_type!r}")
        raise ValueError(
            f"Invalid write key for {resource_type!r}: {key!r}. "
            f"Allowed domains: {sorted(allowed_domains)}."
        )
