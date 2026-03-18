import re
from pathlib import Path

from src.prompts.registry import PROMPT_REGISTRY

_PLACEHOLDER = re.compile(r"{{\s*(\w+)\s*}}")


def test_prompt_registry_contract_files_and_required_placeholders_exist():
    base_dir = Path(__file__).resolve().parents[1] / "src" / "prompts"

    for prompt_id, spec in PROMPT_REGISTRY.items():
        file_name = spec["file"]
        required = spec.get("required", [])

        path = base_dir / file_name
        assert path.exists(), f"{prompt_id} -> missing file: {path}"

        template = path.read_text(encoding="utf-8")
        placeholders = set(_PLACEHOLDER.findall(template))

        # required placeholders must be present in template
        for r in required:
            assert r in placeholders, f"{prompt_id} -> required '{r}' not in template placeholders {sorted(placeholders)}"
