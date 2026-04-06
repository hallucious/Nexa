from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from src.contracts.provider_contract import ProviderRequest as RuntimeProviderRequest
from src.designer.semantic_interpreter import SemanticIntentStructuredBackend
from src.platform.provider_executor import GenerateTextProviderBridge


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class GenerateTextSemanticBackend(SemanticIntentStructuredBackend):
    """Concrete Stage 1 backend using a provider-like generate_text(...) surface.

    The backend is responsible only for obtaining a structured semantic payload.
    It does not build SemanticIntent directly; that remains the responsibility of
    ``LLMBackedStructuredSemanticInterpreter``.
    """

    provider: Any
    provider_name: str = "designer.semantic.backend"
    temperature: float = 0.0
    max_output_tokens: int = 1200
    instructions: str | None = None
    prompt_builder: Callable[[str, str, Mapping[str, Any]], str] | None = None

    def generate_semantic_payload(
        self,
        *,
        request_text: str,
        effective_request_text: str,
        context_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        bridge = GenerateTextProviderBridge(self.provider, provider_name=self.provider_name)
        prompt = self._build_prompt(
            request_text=request_text,
            effective_request_text=effective_request_text,
            context_payload=context_payload,
        )
        result = bridge.execute(
            RuntimeProviderRequest(
                provider_id=self.provider_name,
                prompt=prompt,
                context={"designer_semantic_context": dict(context_payload)},
                options={
                    "temperature": float(self.temperature),
                    "max_output_tokens": int(self.max_output_tokens),
                    "instructions": self.instructions or self.default_instructions(),
                },
                metadata={
                    "purpose": "designer_semantic_interpretation",
                    "effective_request_text": effective_request_text,
                },
            )
        )
        if result.error is not None:
            raise RuntimeError(f"semantic_backend_provider_error:{result.error.type}:{result.error.message}")
        return self._extract_payload(result)

    def _build_prompt(
        self,
        *,
        request_text: str,
        effective_request_text: str,
        context_payload: Mapping[str, Any],
    ) -> str:
        if self.prompt_builder is not None:
            return self.prompt_builder(request_text, effective_request_text, context_payload)
        return self.default_prompt(
            request_text=request_text,
            effective_request_text=effective_request_text,
            context_payload=context_payload,
        )

    @staticmethod
    def default_instructions() -> str:
        return (
            "You are Nexa Designer Stage 1 Semantic Interpreter. "
            "Interpret the request into structured semantic intent JSON only. "
            "Do not emit canonical ids such as node refs, provider ids, plugin ids, or prompt ids. "
            "Use semantic descriptors only. Return valid JSON with category, confidence_hint, "
            "optional clarification fields, and action_candidates."
        )

    @staticmethod
    def default_prompt(
        *,
        request_text: str,
        effective_request_text: str,
        context_payload: Mapping[str, Any],
    ) -> str:
        context_json = json.dumps(context_payload, ensure_ascii=False, sort_keys=True)
        return (
            "Interpret the following Designer request into structured semantic intent JSON.\n\n"
            "User request:\n"
            f"{request_text.strip()}\n\n"
            "Effective request text:\n"
            f"{effective_request_text.strip()}\n\n"
            "Context payload:\n"
            f"{context_json}\n\n"
            "Required output shape:\n"
            "{\n"
            '  "category": "MODIFY_CIRCUIT",\n'
            '  "confidence_hint": 0.0,\n'
            '  "clarification_required": false,\n'
            '  "clarification_questions": [],\n'
            '  "semantic_ambiguity_notes": [],\n'
            '  "notes": [],\n'
            '  "action_candidates": [\n'
            "    {\n"
            '      "action_type": "replace_provider",\n'
            '      "target_node_descriptor": {"kind": "node", "label_hint": "reviewer", "role_hint": "review"},\n'
            '      "provider_descriptor": {"resource_type": "provider", "family": "claude", "raw_reference_text": "Claude"}\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Important rules:\n"
            "- Never output canonical ids.\n"
            "- Never output provider_id, plugin_id, prompt_id, node_ref, target_ref, canonical_ref, or canonical_id.\n"
            "- If the request is ambiguous, set clarification_required=true and include clarification_questions."
        )

    def _extract_payload(self, result: Any) -> Mapping[str, Any]:
        structured = getattr(result, "structured", None)
        if isinstance(structured, Mapping):
            payload = self._extract_mapping_payload(structured)
            if payload is not None:
                return payload
        output = getattr(result, "output", None)
        if isinstance(output, Mapping):
            payload = self._extract_mapping_payload(output)
            if payload is not None:
                return payload
        raw_text = getattr(result, "raw_text", None)
        if isinstance(raw_text, str) and raw_text.strip():
            return self._parse_payload_text(raw_text)
        if isinstance(output, str) and output.strip():
            return self._parse_payload_text(output)
        raise ValueError("semantic_backend_invalid_output:no_structured_payload")

    def _extract_mapping_payload(self, payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if self._looks_like_semantic_payload(payload):
            return payload
        nested = payload.get("semantic_payload")
        if isinstance(nested, Mapping) and self._looks_like_semantic_payload(nested):
            return nested
        return None

    def _parse_payload_text(self, text: str) -> Mapping[str, Any]:
        candidates = [text.strip()]
        fence_match = _JSON_FENCE_RE.search(text)
        if fence_match is not None:
            candidates.insert(0, fence_match.group(1).strip())
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            candidates.append(text[first_brace:last_brace + 1].strip())
        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen or not candidate:
                continue
            seen.add(candidate)
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, Mapping):
                continue
            payload = self._extract_mapping_payload(parsed)
            if payload is not None:
                return payload
            if self._looks_like_semantic_payload(parsed):
                return parsed
        raise ValueError("semantic_backend_invalid_json_payload")

    @staticmethod
    def _looks_like_semantic_payload(payload: Mapping[str, Any]) -> bool:
        semantic_keys = {"category", "primary_category", "action_candidates", "semantic_actions", "clarification_required", "clarification_questions"}
        return bool(semantic_keys.intersection(payload.keys()))
