from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional
import hashlib
import json


DEFAULT_ARTIFACT_SCHEMA_VERSION = "1.0.0"
CANONICAL_ARTIFACT_TYPES = {
    "text",
    "json_object",
    "decision",
    "critique",
    "evidence_set",
    "plan",
    "ranking",
    "score_vector",
    "tool_call_result",
    "validation_report",
    "trace_slice",
    "preview_sample",
}
ALLOWED_VALIDATION_STATUSES = {"unvalidated", "valid", "invalid", "partial"}


class ArtifactContractError(ValueError):
    """Raised when typed artifact contract requirements are violated."""


_ARTIFACT_TYPE_REGISTRY: set[str] = set(CANONICAL_ARTIFACT_TYPES)


def register_artifact_type(artifact_type: str) -> None:
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        raise ArtifactContractError("artifact_type must be non-empty string")
    _ARTIFACT_TYPE_REGISTRY.add(artifact_type.strip())


def registered_artifact_types() -> tuple[str, ...]:
    return tuple(sorted(_ARTIFACT_TYPE_REGISTRY))


def is_registered_artifact_type(artifact_type: str) -> bool:
    return isinstance(artifact_type, str) and artifact_type in _ARTIFACT_TYPE_REGISTRY


def infer_artifact_type(payload: Any) -> str:
    if isinstance(payload, str):
        return "text"
    if isinstance(payload, dict):
        return "json_object"
    if isinstance(payload, (list, tuple)):
        return "json_object"
    return "json_object"



def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)



def _artifact_digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class TypedArtifactEnvelope:
    artifact_id: str
    artifact_type: str
    artifact_schema_version: str
    producer_ref: str
    payload: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    lineage_refs: list[str] = field(default_factory=list)
    trace_refs: list[str] = field(default_factory=list)
    validation_status: str = "unvalidated"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ArtifactContractError("artifact_id must be non-empty")
        if not self.artifact_type:
            raise ArtifactContractError("artifact_type must be non-empty")
        if not is_registered_artifact_type(self.artifact_type):
            raise ArtifactContractError(f"unregistered artifact_type: {self.artifact_type}")
        if not self.artifact_schema_version:
            raise ArtifactContractError("artifact_schema_version must be non-empty")
        if not self.producer_ref:
            raise ArtifactContractError("producer_ref must be non-empty")
        if self.validation_status not in ALLOWED_VALIDATION_STATUSES:
            raise ArtifactContractError(
                f"unsupported validation_status: {self.validation_status}"
            )
        if not isinstance(self.metadata, dict):
            raise ArtifactContractError("metadata must be dict")
        if not isinstance(self.lineage_refs, list) or not all(isinstance(x, str) and x for x in self.lineage_refs):
            raise ArtifactContractError("lineage_refs must be list[str]")
        if not isinstance(self.trace_refs, list) or not all(isinstance(x, str) and x for x in self.trace_refs):
            raise ArtifactContractError("trace_refs must be list[str]")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



def make_typed_artifact(
    *,
    artifact_type: str,
    producer_ref: str,
    payload: Any,
    artifact_schema_version: str = DEFAULT_ARTIFACT_SCHEMA_VERSION,
    metadata: Optional[Dict[str, Any]] = None,
    lineage_refs: Optional[Iterable[str]] = None,
    trace_refs: Optional[Iterable[str]] = None,
    validation_status: str = "unvalidated",
    artifact_id: Optional[str] = None,
) -> TypedArtifactEnvelope:
    normalized_type = artifact_type or infer_artifact_type(payload)
    if artifact_id is None:
        artifact_id = f"artifact::{normalized_type}::{_artifact_digest(payload)}"
    return TypedArtifactEnvelope(
        artifact_id=artifact_id,
        artifact_type=normalized_type,
        artifact_schema_version=artifact_schema_version,
        producer_ref=producer_ref,
        payload=payload,
        metadata=dict(metadata or {}),
        lineage_refs=list(lineage_refs or []),
        trace_refs=list(trace_refs or []),
        validation_status=validation_status,
    )
