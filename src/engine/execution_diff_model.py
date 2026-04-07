"""
execution_diff_model.py

Data model for Execution Diff results between two Nexa circuit runs.

This module defines serializer-friendly structures for representing
differences between two execution runs:

    RunDiff
    NodeDiff
    ArtifactDiff
    TraceDiff
    ContextDiff
    DiffSummary

IMPORTANT: This module is a DATA MODEL ONLY.
It does not implement diff calculation logic.
It has no dependency on the runtime engine, scheduler, or provider modules.

Design constraints:
- All models are dataclasses with dict/JSON serialization support.
- Artifact philosophy is append-only; diff structures reflect this by
  recording artifact presence and hash changes, never mutations.
- context_key fields follow the Working Context Key Schema Contract:
  <domain>.<resource-id>.<field>
- No pipeline concepts are introduced.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Allowed value constants
# ---------------------------------------------------------------------------

# RunDiff.status
RUN_DIFF_STATUS_IDENTICAL = "identical"
RUN_DIFF_STATUS_CHANGED = "changed"
RUN_DIFF_STATUS_INCOMPLETE = "incomplete"

VALID_RUN_DIFF_STATUSES = frozenset({
    RUN_DIFF_STATUS_IDENTICAL,
    RUN_DIFF_STATUS_CHANGED,
    RUN_DIFF_STATUS_INCOMPLETE,
})

# NodeDiff.change_type, ArtifactDiff.change_type, ContextDiff.change_type
CHANGE_TYPE_ADDED = "added"
CHANGE_TYPE_REMOVED = "removed"
CHANGE_TYPE_MODIFIED = "modified"
CHANGE_TYPE_UNCHANGED = "unchanged"

VALID_CHANGE_TYPES = frozenset({
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_REMOVED,
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_UNCHANGED,
})


# ---------------------------------------------------------------------------
# DiffSummary
# ---------------------------------------------------------------------------

@dataclass
class DiffSummary:
    """Aggregated counts summarising the diff between two runs."""

    nodes_added: int = 0
    nodes_removed: int = 0
    nodes_changed: int = 0

    artifacts_added: int = 0
    artifacts_removed: int = 0
    artifacts_changed: int = 0

    trace_keys_changed: int = 0
    context_keys_changed: int = 0
    verification_changes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# NodeDiff
# ---------------------------------------------------------------------------

@dataclass
class NodeDiff:
    """Records how a single node changed between two runs."""

    node_id: str
    change_type: str  # "added" | "removed" | "modified" | "unchanged"

    left_status: Optional[str] = None
    right_status: Optional[str] = None

    left_output_ref: Optional[str] = None
    right_output_ref: Optional[str] = None

    artifact_ids_added: List[str] = field(default_factory=list)
    artifact_ids_removed: List[str] = field(default_factory=list)
    artifact_ids_changed: List[str] = field(default_factory=list)

    left_verifier_status: Optional[str] = None
    right_verifier_status: Optional[str] = None
    left_verifier_reason_codes: List[str] = field(default_factory=list)
    right_verifier_reason_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# ArtifactDiff
# ---------------------------------------------------------------------------

@dataclass
class ArtifactDiff:
    """Records how a single artifact changed between two runs.

    Reflects append-only artifact philosophy: artifacts are never mutated;
    differences are expressed as hash and kind changes between runs.
    """

    artifact_id: str
    change_type: str  # "added" | "removed" | "modified" | "unchanged"

    left_hash: Optional[str] = None
    right_hash: Optional[str] = None

    left_kind: Optional[str] = None
    right_kind: Optional[str] = None
    left_validation_status: Optional[str] = None
    right_validation_status: Optional[str] = None
    left_validation_reason_codes: List[str] = field(default_factory=list)
    right_validation_reason_codes: List[str] = field(default_factory=list)
    left_artifact_schema_version: Optional[str] = None
    right_artifact_schema_version: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# TraceDiff
# ---------------------------------------------------------------------------

@dataclass
class TraceDiff:
    """Records a change in a trace value between two runs.

    scope examples: "node", "provider", "plugin"
    key: the trace field identifier within the scope
    """

    scope: str
    key: str
    change_type: str

    left_value: Any = None
    right_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)




# ---------------------------------------------------------------------------
# VerificationDiff
# ---------------------------------------------------------------------------

@dataclass
class VerificationDiff:
    """Records verifier-aware changes between two runs."""

    target_type: str
    target_id: str
    change_type: str

    left_value: Any = None
    right_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# ContextDiff
# ---------------------------------------------------------------------------

@dataclass
class ContextDiff:
    """Records a change in a Working Context key value between two runs.

    context_key must follow the Working Context Key Schema Contract:
        input.<field>, output.<field>, or <context-domain>.<resource-id>.<field>
    e.g. "input.text", "provider.openai.output", "plugin.rank.score"
    """

    context_key: str
    change_type: str

    left_value: Any = None
    right_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# RunDiff
# ---------------------------------------------------------------------------

@dataclass
class RunDiff:
    """Top-level data model representing the diff between two execution runs.

    status:
        "identical"  — runs produced identical artifacts and context
        "changed"    — at least one node, artifact, trace, or context key differs
        "incomplete" — one or both runs did not complete successfully
    """

    left_run_id: str
    right_run_id: str
    status: str  # "identical" | "changed" | "incomplete"

    node_diffs: List[NodeDiff] = field(default_factory=list)
    artifact_diffs: List[ArtifactDiff] = field(default_factory=list)
    trace_diffs: List[TraceDiff] = field(default_factory=list)
    context_diffs: List[ContextDiff] = field(default_factory=list)
    verification_diffs: List[VerificationDiff] = field(default_factory=list)
    summary: DiffSummary = field(default_factory=DiffSummary)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
