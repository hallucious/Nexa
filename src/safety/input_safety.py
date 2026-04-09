from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import re
import uuid

from src.automation.trigger_model import DEFAULT_TRIGGER_SOURCE, normalize_trigger_source


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


_CREDENTIAL_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9]{8,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{10,}\b"),
    re.compile(r"\b(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?", re.IGNORECASE),
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_CONFIDENTIAL_PATTERN = re.compile(r"\b(confidential|internal only|do not share|nda)\b", re.IGNORECASE)
_UNSAFE_AUTOMATION_PATTERN = re.compile(r"\b(webhook|curl\s+https?://|Authorization:\s*Bearer|automation payload)\b", re.IGNORECASE)


@dataclass(frozen=True)
class InputItem:
    input_ref: str
    content: str
    input_type: str = 'text'
    source_kind: str = 'user'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'input_ref': self.input_ref,
            'content': self.content,
            'input_type': self.input_type,
            'source_kind': self.source_kind,
        }


@dataclass(frozen=True)
class InputSafetyClassification:
    classification_id: str
    input_ref: str
    input_type: str
    source_kind: str
    category_hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'classification_id': self.classification_id,
            'input_ref': self.input_ref,
            'input_type': self.input_type,
            'source_kind': self.source_kind,
            'category_hints': list(self.category_hints),
        }


@dataclass(frozen=True)
class InputSafetyFinding:
    finding_id: str
    input_ref: str
    severity: str
    category: str
    reason_code: str
    human_summary: str
    suggested_next_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'finding_id': self.finding_id,
            'input_ref': self.input_ref,
            'severity': self.severity,
            'category': self.category,
            'reason_code': self.reason_code,
            'human_summary': self.human_summary,
            'suggested_next_action': self.suggested_next_action,
        }


@dataclass(frozen=True)
class InputSafetyDecision:
    decision_id: str
    input_ref: str
    overall_status: str
    finding_refs: List[str]
    confirmation_required: bool
    provider_restrictions: Optional[List[Dict[str, Any]]]
    launch_allowed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision_id': self.decision_id,
            'input_ref': self.input_ref,
            'overall_status': self.overall_status,
            'finding_refs': list(self.finding_refs),
            'confirmation_required': self.confirmation_required,
            'provider_restrictions': list(self.provider_restrictions or []),
            'launch_allowed': self.launch_allowed,
        }


@dataclass(frozen=True)
class InputSafetyConfirmationBoundary:
    boundary_id: str
    decision_ref: str
    requires_user_confirmation: bool
    confirmation_basis: List[str]
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'boundary_id': self.boundary_id,
            'decision_ref': self.decision_ref,
            'requires_user_confirmation': self.requires_user_confirmation,
            'confirmation_basis': list(self.confirmation_basis),
            'confirmed_by': self.confirmed_by,
            'confirmed_at': self.confirmed_at,
        }


@dataclass(frozen=True)
class InputSafetyRecord:
    input_ref: str
    classification_ref: str
    decision_ref: str
    finding_refs: List[str]
    final_status: str
    recorded_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'input_ref': self.input_ref,
            'classification_ref': self.classification_ref,
            'decision_ref': self.decision_ref,
            'finding_refs': list(self.finding_refs),
            'final_status': self.final_status,
            'recorded_at': self.recorded_at,
        }


def _coerce_input_items(raw_inputs: Sequence[Any]) -> List[InputItem]:
    items: List[InputItem] = []
    for index, raw in enumerate(raw_inputs):
        if isinstance(raw, InputItem):
            items.append(raw)
            continue
        if isinstance(raw, dict):
            input_ref = str(raw.get('input_ref') or f'input.{index}')
            content = str(raw.get('content') or '')
            items.append(
                InputItem(
                    input_ref=input_ref,
                    content=content,
                    input_type=str(raw.get('input_type') or 'text'),
                    source_kind=str(raw.get('source_kind') or 'user'),
                )
            )
            continue
        items.append(InputItem(input_ref=f'input.{index}', content=str(raw), input_type='text', source_kind='user'))
    return items


