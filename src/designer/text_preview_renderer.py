from __future__ import annotations

from src.designer.models.circuit_draft_preview import CircuitDraftPreview


class TextPreviewRenderer:
    def render(self, preview: CircuitDraftPreview) -> str:
        lines: list[str] = []
        lines.append(f"{preview.summary_card.title}")
        lines.append(preview.summary_card.one_sentence_summary)
        lines.append("")
        lines.append("Summary")
        lines.append(f"- proposal_type: {preview.summary_card.proposal_type}")
        lines.append(f"- change_scope: {preview.summary_card.change_scope}")
        lines.append(f"- overall_status: {preview.summary_card.overall_status}")
        lines.append(f"- touched_nodes: {preview.summary_card.touched_node_count}")
        lines.append(f"- touched_edges: {preview.summary_card.touched_edge_count}")
        lines.append(f"- touched_outputs: {preview.summary_card.touched_output_count}")
        lines.append("")
        lines.append("Structural Delta")
        lines.append(f"- {preview.structural_preview.structural_delta_summary}")
        if preview.structural_preview.added_nodes:
            lines.append(f"- added_nodes: {', '.join(preview.structural_preview.added_nodes)}")
        if preview.structural_preview.removed_nodes:
            lines.append(f"- removed_nodes: {', '.join(preview.structural_preview.removed_nodes)}")
        if preview.structural_preview.modified_nodes:
            lines.append(f"- modified_nodes: {', '.join(preview.structural_preview.modified_nodes)}")
        if preview.structural_preview.changed_outputs:
            lines.append(f"- changed_outputs: {', '.join(preview.structural_preview.changed_outputs)}")
        lines.append("")
        lines.append("Node Changes")
        if preview.node_change_preview.cards:
            for card in preview.node_change_preview.cards:
                lines.append(f"- {card.node_ref}: {card.change_type} ({card.criticality})")
                lines.append(f"  why: {card.why_it_changed}")
                lines.append(f"  effect: {card.expected_effect}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Edge Changes")
        if preview.edge_change_preview.cards:
            for card in preview.edge_change_preview.cards:
                lines.append(f"- {card.from_node} -> {card.to_node}: {card.change_type}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Output Changes")
        if preview.output_change_preview.cards:
            for card in preview.output_change_preview.cards:
                lines.append(f"- {card.output_ref}: {card.change_type}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Risk + Confirmation")
        lines.append(f"- risk_summary: {preview.risk_preview.summary}")
        if preview.risk_preview.risks:
            for risk in preview.risk_preview.risks:
                lines.append(f"- risk: {risk}")
        if preview.confirmation_preview.required_confirmations:
            for item in preview.confirmation_preview.required_confirmations:
                lines.append(f"- confirmation_required: {item}")
        else:
            lines.append("- confirmation_required: none")
        lines.append("")
        lines.append("Cost + Behavior")
        lines.append(f"- cost: {preview.cost_preview.cost_summary}")
        if preview.cost_preview.estimated_cost_change is not None:
            lines.append(f"- estimated_cost_change: {preview.cost_preview.estimated_cost_change}")
        lines.append(f"- behavior: {preview.behavior_change_preview.summary}")
        for effect in preview.behavior_change_preview.expected_effects:
            lines.append(f"- expected_effect: {effect}")
        for regression in preview.behavior_change_preview.possible_regressions:
            lines.append(f"- possible_regression: {regression}")
        lines.append("")
        lines.append("Assumptions / Defaults")
        if preview.assumption_preview.assumptions:
            for assumption in preview.assumption_preview.assumptions:
                lines.append(f"- assumption: {assumption}")
        else:
            lines.append("- assumption: none")
        if preview.assumption_preview.default_choices:
            for item in preview.assumption_preview.default_choices:
                lines.append(f"- default: {item}")
        else:
            lines.append("- default: none")
        lines.append("")
        lines.append("Next Action")
        lines.append(f"- {preview.summary_card.user_action_hint}")
        if preview.explanation:
            lines.append("")
            lines.append("Explanation")
            lines.append(f"- {preview.explanation}")
        return "\n".join(lines)
