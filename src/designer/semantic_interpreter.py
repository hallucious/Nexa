from __future__ import annotations

from dataclasses import dataclass
import hashlib

from src.designer.models.semantic_intent import SemanticIntent
from src.designer.normalization_context import RequestNormalizationContext


class DesignerSemanticInterpreter:
    def interpret(self, request_text: str, *, context: RequestNormalizationContext) -> SemanticIntent:  # pragma: no cover - interface
        raise NotImplementedError


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
        if self.requests_create_circuit(text):
            return "CREATE_CIRCUIT"
        if any(term in text for term in ("add", "change", "replace", "remove", "rename", "insert", "update")):
            return "MODIFY_CIRCUIT"
        return "MODIFY_CIRCUIT"

    def requests_create_circuit(self, text: str) -> bool:
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

    def requests_provider_change(self, text: str) -> bool:
        provider_terms = ("claude", "anthropic", "gemini", "google", "perplexity", "gpt", "openai")
        return any(term in text for term in provider_terms) and any(
            term in text for term in ("provider", "use", "switch", "change", "replace", "move", "run", "swap")
        )

    def requests_plugin_attach(self, text: str) -> bool:
        plugin_terms = ("plugin", "tool", "search", "lookup", "web search", "normalize", "validate")
        return any(term in text for term in plugin_terms) and any(
            term in text for term in ("attach", "add", "use", "enable", "give", "equip")
        )

    def requests_prompt_change(self, text: str) -> bool:
        prompt_terms = ("prompt", "instruction", "template")
        return any(term in text for term in prompt_terms) and any(
            term in text for term in ("change", "replace", "update", "set", "use", "follow")
        )



def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"
