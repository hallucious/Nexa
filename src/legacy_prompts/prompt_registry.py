from typing import Dict
from .prompt_spec import PromptSpec

class PromptRegistry:
    def __init__(self):
        self._store: Dict[str, PromptSpec] = {}

    def register(self, spec: PromptSpec) -> None:
        self._store[spec.prompt_id] = spec

    def get(self, prompt_id: str) -> PromptSpec:
        if prompt_id not in self._store:
            raise KeyError(f"Prompt '{prompt_id}' not found")
        return self._store[prompt_id]
