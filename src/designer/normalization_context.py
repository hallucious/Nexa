from __future__ import annotations

from dataclasses import dataclass

from src.designer.models.designer_session_state_card import DesignerSessionStateCard


@dataclass(frozen=True)
class RequestNormalizationContext:
    working_save_ref: str | None = None
    session_state_card: DesignerSessionStateCard | None = None
