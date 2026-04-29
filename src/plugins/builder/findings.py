from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.plugins.contracts.common_enums import (
    BUILDER_STAGE_INTAKE,
    BUILDER_STAGES,
    FINDING_SEVERITIES,
    FINDING_SEVERITY_BLOCKING,
    FINDING_SEVERITY_INFO,
    FINDING_SEVERITY_WARNING,
    require_known_value,
)
from src.plugins.contracts.serialization import JsonPayloadMixin


@dataclass(frozen=True)
class BuilderFinding(JsonPayloadMixin):
    finding_id: str
    severity: str
    stage: str
    code: str
    message: str
    target_ref: str | None = None
    remediation_hint: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.finding_id, "finding_id")
        require_known_value(self.severity, allowed=FINDING_SEVERITIES, field_name="finding severity")
        require_known_value(self.stage, allowed=BUILDER_STAGES, field_name="builder stage")
        _require_text(self.code, "code")
        _require_text(self.message, "message")

    @property
    def blocking(self) -> bool:
        return self.severity == FINDING_SEVERITY_BLOCKING


def info_finding(*, finding_id: str, code: str, message: str, stage: str = BUILDER_STAGE_INTAKE, target_ref: str | None = None) -> BuilderFinding:
    return BuilderFinding(
        finding_id=finding_id,
        severity=FINDING_SEVERITY_INFO,
        stage=stage,
        code=code,
        message=message,
        target_ref=target_ref,
    )


def warning_finding(*, finding_id: str, code: str, message: str, stage: str = BUILDER_STAGE_INTAKE, target_ref: str | None = None, remediation_hint: str | None = None) -> BuilderFinding:
    return BuilderFinding(
        finding_id=finding_id,
        severity=FINDING_SEVERITY_WARNING,
        stage=stage,
        code=code,
        message=message,
        target_ref=target_ref,
        remediation_hint=remediation_hint,
    )


def blocking_finding(*, finding_id: str, code: str, message: str, stage: str = BUILDER_STAGE_INTAKE, target_ref: str | None = None, remediation_hint: str | None = None) -> BuilderFinding:
    return BuilderFinding(
        finding_id=finding_id,
        severity=FINDING_SEVERITY_BLOCKING,
        stage=stage,
        code=code,
        message=message,
        target_ref=target_ref,
        remediation_hint=remediation_hint,
    )


def split_findings(findings: tuple[BuilderFinding, ...]) -> tuple[tuple[BuilderFinding, ...], tuple[BuilderFinding, ...]]:
    blocking = tuple(item for item in findings if item.blocking)
    warnings = tuple(item for item in findings if item.severity == FINDING_SEVERITY_WARNING)
    return blocking, warnings


def _require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"BuilderFinding.{field_name} must be non-empty")
    return text


__all__ = [
    "BuilderFinding",
    "blocking_finding",
    "info_finding",
    "split_findings",
    "warning_finding",
]
