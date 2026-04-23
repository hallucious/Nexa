from __future__ import annotations

import pytest

from src.platform.prompt_spec import PromptSpec, PromptSpecError


def test_promptspec_render_success():
    spec = PromptSpec(
        id="g3_fact_audit/v1",
        version="v1",
        template="Hello {name}, your age is {age}.",
        inputs_schema={"name": str, "age": int},
    )
    out = spec.render({"name": "Alice", "age": 30})
    assert out == "Hello Alice, your age is 30."


def test_promptspec_missing_key_raises():
    spec = PromptSpec(
        id="g1_design/v1",
        version="v1",
        template="Hi {name}!",
        inputs_schema={"name": str},
    )
    with pytest.raises(PromptSpecError):
        spec.render({})


def test_promptspec_wrong_type_raises():
    spec = PromptSpec(
        id="g2_continuity/v1",
        version="v1",
        template="Count {n}",
        inputs_schema={"n": int},
    )
    with pytest.raises(PromptSpecError):
        spec.render({"n": "not-int"})


def test_promptspec_template_references_unknown_var_raises():
    spec = PromptSpec(
        id="g4_self_check/v1",
        version="v1",
        template="X={x} Y={y}",
        inputs_schema={"x": int},
    )
    with pytest.raises(PromptSpecError):
        spec.render({"x": 1})
