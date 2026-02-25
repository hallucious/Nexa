from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple


@dataclass
class G2ContinuityAI:
    used: bool
    error: Optional[str]
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
            f"PIC:\n{pic_context.strip()[:6000]}\n\n"
            f"CURRENT:\n{current_request.strip()[:6000]}"
        )

        try:
            text, raw, err = self._provider.generate_text(
                prompt=prompt, temperature=0.0, max_output_tokens=512
            )
        except Exception as e:
            return G2ContinuityAI(
                used=True,
                error=str(e),
                text="",
                raw={},
                prompt=prompt,
            )

        return G2ContinuityAI(
            used=True,
            error=err,
            text=text,
            raw=raw,
            prompt=prompt,
        )


class NoopContinuityPlugin:
    def semantic_check(self, pic_context: str, current_request: str) -> G2ContinuityAI:
        return G2ContinuityAI(
            used=False,
            error=None,
            text="",
            raw={},
            prompt="",
        )


def resolve_g2_continuity_plugin(providers: Optional[Dict[str, Any]]) -> G2ContinuityPlugin:
    p = (providers or {}).get("gpt")
    if p is None:
        return NoopContinuityPlugin()
    return GPTContinuityPlugin(p)  # type: ignore[arg-type]
