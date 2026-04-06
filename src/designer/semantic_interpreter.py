from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Any, Mapping, Protocol, runtime_checkable

from src.designer.models.semantic_intent import (
    SemanticActionCandidate,
    SemanticIntent,
    SemanticResourceDescriptor,
    SemanticTargetDescriptor,
)
from src.designer.normalization_context import RequestNormalizationContext


def requests_create_circuit(text: str) -> bool:
    explicit_create_terms = (
        "create",
        "build",
        "new circuit",
        "new workflow",
        "from scratch",
    )
    if any(term in text for term in explicit_create_terms):
        return True
    if "make" in text and any(term in text for term in ("circuit", "workflow", "pipeline")):
        return True
    return False


def requests_review_gate(text: str) -> bool:
    patterns = (
        r"\bhuman review\b",
        r"\bmanual review\b",
        r"\breview gate\b",
        r"\bapproval gate\b",
        r"\brequire approval\b",
        r"\bneeds approval\b",
        r"\b(add|insert|require)\s+(a\s+)?review\b",
        r"\b(add|insert|require)\s+(a\s+)?approval\b",
    )
    return any(__import__("re").search(pattern, text, flags=__import__("re").IGNORECASE) for pattern in patterns)


def requests_provider_change(text: str, context: RequestNormalizationContext, symbolic_grounder: Any) -> bool:
    import re
    explicit_patterns = (
        r"\b(replace|switch|change) provider\b",
        r"\b(switch|change|move)\s+.*\s+to\s+(claude|anthropic|gemini|google|perplexity|gpt|openai)\b",
        r"\bswap\s+.*\s+(?:to|over\s+to)\s+(claude|anthropic|gemini|google|perplexity|gpt|openai)\b",
        r"\buse\s+(claude|anthropic|gemini|google|perplexity|gpt|openai)\b",
        r"\brun\s+.*\s+on\s+(claude|anthropic|gemini|google|perplexity|gpt|openai)\b",
        r"\b(have|make|let)\s+.*\s+use\s+(claude|anthropic|gemini|google|perplexity|gpt|openai)\b",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in explicit_patterns):
        return True
    available_provider_ids = symbolic_grounder.available_resource_ids(context, resource_type="providers")
    if symbolic_grounder.match_resource_id_from_text(text, available_provider_ids) is None:
        return False
    provider_verbs = ("use", "switch", "change", "replace", "move", "run", "instead", "have", "make", "let", "swap")
    return any(verb in text for verb in provider_verbs)


def requests_plugin_attach(text: str, context: RequestNormalizationContext, symbolic_grounder: Any) -> bool:
    import re
    explicit_patterns = (
        r"\b(attach|add|use|enable)\s+plugin\b",
        r"\b(add|give|enable|use|equip|have|make|let)\s+.*\b(search|normalize|validate|lookup)\b",
        r"\b(search tool|search plugin|lookup tool|web search)\b",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in explicit_patterns):
        return True
    available_plugin_ids = symbolic_grounder.available_resource_ids(context, resource_type="plugins")
    if symbolic_grounder.match_resource_id_from_text(text, available_plugin_ids) is None:
        return False
    plugin_verbs = ("attach", "add", "use", "enable", "give", "equip", "have", "make", "let")
    return any(verb in text for verb in plugin_verbs)


def requests_prompt_change(text: str, context: RequestNormalizationContext, symbolic_grounder: Any) -> bool:
    import re
    explicit_patterns = (
        r"\b(change|replace|update|set)\s+(the\s+)?prompt\b",
        r"\b(change|replace|update|set)\s+(the\s+)?instruction\b",
        r"\b(change|replace|update|set)\s+(the\s+)?template\b",
        r"\buse\s+.*\bprompt\b",
        r"\buse\s+.*\binstruction\b",
        r"\buse\s+.*\btemplate\b",
        r"\b(have|make|let)\s+.*\s+(use|follow)\s+.*\bprompt\b",
        r"\b(have|make|let)\s+.*\s+(use|follow)\s+.*\binstruction\b",
        r"\b(have|make|let)\s+.*\s+(use|follow)\s+.*\btemplate\b",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in explicit_patterns):
        return True
    available_prompt_ids = symbolic_grounder.available_resource_ids(context, resource_type="prompts")
    if symbolic_grounder.match_resource_id_from_text(text, available_prompt_ids) is None:
        return False
    prompt_verbs = ("use", "change", "replace", "update", "set", "swap")
    prompt_nouns = ("prompt", "instruction", "template")
    return any(verb in text for verb in prompt_verbs) and any(noun in text for noun in prompt_nouns)


