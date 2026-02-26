from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, is_dataclass
from typing import Any, Dict, Optional, Tuple

from typing import Protocol
from src.models.decision_models import Decision
from src.pipeline.runner import GateContext
from src.prompts.renderer import PromptRenderer
from src.policy.gate_policy import evaluate_g4
from src.platform.plugin_contract import ReasonCode, normalize_meta
from src.platform.capability_negotiation import negotiate

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "g4_self_check",
    "type": "gate_plugin",
    "entrypoint": "src.platform.g4_self_check_plugin:resolve",
    "inject": {"target": "providers", "key": "gpt"},
    "capabilities": [],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}



def _policy_to_dict(policy: Any) -> Dict[str, Any]:
    """Best-effort serialization for PolicyDecision across versions.

    Avoids hard dependency on a specific helper like .to_dict().
    """

    to_dict = getattr(policy, "to_dict", None)
    if callable(to_dict):
        try:
            v = to_dict()
            if isinstance(v, dict):
                return v
        except Exception:
            pass

    if is_dataclass(policy):
        try:
            v = asdict(policy)
            if isinstance(v, dict):
                return v
        except Exception:
            pass

    d = getattr(policy, "__dict__", None)
    if isinstance(d, dict):
        return dict(d)

    try:
        v = dict(policy)  # type: ignore[arg-type]
        if isinstance(v, dict):
            return v
    except Exception:
        pass

    return {"value": str(policy)}


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

        # Compute local prereq/schema checks (aligned with src.policy.gate_policy.evaluate_g4 contract).
        run_dir = Path(getattr(ctx, "run_dir", ".") or ".")
        prereq_paths = [run_dir / "G1_OUTPUT.json", run_dir / "G2_OUTPUT.json", run_dir / "G3_OUTPUT.json"]
        prereq_missing = any((not p.exists()) for p in prereq_paths)

        def _schema_ok_from_g1(g1_out: Dict[str, Any]) -> bool:
            design = g1_out.get("design") if isinstance(g1_out, dict) else None
            if not isinstance(design, dict):
                return False
            for key in ("requirements", "interfaces", "constraints", "acceptance_criteria"):
                v = design.get(key)
                if not isinstance(v, list) or len(v) == 0:
                    return False
            return True

        schema_ok = False
        if not prereq_missing:
            try:
                g1_text = (run_dir / "G1_OUTPUT.json").read_text(encoding="utf-8")
                g1_out = json.loads(g1_text)
                if isinstance(g1_out, dict):
                    schema_ok = _schema_ok_from_g1(g1_out)
            except Exception:
                schema_ok = False

        policy = evaluate_g4(prereq_missing=prereq_missing, schema_ok=schema_ok)

        output = {
            "policy": _policy_to_dict(policy),
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
            "policy_reason_code": getattr(policy, "reason_code", None),
            "attempt": (ctx.meta.attempts or {}).get("G4", 1),
            "ai": {"engine": "gpt", "used": gpt_used, "error": gpt_error},
        }

        op_rc = ReasonCode.SKIPPED if not gpt_used else (ReasonCode.PROVIDER_ERROR if gpt_error else ReasonCode.SUCCESS)
        meta = normalize_meta(meta, reason_code=op_rc, provider="gpt", source="g4_self_check", error=(gpt_error or None))

        if prompt_ident is not None:
            meta["prompt"] = {
                "id": self.prompt_id,
                "name": prompt_ident.name,
                "version": prompt_ident.version,
                "sha256": prompt_ident.sha256_prefixed,
            }

        return G4SelfCheckPluginResult(decision=policy.decision, output=output, meta=meta)


# ---------------------------------------------------------------------------
# Compatibility shim (used by src.gates.g4_self_check)
# ---------------------------------------------------------------------------


@dataclass
class G4SelfCheckAIShim:
    used: bool
    error: Optional[str]
    text: str
    raw: Dict[str, Any]


def run_g4_self_check_plugin(
    *, provider: Any, prompt_text: str, prompt_ident: Any, is_pytest: bool
) -> G4SelfCheckAIShim:
    """Call the injected provider using the repo provider contract.

    Returns a stable structure for the gate wrapper.
    """

    if is_pytest:
        return G4SelfCheckAIShim(used=False, error=None, text="", raw={})

    try:
        text, raw, err = provider.generate_text(
            prompt=prompt_text,
            temperature=0.0,
            max_output_tokens=512,
        )
        return G4SelfCheckAIShim(used=True, error=err, text=str(text), raw=raw or {})
    except Exception as e:
        return G4SelfCheckAIShim(used=True, error=str(e), text="", raw={})

class G4AIProviderRunner(Protocol):
    def generate(self, *, prompt_text: str, prompt_ident: Any, is_pytest: bool) -> "G4SelfCheckAIShim":
        ...


@dataclass
class _G4AIProviderRunnerImpl:
    provider: Any

    def generate(self, *, prompt_text: str, prompt_ident: Any, is_pytest: bool) -> "G4SelfCheckAIShim":
        return run_g4_self_check_plugin(
            provider=self.provider,
            prompt_text=prompt_text,
            prompt_ident=prompt_ident,
            is_pytest=is_pytest,
        )


def resolve(ctx: GateContext) -> Optional[G4AIProviderRunner]:
    """Unified entrypoint: resolve(ctx) -> optional runner."""
    sel = negotiate(
        gate_id="G4",
        capability="self_check",
        ctx=ctx,
        priority_chain=[("providers", "gpt")],
        required=False,
    )
    if sel.selected is None:
        return None
    return _G4AIProviderRunnerImpl(provider=sel.selected)
