from __future__ import annotations

from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.text_preview_renderer import TextPreviewRenderer


def test_text_preview_renderer_outputs_required_sections_in_order() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    renderer = TextPreviewRenderer()
    rendered = renderer.render(bundle.preview)
    order = [
        "Summary",
        "Structural Delta",
        "Node Changes",
        "Edge Changes",
        "Output Changes",
        "Risk + Confirmation",
        "Cost + Behavior",
        "Assumptions / Defaults",
        "Next Action",
    ]
    positions = [rendered.index(section) for section in order]
    assert positions == sorted(positions)


def test_text_preview_renderer_surfaces_confirmation_items() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Delete node judge from the whole circuit", working_save_ref="ws-001")
    rendered = bundle.rendered_preview
    assert "confirmation_required" in rendered
    assert "destructive" in rendered.casefold() or "confirm" in rendered.casefold()
