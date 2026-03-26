from legacy_prompts.prompt_spec import PromptSpec
from legacy_prompts.prompt_registry import PromptRegistry


def _schema_str(var: str) -> dict:
    return {
        "type": "object",
        "properties": {var: {"type": "string"}},
        "required": [var],
        "additionalProperties": False,
    }


def test_prompt_registry_basic():
    spec = PromptSpec(
        prompt_id="p1",
        version="1.0.0",
        template="Hello {{name}}",
        variables_schema=_schema_str("name"),
        description="test",
    )
    registry = PromptRegistry()
    registry.register(spec)

    loaded = registry.get("p1")
    rendered = loaded.render(variables={"name": "World"})
    assert rendered == "Hello World"


def test_prompt_hash_deterministic_and_prefixed():
    spec = PromptSpec(
        prompt_id="p2",
        version="1.0.0",
        template="Hi {{x}}",
        variables_schema=_schema_str("x"),
        description="test",
    )
    h1 = spec.prompt_hash
    h2 = spec.prompt_hash
    assert h1 == h2
    assert h1.startswith("sha256:")
