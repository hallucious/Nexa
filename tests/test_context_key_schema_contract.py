"""
tests/test_context_key_schema_contract.py

Contract tests for the Nexa Working Context key schema.

Spec: docs/specs/contracts/context_key_schema_contract.md
Version: 1.1.0

These tests lock the canonical key family, allowed domains, and write
restrictions defined in the contract.
"""
from __future__ import annotations

import pytest

from src.contracts.context_key_schema import (
    ALLOWED_DOMAINS,
    CANONICAL_EXAMPLES,
    CONTEXT_KEY_PATTERN,
    PLUGIN_FORBIDDEN_WRITE_DOMAINS,
    RESOURCE_ALLOWED_WRITE_DOMAINS,
    THREE_SEGMENT_DOMAINS,
    TWO_SEGMENT_DOMAINS,
    get_context_key_domain,
    is_plugin_write_allowed,
    is_resource_write_allowed,
    is_valid_context_key,
    validate_context_key,
    validate_resource_write_key,
)


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.text",
    "prompt.main.rendered",
    "provider.openai.output",
    "plugin.search.result",
    "system.trace.status",
    "output.value",
])
def test_canonical_examples_are_valid(key):
    assert is_valid_context_key(key)


@pytest.mark.contract
def test_canonical_examples_constant_is_complete():
    required = {
        "input.text",
        "prompt.main.rendered",
        "provider.openai.output",
        "plugin.search.result",
        "system.trace.status",
        "output.value",
    }
    assert required.issubset(set(CANONICAL_EXAMPLES))


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.story",
    "input.question",
    "prompt.expand.rendered",
    "prompt.summary.template",
    "provider.anthropic.output",
    "provider.gpt4.response",
    "plugin.rank.score",
    "plugin.format_output.result",
    "system.runtime.version",
    "system.trace.node_id",
    "output.final",
    "output.script",
])
def test_valid_keys_pass(key):
    assert is_valid_context_key(key)


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "inputs.text",
    "metadata.run.id",
    "context.main.value",
    "state.node.output",
    "debug.trace.flag",
    "runtime.info.version",
])
def test_invalid_domains_fail(key):
    assert not is_valid_context_key(key)


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.Text",
    "prompt.main.Rendered",
    "provider.OpenAI.output",
    "plugin.search-rank.result",
    "input.text-raw",
    "output.final-text",
    "input.text value",
    "provider.gpt 4.output",
])
def test_uppercase_and_hyphen_keys_fail(key):
    assert not is_valid_context_key(key)


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "",
    "input",
    "prompt.main",
    "input.text.value",
    "output.final.value",
    "provider.openai",
    "input.",
    ".text",
    "prompt..rendered",
    "provider.openai.output.extra",
])
def test_malformed_keys_fail(key):
    assert not is_valid_context_key(key)


@pytest.mark.contract
def test_validate_context_key_raises_for_invalid():
    with pytest.raises(ValueError):
        validate_context_key("bad.key")
    with pytest.raises(ValueError):
        validate_context_key("metadata.run.id")
    with pytest.raises(ValueError):
        validate_context_key("input.Text")


@pytest.mark.contract
def test_validate_context_key_does_not_raise_for_valid():
    validate_context_key("input.text")
    validate_context_key("plugin.rank.score")
    validate_context_key("output.final")


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "plugin.rank.score",
    "plugin.format_output.result",
    "plugin.search.result",
    "plugin.validator.passed",
])
def test_plugin_write_allowed_for_plugin_domain(key):
    assert is_plugin_write_allowed(key)


@pytest.mark.contract
@pytest.mark.parametrize("key", [
    "input.text",
    "prompt.main.rendered",
    "provider.openai.output",
    "system.trace.status",
    "output.value",
])
def test_plugin_write_forbidden_for_other_domains(key):
    assert not is_plugin_write_allowed(key)


@pytest.mark.contract
def test_plugin_write_forbidden_domains_constant():
    non_plugin = ALLOWED_DOMAINS - {"plugin"}
    assert non_plugin == PLUGIN_FORBIDDEN_WRITE_DOMAINS


@pytest.mark.contract
def test_allowed_domains_are_exactly_spec_defined():
    assert ALLOWED_DOMAINS == frozenset({"input", "prompt", "provider", "plugin", "system", "output"})


@pytest.mark.contract
def test_context_key_pattern_is_compiled_regex():
    assert hasattr(CONTEXT_KEY_PATTERN, "match")
    assert CONTEXT_KEY_PATTERN.match("input.text")
    assert CONTEXT_KEY_PATTERN.match("provider.openai.output")
    assert not CONTEXT_KEY_PATTERN.match("bad.key")


@pytest.mark.contract
def test_domain_shape_sets_are_exact():
    assert TWO_SEGMENT_DOMAINS == frozenset({"input", "output"})
    assert THREE_SEGMENT_DOMAINS == frozenset({"prompt", "provider", "plugin", "system"})


@pytest.mark.contract
@pytest.mark.parametrize(
    ("resource_type", "key"),
    [
        ("prompt", "prompt.main.rendered"),
        ("provider", "provider.openai.output"),
        ("plugin", "plugin.search.result"),
        ("runtime", "system.trace.status"),
        ("runtime", "output.value"),
    ],
)
def test_resource_write_boundary_allows_expected_domains(resource_type, key):
    assert is_resource_write_allowed(resource_type, key)


@pytest.mark.contract
@pytest.mark.parametrize(
    ("resource_type", "key"),
    [
        ("prompt", "output.value"),
        ("provider", "prompt.main.rendered"),
        ("plugin", "provider.openai.output"),
        ("plugin", "output.value"),
        ("runtime", "plugin.search.result"),
    ],
)
def test_resource_write_boundary_rejects_cross_domain_writes(resource_type, key):
    assert not is_resource_write_allowed(resource_type, key)


@pytest.mark.contract
def test_validate_resource_write_key_raises_for_invalid_boundary():
    with pytest.raises(ValueError):
        validate_resource_write_key("plugin", "output.value")
    with pytest.raises(ValueError):
        validate_resource_write_key("unknown", "output.value")


@pytest.mark.contract
def test_get_context_key_domain_returns_domain_for_valid_keys():
    assert get_context_key_domain("input.text") == "input"
    assert get_context_key_domain("provider.openai.output") == "provider"
    assert get_context_key_domain("output.value") == "output"
    assert get_context_key_domain("bad.key") is None


@pytest.mark.contract
def test_resource_allowed_write_domains_constant_is_exact():
    assert RESOURCE_ALLOWED_WRITE_DOMAINS == {
        "prompt": frozenset({"prompt"}),
        "provider": frozenset({"provider"}),
        "plugin": frozenset({"plugin"}),
        "runtime": frozenset({"system", "output"}),
    }
