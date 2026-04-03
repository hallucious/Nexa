from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from src.designer.models.designer_intent import (
    ActionSpec,
    AmbiguityFlag,
    AssumptionSpec,
    ConstraintSet,
    DesignerIntent,
    ObjectiveSpec,
    RiskFlag,
    TargetScope,
)


@dataclass(frozen=True)
class RequestNormalizationContext:
    working_save_ref: str | None = None


class DesignerRequestNormalizer:
    """Rule-based Step 2 request normalizer.

    This intentionally avoids LLM calls and produces bounded, reviewable intent
    objects for mutation-oriented designer requests.
    """

    def normalize(self, request_text: str, *, context: RequestNormalizationContext | None = None) -> DesignerIntent:
        if not request_text or not request_text.strip():
            raise ValueError("request_text must be non-empty")
        context = context or RequestNormalizationContext()
        category = self._infer_category(request_text)
        scope = self._build_scope(category, request_text, context)
        actions = self._build_actions(category, request_text)
        assumptions = self._build_assumptions(category, request_text, context)
        ambiguity_flags = self._build_ambiguity_flags(category, request_text, context)
        risk_flags = self._build_risk_flags(request_text)
        requires_confirmation = bool(ambiguity_flags or [flag for flag in risk_flags if flag.severity == "high"])
        constraints = self._build_constraints(request_text)
        objective = ObjectiveSpec(primary_goal=request_text.strip())
        explanation = self._build_explanation(category, scope, ambiguity_flags)
        return DesignerIntent(
            intent_id=_stable_id("intent", request_text),
            category=category,
            user_request_text=request_text.strip(),
            target_scope=scope,
            objective=objective,
            constraints=constraints,
            proposed_actions=tuple(actions),
            assumptions=tuple(assumptions),
            ambiguity_flags=tuple(ambiguity_flags),
            risk_flags=tuple(risk_flags),
            requires_user_confirmation=requires_confirmation,
            confidence=self._estimate_confidence(ambiguity_flags),
            explanation=explanation,
        )

    def _infer_category(self, request_text: str) -> str:
        text = request_text.casefold()
        if any(term in text for term in ("explain", "what does", "why is this")):
            return "EXPLAIN_CIRCUIT"
        if any(term in text for term in ("repair", "fix", "broken", "restore")):
            return "REPAIR_CIRCUIT"
        if any(term in text for term in ("optimize", "optimise", "improve", "reduce cost", "more reliable")):
            return "OPTIMIZE_CIRCUIT"
        if any(term in text for term in ("analyze", "analyse", "risk", "cost", "gap", "why might")):
            return "ANALYZE_CIRCUIT"
        if any(term in text for term in ("create", "make", "build", "new circuit")):
            return "CREATE_CIRCUIT"
        if any(term in text for term in ("add", "change", "replace", "remove", "rename", "insert", "update")):
            return "MODIFY_CIRCUIT"
        return "MODIFY_CIRCUIT"

    def _build_scope(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> TargetScope:
        text = request_text.casefold()
        broad = any(term in text for term in ("all ", "entire", "whole", "across the circuit", "every"))
        node_refs = self._extract_node_refs(request_text)
        max_change_scope = "broad" if broad else "bounded"
        if category == "CREATE_CIRCUIT":
            return TargetScope(mode="new_circuit", node_refs=node_refs, max_change_scope=max_change_scope)
        if category in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"}:
            return TargetScope(
                mode="read_only",
                savefile_ref=context.working_save_ref,
                node_refs=node_refs,
                max_change_scope="minimal",
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

    def _build_constraints(self, request_text: str) -> ConstraintSet:
        text = request_text.casefold()
        return ConstraintSet(
            cost_limit="low" if "low cost" in text or "reduce cost" in text else None,
            speed_priority="high" if "faster" in text or "latency" in text else None,
            quality_priority="high" if "quality" in text or "reliable" in text else None,
            determinism_preference="high" if "determin" in text else None,
            human_review_required="review" in text or "approve" in text,
        )

    def _build_actions(self, category: str, request_text: str) -> list[ActionSpec]:
        text = request_text.casefold()
        if category == "CREATE_CIRCUIT":
            return [
                ActionSpec(
                    action_type="create_node",
                    target_ref="node.start",
                    parameters={"kind": "provider"},
                    rationale="A new circuit proposal requires at least one starting node.",
                ),
                ActionSpec(
                    action_type="define_output",
                    target_ref="output.final",
                    parameters={"source": "node.start.output"},
                    rationale="A new circuit proposal should expose an explicit output binding.",
                ),
            ]
        actions: list[ActionSpec] = []
        if any(term in text for term in ("review", "approve", "human review")):
            actions.append(
                ActionSpec(
                    action_type="add_review_gate",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"review_type": "manual"},
                    rationale="The request explicitly asks for a review/approval step.",
                )
            )
        if any(term in text for term in ("replace provider", "switch provider", "change provider")):
            provider_id = self._infer_provider_id(text)
            actions.append(
                ActionSpec(
                    action_type="replace_provider",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"provider_id": provider_id},
                    rationale="The request explicitly changes the node provider.",
                )
            )
        if any(term in text for term in ("attach plugin", "add plugin", "use plugin")):
            actions.append(
                ActionSpec(
                    action_type="attach_plugin",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"plugin_id": self._infer_plugin_id(text)},
                    rationale="The request explicitly introduces a plugin-backed tool step.",
                )
            )
        if any(term in text for term in ("rename",)):
            actions.append(
                ActionSpec(
                    action_type="rename_component",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"new_name": "renamed_component"},
                    rationale="The request explicitly asks for a rename operation.",
                )
            )
        if any(term in text for term in ("remove", "delete")):
            actions.append(
                ActionSpec(
                    action_type="delete_node",
                    target_ref=self._first_node_ref(request_text),
                    parameters={},
                    rationale="The request explicitly removes an existing structural element.",
                )
            )
        if any(term in text for term in ("insert", "between")):
            actions.append(
                ActionSpec(
                    action_type="insert_node_between",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"position": "between"},
                    rationale="The request explicitly inserts a node into an existing path.",
                )
            )
        if any(term in text for term in ("change", "update", "modify")) and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"mode": "bounded_update"},
                    rationale="The request asks for a bounded change to existing structure.",
                )
            )
        if category == "REPAIR_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"repair_mode": "minimal_fix"},
                    rationale="Repair requests need a minimal corrective patch proposal.",
                )
            )
        if category == "OPTIMIZE_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="set_parameter",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"optimization_goal": "cost_or_quality"},
                    rationale="Optimization requests are normalized into bounded parameter changes first.",
                )
            )
        return actions

    def _build_assumptions(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> list[AssumptionSpec]:
        assumptions: list[AssumptionSpec] = []
        if category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"} and context.working_save_ref is None:
            assumptions.append(
                AssumptionSpec(
                    text="The current working draft is the intended mutation target.",
                    severity="medium",
                    user_visible=True,
                )
            )
        if "review" in request_text.casefold():
            assumptions.append(
                AssumptionSpec(
                    text="A human reviewer will be available when the review step is reached.",
                    severity="medium",
                    user_visible=True,
                )
            )
        return assumptions

    def _build_ambiguity_flags(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> list[AmbiguityFlag]:
        flags: list[AmbiguityFlag] = []
        text = request_text.casefold()
        if category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"} and context.working_save_ref is None:
            flags.append(
                AmbiguityFlag(
                    type="target_not_explicit",
                    description="The request does not identify which working save should be mutated.",
                )
            )
        if any(term in text for term in ("all ", "entire", "whole")):
            flags.append(
                AmbiguityFlag(
                    type="broad_scope",
                    description="The request implies broad-scope changes that should be confirmed before commit.",
                )
            )
        return flags

    def _build_risk_flags(self, request_text: str) -> list[RiskFlag]:
        flags: list[RiskFlag] = []
        text = request_text.casefold()
        if any(term in text for term in ("delete", "remove", "destructive")):
            flags.append(
                RiskFlag(
                    type="destructive_edit",
                    severity="high",
                    description="The request includes destructive structural edits.",
                )
            )
        if "provider" in text and any(term in text for term in ("replace", "switch", "change")):
            flags.append(
                RiskFlag(
                    type="provider_change",
                    severity="medium",
                    description="Provider changes may alter output semantics and cost.",
                )
            )
        return flags

    def _build_explanation(self, category: str, scope: TargetScope, ambiguity_flags: list[AmbiguityFlag]) -> str:
        message = f"Normalized request into {category} with target scope mode '{scope.mode}'."
        if ambiguity_flags:
            message += " User confirmation is required before any commit boundary is crossed."
        return message

    def _estimate_confidence(self, ambiguity_flags: list[AmbiguityFlag]) -> float:
        return 0.65 if ambiguity_flags else 0.9

    def _infer_provider_id(self, text: str) -> str:
        if "claude" in text or "anthropic" in text:
            return "anthropic:claude"
        if "gemini" in text or "google" in text:
            return "google:gemini"
        if "perplexity" in text:
            return "perplexity:sonar"
        return "openai:gpt"

    def _infer_plugin_id(self, text: str) -> str:
        if "search" in text:
            return "web.search"
        if "normalize" in text:
            return "text.normalize"
        if "validate" in text:
            return "schema.validate"
        return "tool.generic"

    def _extract_node_refs(self, request_text: str) -> tuple[str, ...]:
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
                ref = match.group(1)
                if ref.casefold() in stopwords:
                    continue
                if ref not in seen:
                    ordered_refs.append(ref)
                    seen.add(ref)
        return tuple(ordered_refs)

    def _first_node_ref(self, request_text: str) -> str | None:
        refs = self._extract_node_refs(request_text)
        return refs[0] if refs else None


def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"
