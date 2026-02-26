"""G1 Design plugin.

Goal: isolate provider-facing logic (prompt rendering + model call + JSON parse)
from the gate adapter so that G1 stays stable and testable.

Behavior: preserved. If provider is missing or tests are running, this plugin
returns empty AI output and the caller keeps the skeleton design.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from src.pipeline.runner import GateContext
from typing import Protocol
from src.prompts.renderer import PromptRenderer

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "g1_design",
    "type": "gate_plugin",
    "entrypoint": "src.platform.g1_design_plugin:resolve",
    "inject": {"target": "providers", "key": "gpt"},
    "capabilities": [],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}



@dataclass(frozen=True)
class G1DesignAI:
    used: bool
    error: str
    text: str
    prompt_ident: Optional[Any]


def run_g1_design_plugin(*, request_text: str, provider: Optional[Any], is_pytest: bool) -> G1DesignAI:
    """Run the G1 design generation using the injected provider.

    Provider contract:
      - provider.generate_text(prompt=..., temperature=..., max_output_tokens=...)
        -> (text: str, raw: Any, err: Optional[Exception])
    """

    if is_pytest or provider is None:
        return G1DesignAI(used=False, error="", text="", prompt_ident=None)

    gpt_used = False
    gpt_error = ""
    gpt_text = ""
    prompt_ident = None

    try:
        prompt, prompt_ident = PromptRenderer.render_prompt(
            "g1_design@v1",
            request_text=request_text.strip()[:8000],
        )
        gpt_used = True

        gpt_text, _raw, err = provider.generate_text(
            prompt=prompt,
            temperature=0.0,
            max_output_tokens=2048,
        )
        if err is not None:
            gpt_error = f"{type(err).__name__}: {err}"
    except Exception as e:
        gpt_error = f"{type(e).__name__}: {e}"

    return G1DesignAI(used=gpt_used, error=gpt_error, text=gpt_text, prompt_ident=prompt_ident)


def parse_design_json(text: str) -> Optional[dict]:
    """Parse JSON design output. Returns None if invalid."""

    if not text or not text.strip():
        return None
    try:
        candidate = json.loads(text)
    except Exception:
        return None
    return candidate if isinstance(candidate, dict) else None

class G1DesignRunner(Protocol):
    def run(self, request_text: str, *, is_pytest: bool) -> G1DesignAI:
        ...


@dataclass(frozen=True)
class _G1DesignRunnerImpl:
    provider: Optional[Any]

    def run(self, request_text: str, *, is_pytest: bool) -> G1DesignAI:
        return run_g1_design_plugin(request_text=request_text, provider=self.provider, is_pytest=is_pytest)


def resolve(ctx: "GateContext") -> G1DesignRunner:
    """Unified entrypoint: resolve(ctx) -> runner."""
    providers = getattr(ctx, "providers", None) or {}
    return _G1DesignRunnerImpl(provider=providers.get("gpt"))
