from __future__ import annotations

from typing import Any
import re

from src.designer.control_governance import (
    governance_pending_anchor_applicability_for_request,
    governance_recent_anchor_resolution_applicability_for_request,
    governance_recent_revision_history_applicability_for_request,
    governance_recent_revision_redirect_archive_applicability_for_request,
    governance_recent_revision_replacement_applicability_for_request,
    requires_explicit_referential_anchor,
)
from src.designer.normalization_context import RequestNormalizationContext


class DesignerReferentialResolutionSupport:
    """Referential committed-summary and governance snapshot support.

    This isolates committed-summary reference resolution and governance-driven
    referential snapshot lookup from the compatibility facade.
    """

    def __init__(self, symbolic_grounder: Any) -> None:
        self._symbolic_grounder = symbolic_grounder

    def _explicit_node_refs(self, request_text: str, context: RequestNormalizationContext) -> tuple[str, ...]:
        if hasattr(self._symbolic_grounder, "explicit_node_refs"):
            return self._symbolic_grounder.explicit_node_refs(request_text, context)
        direct_refs = ()
        if hasattr(self._symbolic_grounder, "extract_node_refs") and hasattr(self._symbolic_grounder, "resolve_node_refs"):
            direct_refs = self._symbolic_grounder.resolve_node_refs(self._symbolic_grounder.extract_node_refs(request_text), context)
        if direct_refs:
            return direct_refs
        if hasattr(self._symbolic_grounder, "infer_node_refs_from_context_mentions"):
            return self._symbolic_grounder.infer_node_refs_from_context_mentions(request_text, context)
        return ()

    def _selected_node_refs(self, context: RequestNormalizationContext) -> tuple[str, ...]:
        if hasattr(self._symbolic_grounder, "selected_node_refs"):
            return self._symbolic_grounder.selected_node_refs(context)
        return ()


    def repeated_cycle_referential_anchor_required(
        self,
        request_text: str,
        context: RequestNormalizationContext,
        *,
        resolved_summary: dict[str, Any] | None,
    ) -> bool:
        card = context.session_state_card
        if card is None or resolved_summary is None:
            return False
        if not self.uses_referential_committed_summary_language(request_text):
            return False
        if not requires_explicit_referential_anchor(card.notes):
            return False
        return not self.has_explicit_referential_anchor(request_text, context)

    def has_explicit_referential_anchor(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> bool:
        history = self.committed_summary_history(context)
        if self.match_explicit_commit_reference(request_text, history) is not None:
            return True
        if self.uses_second_latest_reference_language(request_text):
            return True
        explicit_node_refs = self._explicit_node_refs(request_text, context)
        if not explicit_node_refs:
            selected_node_refs = self._selected_node_refs(context)
            if len(selected_node_refs) == 1:
                explicit_node_refs = selected_node_refs
        return bool(explicit_node_refs)

    def recent_revision_history_snapshot_for_request(
        self,
        request_text: str,
        category: str,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        card = context.session_state_card
        if card is None:
            return {}
        applicability = governance_recent_revision_history_applicability_for_request(
            card.notes,
            request_text,
            mutation_oriented=category not in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"},
            available_node_refs=card.current_working_save.node_list or card.target_scope.allowed_node_refs,
        )
        if applicability.is_visible_mutation:
            snapshot = dict(applicability.snapshot or {})
            origin_status = str(card.notes.get("approval_revision_recent_history_origin_status", "")).strip()
            origin_summary = str(card.notes.get("approval_revision_recent_history_origin_summary", "")).strip()
            if not snapshot.get("reopened_from_redirect_archive") and origin_status == "reopened_from_redirect_archive":
                snapshot["reopened_from_redirect_archive"] = True
                snapshot["origin_status"] = origin_status
                snapshot["origin_summary"] = origin_summary
            return snapshot
        redirect_archive_applicability = governance_recent_revision_redirect_archive_applicability_for_request(
            card.notes,
            request_text,
            mutation_oriented=category not in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"},
            available_node_refs=card.current_working_save.node_list or card.target_scope.allowed_node_refs,
        )
        if not redirect_archive_applicability.is_reopen_mutation:
            return {}
        snapshot = redirect_archive_applicability.snapshot or {}
        return {
            "count": int(snapshot.get("count", 0) or 0),
            "summary": (
                "A previously redirected revision thread is explicitly reopened by the current mutation request, "
                "so its older multi-step continuity should be restored."
            ),
            "history": list(snapshot.get("history", [])),
            "latest_selected_interpretation": (
                str(snapshot.get("history", [{}])[-1].get("selected_interpretation", "")).strip()
                if isinstance(snapshot.get("history", []), list) and snapshot.get("history", [])
                else ""
            ),
            "reopened_from_redirect_archive": True,
        }

    def recent_revision_replacement_snapshot_for_request(
        self,
        request_text: str,
        category: str,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        card = context.session_state_card
        if card is None:
            return {}
        applicability = governance_recent_revision_replacement_applicability_for_request(
            card.notes,
            request_text,
            mutation_oriented=category not in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"},
        )
        if not applicability.is_visible_mutation:
            return {}
        return applicability.snapshot or {}

    def recent_revision_redirect_archive_snapshot_for_request(
        self,
        request_text: str,
        category: str,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        card = context.session_state_card
        if card is None:
            return {}
        applicability = governance_recent_revision_redirect_archive_applicability_for_request(
            card.notes,
            request_text,
            mutation_oriented=category not in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"},
            available_node_refs=card.current_working_save.node_list or card.target_scope.allowed_node_refs,
        )
        if not applicability.is_visible_mutation:
            return {}
        return applicability.snapshot or {}

    def pending_anchor_snapshot_for_request(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        card = context.session_state_card
        if card is None:
            return {}
        applicability = governance_pending_anchor_applicability_for_request(
            card.notes,
            request_text,
            available_node_refs=card.current_working_save.node_list or card.target_scope.allowed_node_refs,
            commit_history=tuple(item for item in card.notes.get("commit_summary_history", ()) if isinstance(item, dict)),
        )
        if not applicability.is_unsatisfied:
            return {}
        return applicability.snapshot or {}

    def recent_resolution_snapshot_for_request(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        card = context.session_state_card
        if card is None:
            return {}
        applicability = governance_recent_anchor_resolution_applicability_for_request(
            card.notes,
            request_text,
            available_node_refs=card.current_working_save.node_list or card.target_scope.allowed_node_refs,
            commit_history=tuple(item for item in card.notes.get("commit_summary_history", ()) if isinstance(item, dict)),
        )
        if not applicability.is_visible_referential:
            return {}
        return applicability.snapshot or {}

    def latest_committed_summary(self, context: RequestNormalizationContext) -> dict[str, Any] | None:
        card = context.session_state_card
        if card is None:
            return None
        primary = card.notes.get("committed_summary_primary")
        if isinstance(primary, dict):
            return dict(primary)
        history = self.committed_summary_history(context)
        if history:
            return history[0]
        return None

    def committed_summary_history(self, context: RequestNormalizationContext) -> list[dict[str, Any]]:
        card = context.session_state_card
        if card is None:
            return []
        history = card.notes.get("commit_summary_history")
        if not isinstance(history, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in history:
            if isinstance(item, dict):
                normalized.append(dict(item))
        return normalized

    def uses_referential_committed_summary_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\bprevious change\b",
            r"\blast change\b",
            r"\bprevious commit\b",
            r"\blast commit\b",
            r"\bsame change\b",
            r"\bsame edit\b",
            r"\bthat change\b",
            r"\bthat edit\b",
            r"\brevert\b",
            r"\bundo\b",
            r"\brollback\b",
            r"\broll back\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def resolve_committed_summary_reference(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        if not self.uses_referential_committed_summary_language(request_text):
            return None, None, None
        history = self.committed_summary_history(context)
        latest_summary = self.latest_committed_summary(context)
        if latest_summary is not None and (not history or history[0].get("commit_id") != latest_summary.get("commit_id")):
            history = [latest_summary, *history]
        exact_match = self.match_explicit_commit_reference(request_text, history)
        if exact_match is not None:
            return exact_match, "exact_commit_match", None
        if self.uses_second_latest_reference_language(request_text):
            if len(history) >= 2:
                return history[1], "second_latest_auto", None
            return None, None, "insufficient_history"
        if self.uses_ambiguous_nonlatest_reference_language(request_text):
            if len(history) >= 2:
                return None, None, "clarification_required"
            if len(history) == 1:
                return None, None, "insufficient_history"
            return None, None, "missing"
        if latest_summary is not None:
            return latest_summary, "latest_auto", None
        return None, None, "missing"

    def match_explicit_commit_reference(
        self,
        request_text: str,
        history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        text = request_text.casefold()
        commit_tokens = set(re.findall(r"\b[a-f0-9]{7,40}\b", text))
        if not commit_tokens:
            return None
        for item in history:
            commit_id = item.get("commit_id", "").casefold()
            if any(commit_id.startswith(token) for token in commit_tokens):
                return item
        return None

    def uses_second_latest_reference_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\b(second last|second-latest|before last|prior to last|the one before that) (change|commit|edit)\b",
            r"\b(change|commit|edit) before last\b",
            r"\bcommit before last\b",
            r"\bchange before last\b",
            r"\bthe one before that\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def uses_ambiguous_nonlatest_reference_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\bolder change\b",
            r"\bearlier change\b",
            r"\bolder commit\b",
            r"\bearlier commit\b",
            r"\bnot the last (change|commit|edit)\b",
            r"\bother (change|commit|edit)\b",
            r"\bthat older (change|commit|edit)\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def uses_previous_reference_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\bprevious change\b",
            r"\bprevious commit\b",
            r"\bthat previous change\b",
            r"\bthat previous commit\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def committed_summary_touched_node_ids(
        self,
        summary: dict[str, Any] | None,
        context: RequestNormalizationContext,
    ) -> tuple[str, ...]:
        if summary is None:
            return ()
        raw = summary.get("touched_node_ids")
        if not isinstance(raw, (list, tuple)):
            return ()
        refs = tuple(str(item) for item in raw if str(item).strip())
        return self._symbolic_grounder.resolve_node_refs(refs, context)

    def resolve_target_node_refs_from_committed_summary(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
        explicit_node_refs: tuple[str, ...],
    ) -> tuple[str, ...]:
        if category not in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"}:
            return explicit_node_refs
        summary, _, _ = self.resolve_committed_summary_reference(request_text, context)
        if summary is None:
            return explicit_node_refs
        touched_node_ids = self.committed_summary_touched_node_ids(summary, context)
        if explicit_node_refs:
            return explicit_node_refs
        if len(touched_node_ids) == 1:
            return touched_node_ids
        return explicit_node_refs