def _classify_item(item: InputItem) -> Tuple[InputSafetyClassification, List[InputSafetyFinding]]:
    findings: List[InputSafetyFinding] = []
    hints: List[str] = []
    text = item.content or ''

    if any(pattern.search(text) for pattern in _CREDENTIAL_PATTERNS):
        hints.append('credential_exposure')
        findings.append(
            InputSafetyFinding(
                finding_id=str(uuid.uuid4()),
                input_ref=item.input_ref,
                severity='blocking',
                category='credential_exposure',
                reason_code='INPUT_CREDENTIAL_EXPOSURE',
                human_summary='Input appears to contain a credential or API secret.',
                suggested_next_action='Remove the secret before launch.',
            )
        )

    if _EMAIL_PATTERN.search(text):
        hints.append('personal_data')
        findings.append(
            InputSafetyFinding(
                finding_id=str(uuid.uuid4()),
                input_ref=item.input_ref,
                severity='warning',
                category='personal_data',
                reason_code='INPUT_PERSONAL_DATA_DETECTED',
                human_summary='Input appears to contain personal contact information.',
                suggested_next_action='Confirm that sharing this data with providers is intended.',
            )
        )

    if _CONFIDENTIAL_PATTERN.search(text):
        hints.append('confidential_data')
        findings.append(
            InputSafetyFinding(
                finding_id=str(uuid.uuid4()),
                input_ref=item.input_ref,
                severity='warning',
                category='confidential_data',
                reason_code='INPUT_CONFIDENTIAL_DATA_HINT',
                human_summary='Input is marked as confidential or internal-only.',
                suggested_next_action='Confirm that this content may leave the workspace.',
            )
        )

    if _UNSAFE_AUTOMATION_PATTERN.search(text):
        hints.append('unsafe_automation_input')
        findings.append(
            InputSafetyFinding(
                finding_id=str(uuid.uuid4()),
                input_ref=item.input_ref,
                severity='warning',
                category='unsafe_automation_input',
                reason_code='INPUT_AUTOMATION_SENSITIVE_CONTENT',
                human_summary='Input looks sensitive for unattended automation or external delivery.',
                suggested_next_action='Require explicit confirmation before unattended launch.',
            )
        )

    if not findings and item.input_type in {'file', 'url'}:
        hints.append('unknown_risk')
        findings.append(
            InputSafetyFinding(
                finding_id=str(uuid.uuid4()),
                input_ref=item.input_ref,
                severity='info',
                category='unknown_risk',
                reason_code='INPUT_EXTERNAL_SOURCE_REVIEW_RECOMMENDED',
                human_summary='External file or URL input should be reviewed before provider submission.',
                suggested_next_action='Review the external source and confirm it is expected.',
            )
        )

    classification = InputSafetyClassification(
        classification_id=str(uuid.uuid4()),
        input_ref=item.input_ref,
        input_type=item.input_type,
        source_kind=item.source_kind,
        category_hints=hints,
    )
    return classification, findings


def evaluate_input_safety(
    raw_inputs: Sequence[Any],
    *,
    trigger_source: str = DEFAULT_TRIGGER_SOURCE,
    confirmed_by: Optional[str] = None,
    confirmed_at: Optional[str] = None,
) -> Dict[str, Any]:
    items = _coerce_input_items(raw_inputs)
    classifications: List[InputSafetyClassification] = []
    findings: List[InputSafetyFinding] = []
    for item in items:
        classification, item_findings = _classify_item(item)
        classifications.append(classification)
        findings.extend(item_findings)

    normalized_trigger = normalize_trigger_source(trigger_source)
    finding_refs = [finding.finding_id for finding in findings]
    has_blocking = any(finding.severity == 'blocking' for finding in findings)
    has_warning = any(finding.severity == 'warning' for finding in findings)

    confirmation_basis = [finding.reason_code for finding in findings if finding.category in {'personal_data', 'confidential_data', 'unsafe_automation_input'}]
    requires_confirmation = bool(confirmation_basis)
    confirmation_explicit = bool(confirmed_by)

    if has_blocking:
        overall_status = 'blocked'
        launch_allowed = False
    elif requires_confirmation and not confirmation_explicit:
        if normalized_trigger == DEFAULT_TRIGGER_SOURCE:
            overall_status = 'confirmation_required'
        else:
            overall_status = 'blocked'
        launch_allowed = False
    elif has_warning or confirmation_explicit:
        overall_status = 'allow_with_warning'
        launch_allowed = True
    else:
        overall_status = 'allow'
        launch_allowed = True

    decision = InputSafetyDecision(
        decision_id=str(uuid.uuid4()),
        input_ref='launch_inputs',
        overall_status=overall_status,
        finding_refs=finding_refs,
        confirmation_required=requires_confirmation and not confirmation_explicit,
        provider_restrictions=None,
        launch_allowed=launch_allowed,
    )
    boundary = InputSafetyConfirmationBoundary(
        boundary_id=str(uuid.uuid4()),
        decision_ref=decision.decision_id,
        requires_user_confirmation=requires_confirmation,
        confirmation_basis=confirmation_basis,
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
    )
    records = [
        build_input_safety_record(
            classification=classification,
            decision=decision,
            finding_refs=[finding.finding_id for finding in findings if finding.input_ref == classification.input_ref],
            confirmation_boundary=boundary,
        )
        for classification in classifications
    ]
    return {
        'inputs': [item.to_dict() for item in items],
        'classifications': [classification.to_dict() for classification in classifications],
        'findings': [finding.to_dict() for finding in findings],
        'decision': decision.to_dict(),
        'confirmation_boundary': boundary.to_dict(),
        'records': [record.to_dict() for record in records],
    }


def build_input_safety_record(
    *,
    classification: InputSafetyClassification,
    decision: InputSafetyDecision,
    finding_refs: Iterable[str],
    confirmation_boundary: Optional[InputSafetyConfirmationBoundary] = None,
) -> InputSafetyRecord:
    if decision.overall_status == 'blocked':
        final_status = 'blocked'
    elif confirmation_boundary and confirmation_boundary.confirmed_by:
        final_status = 'confirmed_then_allowed'
    elif decision.overall_status == 'allow_with_warning':
        final_status = 'allowed_with_warning'
    else:
        final_status = 'allowed'
    return InputSafetyRecord(
        input_ref=classification.input_ref,
        classification_ref=classification.classification_id,
        decision_ref=decision.decision_id,
        finding_refs=list(finding_refs),
        final_status=final_status,
        recorded_at=_utc_now_iso(),
    )
