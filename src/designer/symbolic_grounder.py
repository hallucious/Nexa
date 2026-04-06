from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hashlib
import re

from src.designer.models.designer_intent import TargetScope
from src.designer.models.grounded_intent import GroundedIntent
from src.designer.models.semantic_intent import SemanticIntent
from src.designer.normalization_context import RequestNormalizationContext


class DesignerSymbolicGrounder:
    def ground(self, semantic_intent: SemanticIntent, *, context: RequestNormalizationContext, precomputed_scope: TargetScope | None = None) -> GroundedIntent:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass(frozen=True)
class DeterministicSymbolicGrounder(DesignerSymbolicGrounder):
    def ground(self, semantic_intent: SemanticIntent, *, context: RequestNormalizationContext, precomputed_scope: TargetScope | None = None) -> GroundedIntent:
        scope = precomputed_scope or self.build_scope(semantic_intent.category, semantic_intent.effective_request_text, context)
        return GroundedIntent(
            grounded_intent_id=_stable_id("grounded", semantic_intent.user_request_text),
            semantic_intent=semantic_intent,
            target_scope=scope,
            resolved_node_refs=scope.node_refs,
            matched_provider_id=self.infer_provider_id(semantic_intent.effective_request_text, context),
            matched_plugin_id=self.infer_plugin_id(semantic_intent.effective_request_text, context),
            matched_prompt_id=self.infer_prompt_id(semantic_intent.effective_request_text, context),
            insert_between_parameters=self.infer_insert_between_parameters(
                semantic_intent.user_request_text,
                scope,
                context,
            ),
        )

    def build_scope(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> TargetScope:
        text = request_text.casefold()
        broad = any(term in text for term in ("all ", "entire", "whole", "across the circuit", "every"))
        explicit_node_refs = self.explicit_node_refs(request_text, context)
        if not explicit_node_refs and not broad:
            selected_node_refs = self.selected_node_refs(context)
            if len(selected_node_refs) == 1 and category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"}:
                explicit_node_refs = selected_node_refs
        node_refs = self.resolve_target_node_refs_from_committed_summary(
            category,
            request_text,
            context,
            explicit_node_refs,
        )
        max_change_scope = "broad" if broad else "bounded"
        card_scope = context.session_state_card.target_scope if context.session_state_card is not None else None
        if category == "CREATE_CIRCUIT":
            mode = card_scope.mode if card_scope is not None and card_scope.mode == "new_circuit" else "new_circuit"
            max_scope = card_scope.touch_budget if card_scope is not None else max_change_scope
            return TargetScope(mode=mode, node_refs=node_refs, max_change_scope=max_scope)
        if category in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"}:
            return TargetScope(
                mode="read_only",
                savefile_ref=context.working_save_ref,
                node_refs=node_refs,
                max_change_scope="minimal",
            )
        if card_scope is not None:
            if card_scope.mode == "node_only":
                refs = tuple(node_refs) or tuple(card_scope.allowed_node_refs)
                return TargetScope(
                    mode="node_only",
                    savefile_ref=context.working_save_ref,
                    node_refs=refs,
                    max_change_scope=card_scope.touch_budget,
                )
            if node_refs:
                return TargetScope(
                    mode="node_only",
                    savefile_ref=context.working_save_ref,
                    node_refs=node_refs,
                    max_change_scope=card_scope.touch_budget,
                )
            return TargetScope(
                mode=card_scope.mode if card_scope.mode != "read_only" else "existing_circuit",
                savefile_ref=context.working_save_ref,
                node_refs=tuple(card_scope.allowed_node_refs),
                edge_refs=tuple(card_scope.allowed_edge_refs),
                max_change_scope=card_scope.touch_budget,
            )
        if node_refs:
            return TargetScope(
                mode="node_only",
                savefile_ref=context.working_save_ref,
                node_refs=node_refs,
                max_change_scope=max_change_scope,
            )
        return TargetScope(
            mode="existing_circuit",
            savefile_ref=context.working_save_ref,
            max_change_scope=max_change_scope,
        )

    def explicit_node_refs(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> tuple[str, ...]:
        direct_refs = self.resolve_node_refs(self.extract_node_refs(request_text), context)
        if direct_refs:
            return direct_refs
        return self.infer_node_refs_from_context_mentions(request_text, context)

    def selected_node_refs(self, context: RequestNormalizationContext) -> tuple[str, ...]:
        card = context.session_state_card
        if card is None or card.current_selection.selection_mode != "node":
            return ()
        return self.resolve_node_refs(tuple(card.current_selection.selected_refs), context)

    def infer_node_refs_from_context_mentions(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> tuple[str, ...]:
        candidates = self.available_node_refs(context)
        if not candidates:
            return ()
        text = request_text.casefold()
        matches: list[str] = []
        for candidate in candidates:
            aliases = self.resource_aliases(candidate)
            if any(self.contains_alias(text, alias) for alias in aliases):
                matches.append(candidate)
        return tuple(dict.fromkeys(matches))

    def available_node_refs(self, context: RequestNormalizationContext) -> tuple[str, ...]:
        if context.session_state_card is None:
            return ()
        refs = tuple(context.session_state_card.current_working_save.node_list)
        if refs:
            return refs
        return tuple(context.session_state_card.target_scope.allowed_node_refs)

    def available_resource_ids(
        self,
        context: RequestNormalizationContext,
        *,
        resource_type: str,
    ) -> tuple[str, ...]:
        card = context.session_state_card
        if card is None:
            return ()
        available_resources = getattr(card.available_resources, resource_type, ())
        resource_ids = [item.id for item in available_resources if getattr(item, "id", None)]
        if resource_ids:
            return tuple(dict.fromkeys(resource_ids))
        fallback_attr = {
            "prompts": "prompt_refs",
            "providers": "provider_refs",
            "plugins": "plugin_refs",
        }[resource_type]
        return tuple(dict.fromkeys(getattr(card.current_working_save, fallback_attr, ())))

    def match_resource_id_from_text(self, text: str, resource_ids: tuple[str, ...]) -> str | None:
        lowered = text.casefold()
        matches: list[tuple[int, int, str]] = []
        for resource_id in resource_ids:
            resource_lower = resource_id.casefold()
            score = 0
            if resource_lower and resource_lower in lowered:
                score = max(score, 100)
            for alias in self.resource_aliases(resource_id):
                if self.contains_alias(lowered, alias):
                    score = max(score, max(10, len(alias)))
            if score:
                matches.append((score, len(resource_id), resource_id))
        if not matches:
            return None
        matches.sort(reverse=True)
        return matches[0][2]

    def resource_aliases(self, resource_id: str) -> tuple[str, ...]:
        lowered = resource_id.casefold()
        parts = tuple(part for part in re.split(r"[^a-z0-9]+", lowered) if part)
        aliases = {lowered, resource_id.split(":")[-1].casefold()}
        aliases.update(parts)
        if len(parts) >= 2:
            aliases.add(" ".join(parts[-2:]))
            aliases.add(" ".join(parts))
        return tuple(sorted(alias for alias in aliases if alias))

    def contains_alias(self, text: str, alias: str) -> bool:
        return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", text))

    def infer_provider_id(self, text: str, context: RequestNormalizationContext) -> str:
        matched = self.match_resource_id_from_text(text, self.available_resource_ids(context, resource_type="providers"))
        if matched is not None:
            return matched
        lowered = text.casefold()
        if "claude" in lowered or "anthropic" in lowered:
            return "anthropic:claude"
        if "gemini" in lowered or "google" in lowered:
            return "google:gemini"
        if "perplexity" in lowered:
            return "perplexity:sonar"
        return "openai:gpt"

    def infer_plugin_id(self, text: str, context: RequestNormalizationContext) -> str:
        matched = self.match_resource_id_from_text(text, self.available_resource_ids(context, resource_type="plugins"))
        if matched is not None:
            return matched
        lowered = text.casefold()
        if "search" in lowered:
            return "web.search"
        if "normalize" in lowered:
            return "text.normalize"
        if "validate" in lowered:
            return "schema.validate"
        return "tool.generic"

    def infer_prompt_id(self, text: str, context: RequestNormalizationContext) -> str | None:
        matched = self.match_resource_id_from_text(text, self.available_resource_ids(context, resource_type="prompts"))
        if matched is not None:
            return matched
        prompt_refs = self.available_resource_ids(context, resource_type="prompts")
        return prompt_refs[0] if len(prompt_refs) == 1 else None

    def available_edge_pairs(self, context: RequestNormalizationContext) -> tuple[tuple[str, str], ...]:
        card = context.session_state_card
        if card is None:
            return ()
        pairs: list[tuple[str, str]] = []
        for edge in card.current_working_save.edge_list or card.target_scope.allowed_edge_refs:
            if "->" not in edge:
                continue
            left, right = edge.split("->", 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                pairs.append((left, right))
        return tuple(dict.fromkeys(pairs))

    def predecessors_for_node(self, node_ref: str, context: RequestNormalizationContext) -> tuple[str, ...]:
        return tuple(source for source, target in self.available_edge_pairs(context) if target == node_ref)

    def successors_for_node(self, node_ref: str, context: RequestNormalizationContext) -> tuple[str, ...]:
        return tuple(target for source, target in self.available_edge_pairs(context) if source == node_ref)

    def extract_between_node_refs(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> tuple[str, str] | None:
        patterns = (
            r"\bbetween\s+(?:the\s+)?node\s+([A-Za-z0-9_\-\.]+)\s+and\s+(?:the\s+)?node\s+([A-Za-z0-9_\-\.]+)",
            r"\bbetween\s+(?:the\s+)?([A-Za-z0-9_\-\.]+)\s+and\s+(?:the\s+)?([A-Za-z0-9_\-\.]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, request_text, flags=re.IGNORECASE)
            if not match:
                continue
            refs = self.resolve_node_refs((match.group(1), match.group(2)), context)
            if len(refs) == 2:
                return refs[0], refs[1]
        return None

    def infer_insert_between_parameters(
        self,
        request_text: str,
        scope: TargetScope,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        parameters: dict[str, Any] = {"position": "between"}
        between_refs = self.extract_between_node_refs(request_text, context)
        if between_refs is not None:
            before_node, after_node = between_refs
            parameters.update({
                "before_node": before_node,
                "after_node": after_node,
                "from_node": before_node,
                "to_node": after_node,
            })
            return parameters
        target_ref = self.first_target_ref(scope, request_text)
        if target_ref is None:
            return parameters
        text = request_text.casefold()
        if any(phrase in text for phrase in ("before", "in front of", "ahead of")):
            parameters.update({"after_node": target_ref, "to_node": target_ref, "position": "before"})
            predecessors = self.predecessors_for_node(target_ref, context)
            if len(predecessors) == 1:
                parameters.update({"before_node": predecessors[0], "from_node": predecessors[0]})
            return parameters
        if any(phrase in text for phrase in ("after", "behind")):
            parameters.update({"before_node": target_ref, "from_node": target_ref, "position": "after"})
            successors = self.successors_for_node(target_ref, context)
            if len(successors) == 1:
                parameters.update({"after_node": successors[0], "to_node": successors[0]})
            return parameters
        return parameters

    def resolve_node_refs(
        self,
        node_refs: tuple[str, ...],
        context: RequestNormalizationContext,
    ) -> tuple[str, ...]:
        if not node_refs:
            return node_refs
        candidates: tuple[str, ...] = ()
        if context.session_state_card is not None:
            candidates = tuple(context.session_state_card.current_working_save.node_list)
            if not candidates:
                candidates = tuple(context.session_state_card.target_scope.allowed_node_refs)
        if not candidates:
            return node_refs
        resolved: list[str] = []
        for ref in node_refs:
            if ref in candidates:
                resolved.append(ref)
                continue
            suffix_matches = [item for item in candidates if item.endswith(f".{ref}")]
            if len(suffix_matches) == 1:
                resolved.append(suffix_matches[0])
            else:
                resolved.append(ref)
        return tuple(dict.fromkeys(resolved))

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

    def first_node_ref(self, request_text: str) -> str | None:
        refs = self.extract_node_refs(request_text)
        return refs[0] if refs else None

    def first_target_ref(self, scope: TargetScope, request_text: str) -> str | None:
        if scope.node_refs:
            return scope.node_refs[0]
        return self.first_node_ref(request_text)

    def resolve_target_node_refs_from_committed_summary(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
        explicit_node_refs: tuple[str, ...],
    ) -> tuple[str, ...]:
        # Commit-summary resolution currently remains owned by the compatibility facade.
        return explicit_node_refs



def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"
