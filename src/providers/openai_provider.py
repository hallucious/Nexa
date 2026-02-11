from __future__ import annotations

import os
from typing import Optional

from src.providers.safe_mode import run_safe_mode


class OpenAIProvider:
    """OpenAI provider wrapper with SAFE_MODE stages.

    NOTE: Insert your real OpenAI API call inside `_call()`.
    This file intentionally keeps the external interface stable: `generate(prompt)->str`.
    """

    def __init__(self, *, model: str = "gpt-4.1", fallback_model: Optional[str] = None):
        self.model = model
        self.fallback_model = fallback_model or os.environ.get("OPENAI_FALLBACK_MODEL")

    def _call(self, prompt: str, *, model: Optional[str] = None) -> str:
        # TODO: Replace with real OpenAI API call.
        # Example pseudocode:
        #   client = OpenAI()
        #   resp = client.responses.create(model=model or self.model, input=prompt)
        #   return resp.output_text
        return "<openai-response>"

    def generate(self, prompt: str) -> str:
        def call_fn(p: str) -> str:
            return self._call(p, model=self.model)

        fallback_fn = None
        if self.fallback_model:
            def fb(p: str) -> str:
                return self._call(p, model=self.fallback_model)
            fallback_fn = fb

        res = run_safe_mode(prompt, call_fn, fallback_call_fn=fallback_fn)
        return res.text
