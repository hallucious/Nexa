"""
text_extractor.py

Deterministic extractor for converting raw text into a Representation made of
ComparableUnit records.

Current scope:
- heading-aware text extraction for markdown-like text
- headings beginning with "## " or "### " create section units
- no-heading input falls back to a single section unit
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

from src.engine.representation_model import ComparableUnit, Representation


_HEADING_PATTERN = re.compile(r"^(##|###)\s+(?P<heading>.+?)\s*$")
_CANONICAL_LABEL_PATTERN = re.compile(r"^[^A-Za-z0-9]*([A-Za-z0-9]+)")


def _build_representation_id(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"text:{digest}"


def _normalize_heading(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip())


def _canonical_label_from_heading(heading: Optional[str]) -> Optional[str]:
    if heading is None:
        return None
    normalized = _normalize_heading(heading)
    match = _CANONICAL_LABEL_PATTERN.match(normalized)
    if match is None:
        return None
    return match.group(1).lower()


def _make_unit(
    *,
    index: int,
    heading: Optional[str],
    lines: list[str],
) -> ComparableUnit:
    normalized_heading = _normalize_heading(heading) if heading is not None else None
    payload = "\n".join(lines).strip()
    return ComparableUnit(
        unit_id=str(index),
        unit_kind="section",
        canonical_label=_canonical_label_from_heading(normalized_heading),
        payload=payload,
        metadata={
            "heading": normalized_heading,
            "position": index,
        },
    )


def extract_text_representation(text: str) -> Representation:
    """Convert raw text into a deterministic Representation.

    Rules:
    - lines beginning with "## " or "### " start a new section
    - each section becomes one ComparableUnit
    - if no section heading exists, the full text becomes one section unit
    """

    lines = text.splitlines()
    units: list[ComparableUnit] = []

    current_heading: Optional[str] = None
    current_lines: list[str] = []
    saw_heading = False

    for line in lines:
        heading_match = _HEADING_PATTERN.match(line)
        if heading_match is not None:
            saw_heading = True
            if current_heading is not None:
                units.append(
                    _make_unit(
                        index=len(units),
                        heading=current_heading,
                        lines=current_lines,
                    )
                )
            current_heading = heading_match.group("heading")
            current_lines = [line]
            continue

        if current_heading is not None:
            current_lines.append(line)
        else:
            current_lines.append(line)

    if saw_heading and current_heading is not None:
        units.append(
            _make_unit(
                index=len(units),
                heading=current_heading,
                lines=current_lines,
            )
        )
    elif not saw_heading:
        units.append(
            _make_unit(
                index=0,
                heading=None,
                lines=lines,
            )
        )

    return Representation(
        representation_id=_build_representation_id(text),
        artifact_type="text",
        units=units,
        metadata={
            "unit_count": len(units),
            "heading_mode": saw_heading,
        },
    )
