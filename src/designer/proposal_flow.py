from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any, Mapping

from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.designer_proposal_control import (
    DesignerControlledProposalResult,
    DesignerProposalControlState,
    ProposalControlPolicy,
)
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.designer.patch_builder import CircuitPatchBuilder
from src.designer.precheck_builder import DesignerPrecheckBuilder
from src.designer.preview_builder import DesignerPreviewBuilder
from src.designer.request_normalizer import DesignerRequestNormalizer, RequestNormalizationContext
from src.designer.session_state_card_builder import DesignerSessionStateCardBuilder
from src.designer.text_preview_renderer import TextPreviewRenderer


@dataclass(frozen=True)
class DesignerProposalBundle:
    request_text: str
    target_working_save_ref: str | None
    session_state_card: DesignerSessionStateCard
    intent: DesignerIntent
    patch: CircuitPatchPlan
    precheck: ValidationPrecheck
    preview: CircuitDraftPreview
    rendered_preview: str

    @property
    def can_proceed_to_preview(self) -> bool:
        return self.precheck.can_proceed_to_preview


@dataclass(frozen=True)
class StarterCircuitTemplateSpec:
    template_id: str
    display_name: str
    category: str
    summary: str
    designer_request_text: str


_STARTER_CIRCUIT_TEMPLATES: tuple[StarterCircuitTemplateSpec, ...] = (
    StarterCircuitTemplateSpec(
        template_id="text_summarizer",
        display_name="Text Summarizer",
        category="summarization",
        summary="Summarize pasted text into a short structured brief.",
        designer_request_text="Create a workflow that takes pasted text, summarizes the key points, and returns a short readable summary.",
    ),
    StarterCircuitTemplateSpec(
        template_id="review_classifier",
        display_name="Review Classifier",
        category="classification",
        summary="Classify customer reviews by sentiment and key issues.",
        designer_request_text="Create a workflow that reads customer reviews, classifies sentiment, and extracts the main issue categories.",
    ),
    StarterCircuitTemplateSpec(
        template_id="document_analyzer",
        display_name="Document Analyzer",
        category="document_analysis",
        summary="Read a document and produce a clear analysis summary.",
        designer_request_text="Create a workflow that analyzes an uploaded document, identifies the important sections, and explains the main points clearly.",
    ),
    StarterCircuitTemplateSpec(
        template_id="email_drafter",
        display_name="Email Drafter",
        category="writing",
        summary="Draft a professional email from a goal and key details.",
        designer_request_text="Create a workflow that takes a goal and key details, then drafts a professional email the user can review and send.",
    ),
    StarterCircuitTemplateSpec(
        template_id="code_reviewer",
        display_name="Code Reviewer",
        category="code",
        summary="Review code and explain issues, risks, and improvements.",
        designer_request_text="Create a workflow that reviews pasted code, explains problems or risks, and suggests concrete improvements.",
    ),
    StarterCircuitTemplateSpec(
        template_id="news_briefer",
        display_name="News Briefer",
        category="summarization",
        summary="Turn multiple news items into a concise daily brief.",
        designer_request_text="Create a workflow that takes several news items and turns them into a concise daily briefing with the main takeaways.",
    ),
    StarterCircuitTemplateSpec(
        template_id="qa_responder",
        display_name="Q&A Responder",
        category="writing",
        summary="Answer a question clearly using the provided context.",
        designer_request_text="Create a workflow that accepts a question and supporting context, then produces a clear and direct answer for the user.",
    ),
    StarterCircuitTemplateSpec(
        template_id="data_extractor",
        display_name="Data Extractor",
        category="classification",
        summary="Extract key fields from semi-structured text.",
        designer_request_text="Create a workflow that reads semi-structured text and extracts the important fields into a clean structured output.",
    ),
    StarterCircuitTemplateSpec(
        template_id="translation_helper",
        display_name="Translation Helper",
        category="writing",
        summary="Translate text while preserving tone and intent.",
        designer_request_text="Create a workflow that translates text into the target language while preserving the original tone and intent.",
    ),
    StarterCircuitTemplateSpec(
        template_id="content_rewriter",
        display_name="Content Rewriter",
        category="writing",
        summary="Rewrite text for clarity, tone, and readability.",
        designer_request_text="Create a workflow that rewrites text to improve clarity, tone, and readability while preserving meaning.",
    ),
)


def list_starter_circuit_templates() -> tuple[StarterCircuitTemplateSpec, ...]:
    return _STARTER_CIRCUIT_TEMPLATES


def get_starter_circuit_template(template_id: str) -> StarterCircuitTemplateSpec:
    for template in _STARTER_CIRCUIT_TEMPLATES:
        if template.template_id == template_id:
            return template
    raise KeyError(f"unknown starter template: {template_id}")


def _call_normalizer_with_optional_session_keys(
    normalizer: Any,
    request_text: str,
    *,
    context: RequestNormalizationContext,
    semantic_backend_session_key: str | None,
    semantic_backend_session_keys: Mapping[str, str] | None,
) -> DesignerIntent:
    """Call normalize() without breaking older test doubles or consumers.

    Some existing normalizer stubs only accept `(request_text, *, context=...)`.
    The Phase 4 session-key wiring adds optional keyword arguments, but proposal
    flow must remain backward-compatible with older doubles and legacy callers.
    """

    normalize = normalizer.normalize
    try:
        parameters = inspect.signature(normalize).parameters
    except (TypeError, ValueError):
        parameters = {}

    kwargs: dict[str, Any] = {"context": context}
    if "semantic_backend_session_key" in parameters:
        kwargs["semantic_backend_session_key"] = semantic_backend_session_key
    if "semantic_backend_session_keys" in parameters:
        kwargs["semantic_backend_session_keys"] = semantic_backend_session_keys
    return normalize(request_text, **kwargs)