def requests_insert_between(text: str) -> bool:
    import re
    positional_terms = ("insert", "between", "before", "after", "in front of", "ahead of", "behind")
    if any(term in text for term in positional_terms):
        return True
    natural_insert_patterns = (
        r"\b(put|place|drop|slip)\s+.*\s+in front of\b",
        r"\b(put|place|drop|slip)\s+.*\s+(before|after|behind)\b",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in natural_insert_patterns)


class DesignerSemanticInterpreter:
    def interpret(self, request_text: str, *, context: RequestNormalizationContext) -> SemanticIntent:  # pragma: no cover - interface
        raise NotImplementedError


@runtime_checkable
class SemanticIntentStructuredBackend(Protocol):
    def generate_semantic_payload(
        self,
        *,
        request_text: str,
        effective_request_text: str,
        context_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class LegacyRuleBasedSemanticInterpreter(DesignerSemanticInterpreter):
    """Compatibility semantic interpreter for the pre-LLM Designer normalizer.

    This keeps current rule-based category inference while the new Stage 1/Stage 2
    boundary is introduced. It deliberately limits itself to semantic interpretation
    concerns: effective request composition and intent-category inference.
    """

    def interpret(self, request_text: str, *, context: RequestNormalizationContext) -> SemanticIntent:
        effective_request_text = self.compose_effective_request_text(request_text, context)
        category = self.infer_category(effective_request_text)
        return SemanticIntent(
            semantic_intent_id=_stable_id("semantic", request_text),
            user_request_text=request_text.strip(),
            effective_request_text=effective_request_text,
            category=category,
        )

    def compose_effective_request_text(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> str:
        card = context.session_state_card
        if card is None:
            return request_text
        parts = [request_text.strip()]
        if card.conversation_context.clarified_interpretation:
            parts.append(card.conversation_context.clarified_interpretation.strip())
        if card.revision_state.user_corrections:
            parts.extend(item.strip() for item in card.revision_state.user_corrections if item.strip())
        return " ".join(part for part in parts if part)

    def infer_category(self, request_text: str) -> str:
        text = request_text.casefold()
        if any(term in text for term in ("explain", "what does", "why is this")):
            return "EXPLAIN_CIRCUIT"
        if any(term in text for term in ("repair", "fix", "broken", "restore")):
            return "REPAIR_CIRCUIT"
        if any(term in text for term in ("optimize", "optimise", "improve", "reduce cost", "more reliable")):
            return "OPTIMIZE_CIRCUIT"
        if any(term in text for term in ("analyze", "analyse", "risk", "cost", "gap", "why might")):
            return "ANALYZE_CIRCUIT"
        if requests_create_circuit(text):
            return "CREATE_CIRCUIT"
        if any(term in text for term in ("add", "change", "replace", "remove", "rename", "insert", "update")):
            return "MODIFY_CIRCUIT"
        return "MODIFY_CIRCUIT"






@dataclass(frozen=True)
class LLMBackedStructuredSemanticInterpreter(DesignerSemanticInterpreter):
    backend: SemanticIntentStructuredBackend
    fallback_interpreter: DesignerSemanticInterpreter | None = None
    allow_fallback: bool = True

    def interpret(self, request_text: str, *, context: RequestNormalizationContext) -> SemanticIntent:
        effective_request_text = self.compose_effective_request_text(request_text, context)
        context_payload = self.build_context_payload(context)
        try:
            payload = self.backend.generate_semantic_payload(
                request_text=request_text.strip(),
                effective_request_text=effective_request_text,
                context_payload=context_payload,
            )
            semantic_intent = self._build_semantic_intent(
                request_text=request_text,
                effective_request_text=effective_request_text,
                payload=payload,
            )
        except Exception as exc:
            if not self.allow_fallback or self.fallback_interpreter is None:
                raise
            fallback = self.fallback_interpreter.interpret(request_text, context=context)
            return replace(
                fallback,
                notes=tuple(fallback.notes) + (f"llm_semantic_fallback:{exc.__class__.__name__}",),
            )
        return semantic_intent

    def compose_effective_request_text(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> str:
        if self.fallback_interpreter is not None and hasattr(self.fallback_interpreter, "compose_effective_request_text"):
            compose = getattr(self.fallback_interpreter, "compose_effective_request_text")
            return compose(request_text, context)
        card = context.session_state_card
        if card is None:
            return request_text
        parts = [request_text.strip()]
        if card.conversation_context.clarified_interpretation:
            parts.append(card.conversation_context.clarified_interpretation.strip())
        if card.revision_state.user_corrections:
            parts.extend(item.strip() for item in card.revision_state.user_corrections if item.strip())
        return " ".join(part for part in parts if part)

    def build_context_payload(self, context: RequestNormalizationContext) -> Mapping[str, Any]:
        card = context.session_state_card
        if card is None:
            return {"working_save_ref": context.working_save_ref}
        return {
            "working_save_ref": context.working_save_ref,
            "session_id": card.session_id,
            "storage_role": card.storage_role,
            "current_selection": {
                "selection_mode": card.current_selection.selection_mode,
                "selected_refs": list(card.current_selection.selected_refs),
            },
            "target_scope": {
                "mode": card.target_scope.mode,
                "allowed_node_refs": list(card.target_scope.allowed_node_refs),
                "allowed_edge_refs": list(card.target_scope.allowed_edge_refs),
                "touch_budget": card.target_scope.touch_budget,
            },
            "current_working_save": {
                "savefile_ref": card.current_working_save.savefile_ref,
                "node_list": list(card.current_working_save.node_list),
                "edge_list": list(card.current_working_save.edge_list),
                "prompt_refs": list(card.current_working_save.prompt_refs),
                "provider_refs": list(card.current_working_save.provider_refs),
                "plugin_refs": list(card.current_working_save.plugin_refs),
            },
            "available_resources": {
                "providers": [item.id for item in card.available_resources.providers],
                "plugins": [item.id for item in card.available_resources.plugins],
                "prompts": [item.id for item in card.available_resources.prompts],
            },
        }

    def _build_semantic_intent(
        self,
        *,
        request_text: str,
        effective_request_text: str,
        payload: Mapping[str, Any],
    ) -> SemanticIntent:
        self._ensure_no_forbidden_canonical_ids(payload)
        category = str(payload.get("category") or payload.get("primary_category") or "MODIFY_CIRCUIT").strip() or "MODIFY_CIRCUIT"
        interpreted_text = str(payload.get("effective_request_text") or effective_request_text).strip() or effective_request_text
        confidence_hint = self._coerce_confidence(payload.get("confidence_hint"))
        notes = self._coerce_notes(payload.get("notes") or payload.get("interpretation_notes"))
        action_candidates = tuple(self._coerce_action_candidate(item) for item in self._coerce_action_payloads(payload.get("action_candidates") or payload.get("semantic_actions")))
        clarification_required = self._coerce_bool(payload.get("clarification_required") or payload.get("requires_clarification"))
        clarification_questions = self._coerce_text_list(payload.get("clarification_questions") or payload.get("clarification_requests"))
        semantic_ambiguity_notes = self._coerce_text_list(payload.get("semantic_ambiguity_notes") or payload.get("ambiguity_notes"))
        return SemanticIntent(
            semantic_intent_id=_stable_id("semantic", request_text),
            user_request_text=request_text.strip(),
            effective_request_text=interpreted_text,
            category=category,
            action_candidates=action_candidates,
            confidence_hint=confidence_hint,
            notes=notes,
            clarification_required=clarification_required,
            clarification_questions=clarification_questions,
            semantic_ambiguity_notes=semantic_ambiguity_notes,
        )

    def _ensure_no_forbidden_canonical_ids(self, payload: Mapping[str, Any]) -> None:
        forbidden_keys = {
            "canonical_ref",
            "canonical_id",
            "target_ref",
            "node_ref",
            "provider_id",
            "plugin_id",
            "prompt_id",
            "resource_id",
        }

        def _walk(value: Any) -> None:
            if isinstance(value, Mapping):
                hit = forbidden_keys.intersection(value.keys())
                if hit:
                    raise ValueError(f"Semantic payload must not contain canonical ids: {sorted(hit)}")
                for item in value.values():
                    _walk(item)
            elif isinstance(value, list):
                for item in value:
                    _walk(item)

        _walk(payload)

    def _coerce_action_payloads(self, payload: Any) -> tuple[Mapping[str, Any], ...]:
        if payload is None:
            return ()
        if not isinstance(payload, list):
            raise ValueError("Structured semantic payload action_candidates must be a list")
        coerced: list[Mapping[str, Any]] = []
        for item in payload:
            if not isinstance(item, Mapping):
                raise ValueError("Each structured semantic action candidate must be an object")
            coerced.append(item)
        return tuple(coerced)

    def _coerce_action_candidate(self, payload: Mapping[str, Any]) -> SemanticActionCandidate:
        action_type = str(payload.get("action_type") or "").strip()
        if not action_type:
            raise ValueError("Structured semantic action candidate requires action_type")
        target_descriptor = self._coerce_target_descriptor(payload.get("target_node_descriptor") or payload.get("target_descriptor"))
        provider_descriptor = self._coerce_resource_descriptor(payload.get("provider_descriptor"), default_kind="provider")
        plugin_descriptor = self._coerce_resource_descriptor(payload.get("plugin_descriptor"), default_kind="plugin")
        prompt_descriptor = self._coerce_resource_descriptor(payload.get("prompt_descriptor"), default_kind="prompt")
        notes = self._coerce_notes(payload.get("notes") or payload.get("rationale"))
        return SemanticActionCandidate(
            action_type=action_type,
            target_node_descriptor=target_descriptor,
            provider_descriptor=provider_descriptor,
            plugin_descriptor=plugin_descriptor,
            prompt_descriptor=prompt_descriptor,
            notes=notes,
        )

    def _coerce_target_descriptor(self, payload: Any) -> SemanticTargetDescriptor | None:
        if payload is None:
            return None
        if not isinstance(payload, Mapping):
            raise ValueError("Semantic target descriptor must be an object")
        return SemanticTargetDescriptor(
            kind=str(payload.get("kind") or payload.get("entity_kind") or "node"),
            label_hint=self._optional_text(payload.get("label_hint")),
            role_hint=self._optional_text(payload.get("role_hint")),
            position_hint=self._optional_text(payload.get("position_hint") or payload.get("ordinal_hint") or payload.get("relationship_hint")),
            raw_reference_text=self._optional_text(payload.get("raw_reference_text") or payload.get("explicit_user_reference") or payload.get("candidate_reference_text")),
        )

    def _coerce_resource_descriptor(
        self,
        payload: Any,
        *,
        default_kind: str,
    ) -> SemanticResourceDescriptor | None:
        if payload is None:
            return None
        if not isinstance(payload, Mapping):
            raise ValueError("Semantic resource descriptor must be an object")
        return SemanticResourceDescriptor(
            resource_type=str(payload.get("resource_type") or payload.get("resource_kind") or default_kind),
            family=self._optional_text(payload.get("family") or payload.get("family_hint")),
            label_hint=self._optional_text(payload.get("label_hint")),
            capability_hint=self._optional_text(payload.get("capability_hint") or payload.get("style_hint")),
            raw_reference_text=self._optional_text(payload.get("raw_reference_text") or payload.get("user_reference_text")),
        )

    def _coerce_bool(self, payload: Any) -> bool:
        if payload is None:
            return False
        if isinstance(payload, bool):
            return payload
        if isinstance(payload, str):
            return payload.strip().casefold() in {"true", "1", "yes", "required"}
        return bool(payload)

    def _coerce_text_list(self, payload: Any) -> tuple[str, ...]:
        if payload is None:
            return ()
        if isinstance(payload, str):
            text = payload.strip()
            return (text,) if text else ()
        if isinstance(payload, list):
            return tuple(str(item).strip() for item in payload if str(item).strip())
        if isinstance(payload, Mapping):
            values = []
            for value in payload.values():
                text = str(value).strip()
                if text:
                    values.append(text)
            return tuple(values)
        text = str(payload).strip()
        return (text,) if text else ()

    def _coerce_notes(self, payload: Any) -> tuple[str, ...]:
        if payload is None:
            return ()
        if isinstance(payload, str):
            text = payload.strip()
            return (text,) if text else ()
        if isinstance(payload, list):
            return tuple(str(item).strip() for item in payload if str(item).strip())
        return (str(payload).strip(),) if str(payload).strip() else ()

    def _coerce_confidence(self, payload: Any) -> float:
        if payload is None:
            return 0.6
        try:
            value = float(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("Structured semantic payload confidence_hint must be numeric") from exc
        return min(1.0, max(0.0, value))

    def _optional_text(self, payload: Any) -> str | None:
        if payload is None:
            return None
        text = str(payload).strip()
        return text or None


def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"
