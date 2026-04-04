from __future__ import annotations

from dataclasses import dataclass

from src.designer.models.circuit_draft_preview import CircuitDraftPreview
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
    ) -> DesignerProposalBundle:
        session_state_card = session_state_card or self._session_state_card_builder.build(
            request_text=request_text,
            artifact=None,
            session_id=None,
            target_scope_mode="existing_circuit" if working_save_ref else "new_circuit",
        )
        context = RequestNormalizationContext(working_save_ref=working_save_ref, session_state_card=session_state_card)
        intent = self._normalizer.normalize(request_text, context=context)
        if intent.category in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"}:
            raise ValueError("Step 2 proposal flow only supports mutation-oriented designer requests")
        patch = self._patch_builder.build(intent)
        precheck = self._precheck_builder.build(intent, patch)
        preview = self._preview_builder.build(intent, patch, precheck)
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
