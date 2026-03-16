"""
tests/test_context_key_schema_contract.py

Contract tests for the Nexa Working Context key schema.

Spec: docs/specs/contracts/context_key_schema_contract.md
Version: 1.0.0

These tests lock the canonical key format, allowed domains, and plugin
write restrictions defined in the contract.
"""
from __future__ import annotations

import pytest

from src.contracts.context_key_schema import (
    ALLOWED_DOMAINS,
    CANONICAL_EXAMPLES,
    CONTEXT_KEY_PATTERN,
    PLUGIN_FORBIDDEN_WRITE_DOMAINS,
    is_plugin_write_allowed,
    is_valid_context_key,
    validate_context_key,
)


# ---------------------------------------------------------------------------
# 1. Canonical examples must be valid
# ---------------------------------------------------------------------------

@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.text.value",
    "prompt.main.rendered",
    "provider.openai.output",
    "plugin.search.result",
    "system.trace.status",
    "output.summary.value",
])
def test_canonical_examples_are_valid(key):
    assert is_valid_context_key(key), f"canonical key must be valid: {key!r}"


@pytest.mark.contract
def test_canonical_examples_constant_is_complete():
    """The CANONICAL_EXAMPLES tuple must contain all six spec-defined examples."""
    required = {
        "input.text.value",
        "prompt.main.rendered",
        "provider.openai.output",
        "plugin.search.result",
        "system.trace.status",
        "output.summary.value",
    }
    assert required.issubset(set(CANONICAL_EXAMPLES)), (
        f"CANONICAL_EXAMPLES is missing spec-required keys: {required - set(CANONICAL_EXAMPLES)}"
    )


# ---------------------------------------------------------------------------
# 2. Valid keys for every allowed domain
# ---------------------------------------------------------------------------

@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.story.raw",
    "input.question.text",
    "prompt.expand.rendered",
    "prompt.summary.template",
    "provider.anthropic.output",
    "provider.gpt4.response",
    "plugin.rank.score",
    "plugin.format_output.result",
    "system.runtime.version",
    "system.trace.node_id",
    "output.final.value",
    "output.script.text",
])
def test_valid_keys_pass(key):
    assert is_valid_context_key(key), f"expected valid: {key!r}"


# ---------------------------------------------------------------------------
# 3. Invalid domains must be rejected
# ---------------------------------------------------------------------------

@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "inputs.text.value",       # plural
    "metadata.run.id",         # not in allowed domains
    "context.main.value",      # not in allowed domains
    "state.node.output",       # not in allowed domains
    "debug.trace.flag",        # not in allowed domains
    "runtime.info.version",    # not in allowed domains
])
def test_invalid_domains_fail(key):
    assert not is_valid_context_key(key), f"expected invalid (bad domain): {key!r}"


# ---------------------------------------------------------------------------
# 4. Uppercase / hyphenated / special characters in identifiers must fail
# ---------------------------------------------------------------------------

@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.Text.value",           # uppercase in resource-id
    "prompt.main.Rendered",       # uppercase in field
    "provider.OpenAI.output",     # uppercase in resource-id
    "plugin.search-rank.result",  # hyphen in resource-id
    "input.text-raw.value",       # hyphen in resource-id
    "output.summary.final-text",  # hyphen in field
    "input.text value.raw",       # space in resource-id
    "provider.gpt 4.output",      # space in resource-id
])
def test_uppercase_and_hyphen_keys_fail(key):
    assert not is_valid_context_key(key), f"expected invalid (case/hyphen): {key!r}"


# ---------------------------------------------------------------------------
# 5. Malformed keys must fail (wrong number of parts)
# ---------------------------------------------------------------------------

@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "",                         # empty
    "input",                    # one part only
    "input.text",               # two parts only (missing field)
    "input.text.value.extra",   # four parts (too many)
    ".text.value",              # empty domain
    "input..value",             # empty resource-id
    "input.text.",              # empty field
    "input.text.value.",        # trailing dot
    ".input.text.value",        # leading dot
])
def test_malformed_keys_fail(key):
    assert not is_valid_context_key(key), f"expected invalid (malformed): {key!r}"


# ---------------------------------------------------------------------------
# 6. validate_context_key raises ValueError for invalid keys
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_validate_context_key_raises_for_invalid():
    with pytest.raises(ValueError):
        validate_context_key("bad.key")

    with pytest.raises(ValueError):
        validate_context_key("metadata.run.id")

    with pytest.raises(ValueError):
        validate_context_key("input.Text.value")


@pytest.mark.contract
def test_validate_context_key_does_not_raise_for_valid():
    validate_context_key("input.text.value")   # must not raise
    validate_context_key("plugin.rank.score")  # must not raise
    validate_context_key("output.final.value") # must not raise


# ---------------------------------------------------------------------------
# 7. Plugin write restriction
# ---------------------------------------------------------------------------

@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "plugin.rank.score",
    "plugin.format_output.result",
    "plugin.search.result",
    "plugin.validator.passed",
])
def test_plugin_write_allowed_for_plugin_domain(key):
    assert is_plugin_write_allowed(key), f"plugin write must be allowed for: {key!r}"


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.text.value",
    "prompt.main.rendered",
    "provider.openai.output",
    "system.trace.status",
    "output.summary.value",
])
def test_plugin_write_forbidden_for_other_domains(key):
    assert not is_plugin_write_allowed(key), (
        f"plugin write must be FORBIDDEN for: {key!r}"
    )


@pytest.mark.contract
def test_plugin_write_forbidden_domains_constant():
    """PLUGIN_FORBIDDEN_WRITE_DOMAINS must cover all non-plugin allowed domains."""
    non_plugin = ALLOWED_DOMAINS - {"plugin"}
    assert non_plugin == PLUGIN_FORBIDDEN_WRITE_DOMAINS, (
        "PLUGIN_FORBIDDEN_WRITE_DOMAINS must exactly match all non-plugin allowed domains"
    )


# ---------------------------------------------------------------------------
# 8. ALLOWED_DOMAINS constant is exactly the spec-defined set
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_allowed_domains_are_exactly_spec_defined():
    expected = frozenset({"input", "prompt", "provider", "plugin", "system", "output"})
    assert ALLOWED_DOMAINS == expected, (
        f"ALLOWED_DOMAINS mismatch. got: {ALLOWED_DOMAINS}, expected: {expected}"
    )


# ---------------------------------------------------------------------------
# 9. CONTEXT_KEY_PATTERN is usable as a compiled regex
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_context_key_pattern_is_compiled_regex():
    assert hasattr(CONTEXT_KEY_PATTERN, "match"), "CONTEXT_KEY_PATTERN must be a compiled regex"
    assert CONTEXT_KEY_PATTERN.match("input.text.value")
    assert not CONTEXT_KEY_PATTERN.match("bad.key")
