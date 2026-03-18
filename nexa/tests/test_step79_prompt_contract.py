from __future__ import annotations

import pytest

from src.prompts.prompt_spec import PromptSpec


def test_prompt_spec_hash_is_deterministic_and_prefixed():
    spec = PromptSpec(
        prompt_id="p1",
        version="1.0.0",
        template="Hello {{name}}",
        variables_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False},
        description="test",
    )
    h1 = spec.prompt_hash
    h2 = spec.prompt_hash
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_prompt_spec_render_validates_variables_missing():
    spec = PromptSpec(
        prompt_id="p2",
        version="1.0.0",
        template="Hello {{name}}",
        variables_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False},
        description="test",
    )
    with pytest.raises(Exception):
        spec.render(variables={})


def test_prompt_spec_render_validates_variables_extra():
    spec = PromptSpec(
        prompt_id="p3",
        version="1.0.0",
        template="Hello {{name}}",
        variables_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False},
        description="test",
    )
    with pytest.raises(Exception):
        spec.render(variables={"name": "x", "extra": 1})


def test_prompt_spec_render_success():
    spec = PromptSpec(
        prompt_id="p4",
        version="1.0.0",
        template="Hello {{name}}",
        variables_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False},
        description="test",
    )
    out = spec.render(variables={"name": "World"})
    assert out == "Hello World"
