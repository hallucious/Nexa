
from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.platform.prompt_loader import load_prompt_spec
from src.platform.prompt_spec import PromptSpec


class PromptRegistry:
    """
    Prompt registry that loads PromptSpec files from:

        registry/prompts/{prompt_id}/vX.md
    """

    def __init__(self, root: str = "registry/prompts"):
        self.root = Path(root)

    def get(self, prompt_id: str, version: Optional[str] = None) -> PromptSpec:
        prompt_dir = self.root / prompt_id

        if not prompt_dir.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_id}")

        if version is None:
            version = self._latest_version(prompt_dir)

        path = prompt_dir / f"{version}.md"

        if not path.exists():
            raise FileNotFoundError(f"Prompt version not found: {prompt_id}:{version}")

        return load_prompt_spec(path)

    def _latest_version(self, prompt_dir: Path) -> str:
        versions = []

        for p in prompt_dir.glob("v*.md"):
            versions.append(p.stem)

        if not versions:
            raise RuntimeError(f"No prompt versions found in {prompt_dir}")

        versions.sort(key=lambda v: int(v.lstrip("v")))
        return versions[-1]
