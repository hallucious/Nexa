from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.models.decision_models import Decision
from src.pipeline.runner import GateContext
from src.prompts.renderer import PromptRenderer
from src.policy.gate_policy import evaluate_g4


@dataclass
class G4SelfCheckPluginResult:
    decision: Decision
    output: Dict[str, Any]
    meta: Dict[str, Any]


class G4SelfCheckPlugin:
    """Pure execution unit for G4.

    - Does NOT write files.
    - Gate wrapper remains responsible for artifacts.
    """

    prompt_id: str = "g4_self_check@v1"

    def run(self, ctx: GateContext) -> G4SelfCheckPluginResult:
        is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))
        provider = (ctx.providers or {}).get("gpt")

        gpt_used = False
        gpt_error = ""
        gpt_text = ""
        prompt_ident = None

        if (not is_pytest) and provider is not None:
            try:
                prompt, prompt_ident = PromptRenderer.render_prompt(self.prompt_id)
                gpt_used = True
                gpt_text, _raw, err = provider.generate_text(
                    prompt=prompt, temperature=0.0, max_output_tokens=2048
                )
                if err is not None:
                    gpt_error = f"{type(err).__name__}: {err}"
            except Exception as e:
                gpt_error = f"{type(e).__name__}: {e}"

        # When GPT output is absent/invalid, policy still decides based on local checks.
        model_json: Optional[Dict[str, Any]] = None
        if gpt_text.strip():
            try:
                candidate = json.loads(gpt_text)
                if isinstance(candidate, dict):
                    model_json = candidate
            except Exception:
                model_json = None

        policy = evaluate_g4(model_json or {})

        output = {
            "policy": policy.to_dict(),
            "ai": {
                "engine": "gpt",
                "used": gpt_used,
                "error": gpt_error,
                "text": gpt_text,
            },
        }

        meta: Dict[str, Any] = {
            "gate": "G4",
            "decision": policy.decision.value,
            "reason_code": getattr(policy, "reason_code", None),
            "attempt": (ctx.meta.attempts or {}).get("G4", 1),
            "ai": {"engine": "gpt", "used": gpt_used, "error": gpt_error},
        }

        if prompt_ident is not None:
            meta["prompt"] = {
                "id": self.prompt_id,
                "name": prompt_ident.name,
                "version": prompt_ident.version,
                "sha256": prompt_ident.sha256_prefixed,
            }

        return G4SelfCheckPluginResult(decision=policy.decision, output=output, meta=meta)
