from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class ExtractedTextArtifact:
    artifact_ref: str
    workspace_id: str
    extraction_id: str
    text: str
    content_hash: str
    created_at: Optional[str] = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.artifact_ref or "").strip():
            raise ValueError("ExtractedTextArtifact.artifact_ref must be non-empty")
        if not str(self.workspace_id or "").strip():
            raise ValueError("ExtractedTextArtifact.workspace_id must be non-empty")
        if not str(self.extraction_id or "").strip():
            raise ValueError("ExtractedTextArtifact.extraction_id must be non-empty")


class InMemoryExtractedTextArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, ExtractedTextArtifact] = {}

    def write_text_artifact(
        self,
        *,
        workspace_id: str,
        extraction_id: str,
        text: str,
        content_hash: str,
        metadata: Mapping[str, object] | None = None,
        artifact_ref: str | None = None,
        created_at: str | None = None,
    ) -> ExtractedTextArtifact:
        ref = artifact_ref or f"extracted-text://{workspace_id}/{extraction_id}"
        artifact = ExtractedTextArtifact(
            artifact_ref=ref,
            workspace_id=workspace_id,
            extraction_id=extraction_id,
            text=text,
            content_hash=content_hash,
            created_at=created_at,
            metadata=dict(metadata or {}),
        )
        self._artifacts[ref] = artifact
        return artifact

    def get_text_artifact(self, artifact_ref: str) -> ExtractedTextArtifact | None:
        return self._artifacts.get(str(artifact_ref or "").strip())
