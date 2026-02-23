from __future__ import annotations

from pathlib import Path

import pytest

from src.platform.prompt_loader import load_prompt_spec, PromptLoaderError
from src.platform.prompt_spec import PromptSpec


def test_prompt_loader_infers_id_version_and_renders(tmp_path: Path):
    # Arrange: create prompts/g1_design/v1.md
    prompts_dir = tmp_path / "prompts" / "g1_design"
    prompts_dir.mkdir(parents=True)
    p = prompts_dir / "v1.md"
    p.write_text("Hello {name}!\n", encoding="utf-8")

    # Act
    spec = load_prompt_spec(p, inputs_schema={"name": str})

    # Assert
    assert isinstance(spec, PromptSpec)
    assert spec.id == "g1_design/v1"
    assert spec.version == "v1"
    assert spec.render({"name": "Bob"}).strip() == "Hello Bob!"


def test_prompt_loader_requires_schema_without_header(tmp_path: Path):
    p = tmp_path / "prompts" / "g2_continuity" / "v1.md"
    p.parent.mkdir(parents=True)
    p.write_text("X={x}", encoding="utf-8")

    with pytest.raises(PromptLoaderError):
        load_prompt_spec(p)


def test_prompt_loader_header_overrides_schema(tmp_path: Path):
    p = tmp_path / "prompts" / "g3_fact_audit" / "v9.md"
    p.parent.mkdir(parents=True)

    header = '<!--PROMPT_SPEC: {"id":"g3_fact_audit/v9","version":"v9","inputs_schema":{"n":"int"}}-->'
    p.write_text(header + "\n" + "N={n}\n", encoding="utf-8")

    spec = load_prompt_spec(p)  # schema from header
    assert spec.id == "g3_fact_audit/v9"
    assert spec.version == "v9"
    assert spec.render({"n": 7}).strip() == "N=7"
