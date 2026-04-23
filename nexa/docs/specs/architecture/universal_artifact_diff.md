TITLE: Universal Artifact Diff Architecture
VERSION: 1.0.0
LOCATION: docs/specs/architecture/universal_artifact_diff.md

# 1. Purpose

Define a media-agnostic architecture for comparing ANY artifact type within Nexa.

This specification establishes a universal comparison model that:
- supports all current media types (text, image, video, audio, code, etc.)
- supports unknown future media without requiring core engine redesign
- enforces strict separation of extraction, alignment, comparison, and rendering
- guarantees deterministic and reproducible diff behavior

---

# 2. Core Principle

All comparisons MUST follow the pipeline:

Artifact
→ Representation
→ ComparableUnit[]
→ Alignment
→ DiffResult
→ Formatter

Direct raw artifact comparison is STRICTLY PROHIBITED.

---

# 3. Core Entities

## 3.1 Artifact

Definition:
A raw output produced by a node.

Structure:

Artifact {
    artifact_id: str
    artifact_type: str
    raw_content: Any
    metadata: dict
}

---

## 3.2 Representation

Definition:
A structured, comparison-ready transformation of an Artifact.

Rules:
- MUST be deterministic
- MUST be reproducible
- MUST NOT depend on formatter behavior

Structure:

Representation {
    representation_id: str
    artifact_type: str
    units: List[ComparableUnit]
    metadata: dict
}

---

## 3.3 ComparableUnit (CORE ABSTRACTION)

Definition:
The smallest comparable building block across ALL media types.

Structure:

ComparableUnit {
    unit_id: str
    unit_kind: str
    canonical_label: str | None
    payload: Any
    metadata: dict
}

Rules:
- unit_kind MUST be extensible
- canonical_label SHOULD be normalized when possible
- payload MAY contain raw content, embeddings, or structured data

---

# 4. Extractor Layer (Media Adapter)

## 4.1 Definition

Transforms Artifact → Representation

Interface:

extract_representation(artifact: Artifact) -> Representation

---

## 4.2 Rules

- MUST be deterministic
- MUST NOT perform comparison logic
- MUST produce ComparableUnit list
- MUST be isolated per media type

---

## 4.3 Examples (Non-exhaustive)

Text → section / paragraph  
Video → scene / shot / time_block  
Audio → segment / phrase  
Code → function / class / block  
Image → region / object_group  
Table → row_group / column_block  

---

# 5. Alignment Layer

## 5.1 Definition

Matches ComparableUnits between A and B.

Interface:

align_units(
    units_a: List[ComparableUnit],
    units_b: List[ComparableUnit]
) -> AlignmentResult

---

## 5.2 AlignmentResult

AlignmentResult {
    matched_pairs: List[(unit_a, unit_b)]
    added_units: List[unit_b]
    removed_units: List[unit_a]
    unmatched_pairs: List[(unit_a, unit_b)]
}

---

## 5.3 Strategy Priority

1. canonical_label match
2. structural position
3. metadata similarity
4. optional content similarity (plugin-based)

---

# 6. Comparison Layer

## 6.1 Definition

Compares aligned units.

Interface:

compare_units(alignment: AlignmentResult) -> DiffResult

---

## 6.2 DiffResult

DiffResult {
    unit_diffs: List[UnitDiff]
    summary: dict
    metrics: dict
}

---

## 6.3 UnitDiff

UnitDiff {
    unit_kind: str
    label: str | None
    status: str  # added | removed | changed | unchanged
    delta: Any
    metadata: dict
}

---

# 7. Formatter Layer

## 7.1 Definition

Converts DiffResult into output formats.

Interface:

render(diff: DiffResult, format: str) -> str | dict

---

## 7.2 Rules

- MUST NOT generate semantic meaning
- MUST NOT perform comparison logic
- MUST only present DiffResult

---

# 8. Media-Agnostic Guarantee

The system MUST ensure:

- New media support requires ONLY extractor implementation
- No modification to:
  - alignment engine
  - comparison engine
  - formatter core

---

# 9. Determinism Requirements

- Same input → same Representation
- Same Representation → same DiffResult
- No randomness allowed

---

# 10. Extension Points

- Extractor plugins
- Alignment plugins
- Comparator plugins
- Formatter plugins

---

# 11. Refactoring Requirement

Existing logic:

text → line diff → section summary

MUST be replaced with:

text → Representation → ComparableUnit → Alignment → Diff → Formatter

---

# 12. Non-Negotiable Rules

1. Raw string diff MUST NOT be the primary comparison
2. Formatter MUST remain output-only
3. ComparableUnit is the universal abstraction layer
4. Extractor defines media semantics
5. Core engine MUST remain media-agnostic
6. Unknown future media MUST be supported without redesign

---

# 13. Immediate Next Step

Implement:

- ComparableUnit model
- text extractor based on Representation

This replaces:
- _extract_sections()
- section-summary string logic

---

# Final Statement

Nexa is defined as:

"Universal Artifact Diff Engine"

NOT:

"Text Diff Tool"