from __future__ import annotations

from typing import Any
import re

from src.designer.models.designer_intent import TargetScope
from src.designer.normalization_context import RequestNormalizationContext
from src.designer.symbolic_grounder import DesignerSymbolicGrounder


class DesignerLegacyMutationHeuristics:
    """Legacy bounded heuristics that still support the compatibility facade.

    The long-term goal is to minimize the role of these rules, but during
    migration the compatibility facade still needs a stable home for phrase
    detection and fallback mutation helpers. Keeping them here prevents
    ``request_normalizer.py`` from continuing to grow as a monolith.
    """

    def __init__(self, symbolic_grounder: DesignerSymbolicGrounder) -> None:
        self._symbolic_grounder = symbolic_grounder

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

    def requests_review_gate(self, text: str) -> bool:
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
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def requests_provider_change(self, text: str, context: RequestNormalizationContext) -> bool:
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
        available_provider_ids = self.available_resource_ids(context, resource_type="providers")
        if self.match_resource_id_from_text(text, available_provider_ids) is None:
            return False
        provider_verbs = ("use", "switch", "change", "replace", "move", "run", "instead", "have", "make", "let", "swap")
        return any(verb in text for verb in provider_verbs)

    def requests_plugin_attach(self, text: str, context: RequestNormalizationContext) -> bool:
        explicit_patterns = (
            r"\b(attach|add|use|enable)\s+plugin\b",
            r"\b(add|give|enable|use|equip|have|make|let)\s+.*\b(search|normalize|validate|lookup)\b",
            r"\b(search tool|search plugin|lookup tool|web search)\b",
        )
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in explicit_patterns):
            return True
        available_plugin_ids = self.available_resource_ids(context, resource_type="plugins")
        if self.match_resource_id_from_text(text, available_plugin_ids) is None:
            return False
        plugin_verbs = ("attach", "add", "use", "enable", "give", "equip", "have", "make", "let")
        return any(verb in text for verb in plugin_verbs)

    def requests_prompt_change(self, text: str, context: RequestNormalizationContext) -> bool:
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
        available_prompt_ids = self.available_resource_ids(context, resource_type="prompts")
        if self.match_resource_id_from_text(text, available_prompt_ids) is None:
            return False
        prompt_verbs = ("use", "change", "replace", "update", "set", "swap")
        prompt_nouns = ("prompt", "instruction", "template")
        return any(verb in text for verb in prompt_verbs) and any(noun in text for noun in prompt_nouns)

    def requests_insert_between(self, text: str) -> bool:
        positional_terms = ("insert", "between", "before", "after", "in front of", "ahead of", "behind")
        if any(term in text for term in positional_terms):
            return True
        natural_insert_patterns = (
            r"\b(put|place|drop|slip)\s+.*\s+in front of\b",
            r"\b(put|place|drop|slip)\s+.*\s+(before|after|behind)\b",
        )
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in natural_insert_patterns)

    def infer_provider_id(self, text: str, context: RequestNormalizationContext) -> str:
        return self._symbolic_grounder.infer_provider_id(text, context)

    def infer_plugin_id(self, text: str, context: RequestNormalizationContext) -> str:
        return self._symbolic_grounder.infer_plugin_id(text, context)

    def infer_prompt_id(self, text: str, context: RequestNormalizationContext) -> str | None:
        return self._symbolic_grounder.infer_prompt_id(text, context)

    def explicit_node_refs(self, request_text: str, context: RequestNormalizationContext) -> tuple[str, ...]:
        direct_refs = self.resolve_node_refs(self.extract_node_refs(request_text), context)
        if direct_refs:
            return direct_refs
        return self.infer_node_refs_from_context_mentions(request_text, context)

    def selected_node_refs(self, context: RequestNormalizationContext) -> tuple[str, ...]:
        return self._symbolic_grounder.selected_node_refs(context)

    def infer_node_refs_from_context_mentions(self, request_text: str, context: RequestNormalizationContext) -> tuple[str, ...]:
        return self._symbolic_grounder.infer_node_refs_from_context_mentions(request_text, context)

    def available_resource_ids(self, context: RequestNormalizationContext, *, resource_type: str) -> tuple[str, ...]:
        return self._symbolic_grounder.available_resource_ids(context, resource_type=resource_type)

    def match_resource_id_from_text(self, text: str, resource_ids: tuple[str, ...]) -> str | None:
        return self._symbolic_grounder.match_resource_id_from_text(text, resource_ids)

    def infer_insert_between_parameters(self, request_text: str, scope: TargetScope, context: RequestNormalizationContext) -> dict[str, Any]:
        return self._symbolic_grounder.infer_insert_between_parameters(request_text, scope, context)

    def resolve_node_refs(self, node_refs: tuple[str, ...], context: RequestNormalizationContext) -> tuple[str, ...]:
        return self._symbolic_grounder.resolve_node_refs(node_refs, context)

    def extract_node_refs(self, request_text: str) -> tuple[str, ...]:
        prioritized_patterns = (
            r"\bin\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bon\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bfor\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bat\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bnode\s+([A-Za-z0-9_\-\.]+)",
        )
        stopwords = {"before", "after", "between", "final", "a", "an", "the"}
        ordered_refs: list[str] = []
        seen: set[str] = set()
        for pattern in prioritized_patterns:
            for match in re.finditer(pattern, request_text, flags=re.IGNORECASE):
                ref = match.group(1).rstrip('.,;:')
                if ref.casefold() in stopwords:
                    continue
                if ref not in seen:
                    ordered_refs.append(ref)
                    seen.add(ref)
        return tuple(ordered_refs)

    def first_target_ref(self, scope: TargetScope, request_text: str) -> str | None:
        if scope.node_refs:
            return scope.node_refs[0]
        return self.first_node_ref(request_text)

    def first_node_ref(self, request_text: str) -> str | None:
        return self._symbolic_grounder.first_node_ref(request_text)