def _session_keys_from_session_state_card(session_state_card: DesignerSessionStateCard | None) -> dict[str, str]:
    if session_state_card is None or not isinstance(session_state_card.notes, dict):
        return {}
    raw = session_state_card.notes.get("provider_session_keys")
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, str] = {}
    for preset, key in raw.items():
        if isinstance(preset, str) and isinstance(key, str) and key.strip():
            result[preset] = key.strip()
    return result


class DesignerProposalFlow:
    def __init__(
        self,
        *,
        normalizer: DesignerRequestNormalizer | None = None,
        patch_builder: CircuitPatchBuilder | None = None,
        precheck_builder: DesignerPrecheckBuilder | None = None,
        preview_builder: DesignerPreviewBuilder | None = None,
        renderer: TextPreviewRenderer | None = None,
        session_state_card_builder: DesignerSessionStateCardBuilder | None = None,
    ) -> None:
        self._normalizer = normalizer or DesignerRequestNormalizer()
        self._patch_builder = patch_builder or CircuitPatchBuilder()
        self._precheck_builder = precheck_builder or DesignerPrecheckBuilder()
        self._preview_builder = preview_builder or DesignerPreviewBuilder()
        self._renderer = renderer or TextPreviewRenderer()
        self._session_state_card_builder = session_state_card_builder or DesignerSessionStateCardBuilder()

    def propose(
        self,
        request_text: str,
        *,
        working_save_ref: str | None = None,
        session_state_card: DesignerSessionStateCard | None = None,
        semantic_backend_session_key: str | None = None,
        semantic_backend_session_keys: Mapping[str, str] | None = None,
    ) -> DesignerProposalBundle:
        session_state_card = session_state_card or self._session_state_card_builder.build(
            request_text=request_text,
            artifact=None,
            session_id=None,
            target_scope_mode="existing_circuit" if working_save_ref else "new_circuit",
        )
        context = RequestNormalizationContext(working_save_ref=working_save_ref, session_state_card=session_state_card)
        effective_session_keys = dict(_session_keys_from_session_state_card(session_state_card))
        if semantic_backend_session_keys:
            for preset, key in semantic_backend_session_keys.items():
                if isinstance(preset, str) and isinstance(key, str) and key.strip():
                    effective_session_keys[preset] = key.strip()
        intent = _call_normalizer_with_optional_session_keys(
            self._normalizer,
            request_text,
            context=context,
            semantic_backend_session_key=semantic_backend_session_key,
            semantic_backend_session_keys=effective_session_keys or None,
        )
        if intent.category in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"}:
            raise ValueError("Step 2 proposal flow only supports mutation-oriented designer requests")
        patch = self._patch_builder.build(intent)
        precheck = self._build_precheck(intent, patch, session_state_card=session_state_card)
        preview = self._build_preview(intent, patch, precheck, session_state_card=session_state_card)
        rendered_preview = self._renderer.render(preview)
        return DesignerProposalBundle(
            request_text=request_text.strip(),
            target_working_save_ref=working_save_ref,
            session_state_card=session_state_card,
            intent=intent,
            patch=patch,
            precheck=precheck,
            preview=preview,
            rendered_preview=rendered_preview,
        )

    def _build_precheck(
        self,
        intent: DesignerIntent,
        patch: CircuitPatchPlan,
        *,
        session_state_card: DesignerSessionStateCard,
    ) -> ValidationPrecheck:
        try:
            return self._precheck_builder.build(intent, patch, session_state_card=session_state_card)
        except TypeError as exc:
            if "session_state_card" not in str(exc):
                raise
            return self._precheck_builder.build(intent, patch)

    def _build_preview(
        self,
        intent: DesignerIntent,
        patch: CircuitPatchPlan,
        precheck: ValidationPrecheck,
        *,
        session_state_card: DesignerSessionStateCard,
    ) -> CircuitDraftPreview:
        try:
            return self._preview_builder.build(intent, patch, precheck, session_state_card=session_state_card)
        except TypeError as exc:
            if "session_state_card" not in str(exc):
                raise
            return self._preview_builder.build(intent, patch, precheck)

    def propose_with_control(
        self,
        request_text: str,
        *,
        working_save_ref: str | None = None,
        session_state_card: DesignerSessionStateCard | None = None,
        control_state: DesignerProposalControlState | None = None,
        control_policy: ProposalControlPolicy | None = None,
        semantic_backend_session_key: str | None = None,
        semantic_backend_session_keys: Mapping[str, str] | None = None,
    ) -> DesignerControlledProposalResult:
        from src.designer.proposal_control import DesignerProposalControlPlane

        controller = DesignerProposalControlPlane(proposal_flow=self)
        return controller.run(
            request_text,
            working_save_ref=working_save_ref,
            session_state_card=session_state_card,
            control_state=control_state,
            control_policy=control_policy,
            semantic_backend_session_key=semantic_backend_session_key,
            semantic_backend_session_keys=semantic_backend_session_keys,
        )



__all__ = [
    "StarterCircuitTemplateSpec",
    "list_starter_circuit_templates",
    "get_starter_circuit_template",
    "DesignerProposalBundle",
    "DesignerProposalFlow",
]
