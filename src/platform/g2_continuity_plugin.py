from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

from src.pipeline.runner import GateContext

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "g2_continuity",
    "type": "gate_plugin",
    "entrypoint": "src.platform.g2_continuity_plugin:resolve",
    "inject": {"target": "providers", "key": "gpt"},
    "capabilities": [],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}


@dataclass
class G2ContinuityAI:
    """Result of the optional semantic continuity check.

    - used=False means no provider was available (noop).
    - verdict is one of: SAME|DRIFT|VIOLATION|UNKNOWN
    """

    used: bool
    error: Optional[str]
    verdict: str
    rationale: str
    text: str
    raw: Dict[str, Any]
    prompt: str


class TextProvider(Protocol):
    def generate_text(
        self, *, prompt: str, temperature: float, max_output_tokens: int
    ) -> Tuple[str, Dict[str, Any], Optional[str]]: ...


class G2ContinuityPlugin(Protocol):
    def semantic_check(self, pic_context: str, current_request: str) -> G2ContinuityAI: ...


class GPTContinuityPlugin:
    def __init__(self, provider: TextProvider):
        self._provider = provider

    def semantic_check(self, pic_context: str, current_request: str) -> G2ContinuityAI:
        prompt = (
            'You are Gate2 (Continuity). Compare the previous "PIC" text and the current text.\n'
            'Return ONLY valid JSON: {"verdict":"SAME|DRIFT|VIOLATION|UNKNOWN","rationale":"..."}\n\n'
            f"PIC:\n{(pic_context or '').strip()[:6000]}\n\n"
            f"CURRENT:\n{(current_request or '').strip()[:6000]}"
        )

        try:
            text, raw, err = self._provider.generate_text(
                prompt=prompt, temperature=0.0, max_output_tokens=512
            )
        except Exception as e:
            return G2ContinuityAI(
                used=True,
                error=f"provider error: {type(e).__name__}: {e}",
                verdict="UNKNOWN",
                rationale="",
                text="",
                raw={},
                prompt=prompt,
            )

        verdict = "UNKNOWN"
        rationale = ""

        # Best-effort JSON parse; do not raise.
        try:
            obj = json.loads((text or "").strip())
            if isinstance(obj, dict):
                v = obj.get("verdict")
                r = obj.get("rationale")
                if isinstance(v, str) and v:
                    verdict = v
                if isinstance(r, str):
                    rationale = r
        except Exception:
            pass

        return G2ContinuityAI(
            used=True,
            error=err,
            verdict=verdict,
            rationale=rationale,
            text=text or "",
            raw=raw or {},
            prompt=prompt,
        )


class NoopContinuityPlugin:
    def semantic_check(self, pic_context: str, current_request: str) -> G2ContinuityAI:
        return G2ContinuityAI(
            used=False,
            error=None,
            verdict="UNKNOWN",
            rationale="",
            text="",
            raw={},
            prompt="",
        )


def resolve_g2_continuity_plugin(providers: Optional[Dict[str, Any]]) -> G2ContinuityPlugin:
    """Resolve G2 plugin.

    Contract:
    - If providers['gpt'] exists -> GPTContinuityPlugin
    - Else -> NoopContinuityPlugin
    """
    p = (providers or {}).get("gpt")
    if p is None:
        return NoopContinuityPlugin()
    return GPTContinuityPlugin(p)  # type: ignore[arg-type]

def resolve(ctx: "GateContext") -> "G2ContinuityPlugin":
    """Unified entrypoint: resolve(ctx) -> plugin.

    Preserves legacy behavior of resolve_g2_continuity_plugin(providers).
    """
    return resolve_g2_continuity_plugin(getattr(ctx, "providers", None))
