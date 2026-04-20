from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.contracts.commit_snapshot_contract import (
    COMMIT_SNAPSHOT_ALLOWED_VALIDATION_RESULTS,
    COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS,
    COMMIT_SNAPSHOT_IDENTITY_FIELD,
    COMMIT_SNAPSHOT_REQUIRED_SECTIONS,
)
from src.contracts.nex_contract import (
    ALLOWED_STORAGE_ROLES,
    COMMIT_SNAPSHOT_ROLE,
    WORKING_SAVE_ROLE,
    ValidationFinding,
)
from src.contracts.working_save_contract import (
    WORKING_SAVE_ALLOWED_RUNTIME_STATUSES,
    WORKING_SAVE_IDENTITY_FIELD,
    WORKING_SAVE_REQUIRED_SECTIONS,
)
from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import DesignerDraftModel, RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel

_SHARED_BACKBONE = ("meta", "circuit", "resources", "state")


def _finding(
    code: str,
    category: str,
    severity: str,
    blocking: bool,
    location: str | None,
    message: str,
    hint: str | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        code=code,
        category=category,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        blocking=blocking,
        location=location,
        message=message,
        hint=hint,
    )


def _parse_source(source: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(source, dict):
        return dict(source), None
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(".nex root must be a JSON object")
    return data, str(path)


def _check_shared_backbone(data: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    missing = [section for section in _SHARED_BACKBONE if section not in data]
    if missing:
        findings.append(
            _finding(
                "NEX_MISSING_SHARED_BACKBONE",
                "top_level_shape",
                "high",
                True,
                None,
                "Missing shared .nex backbone section(s): " + ", ".join(missing),
            )
        )
        return findings

    for section in _SHARED_BACKBONE:
        if not isinstance(data.get(section), dict):
            findings.append(
                _finding(
                    "NEX_SHARED_SECTION_NOT_OBJECT",
                    "shared_schema",
                    "high",
                    True,
                    section,
                    f"Shared section '{section}' must be an object",
                )
            )
    return findings


def _resolve_storage_role(data: dict[str, Any], *, allow_legacy_fallback: bool = True) -> tuple[str, list[str], list[ValidationFinding]]:
    meta = data.get("meta", {})
    role = meta.get("storage_role") if isinstance(meta, dict) else None
    migration_notes: list[str] = []
    findings: list[ValidationFinding] = []

    if role is None:
        if allow_legacy_fallback:
            role = WORKING_SAVE_ROLE
            migration_notes.append("Missing meta.storage_role; defaulted to working_save for legacy compatibility")
        else:
            findings.append(
                _finding(
                    "NEX_STORAGE_ROLE_MISSING",
                    "storage_role",
                    "high",
                    True,
                    "meta.storage_role",
                    "meta.storage_role is required when legacy fallback is disabled",
                )
            )
            role = WORKING_SAVE_ROLE

    if role not in ALLOWED_STORAGE_ROLES:
        findings.append(
            _finding(
                "NEX_STORAGE_ROLE_INVALID",
                "storage_role",
                "high",
                True,
                "meta.storage_role",
                f"Unsupported storage_role '{role}'",
            )
        )
    return role, migration_notes, findings


def _validate_shared_schema(data: dict[str, Any], *, strict_unknown_fields: bool = False) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    resources = data.get("resources", {})
    state = data.get("state", {})
    meta = data.get("meta", {})
    circuit = data.get("circuit", {})

    if not isinstance(meta.get("format_version"), str) or not meta.get("format_version"):
        findings.append(_finding("NEX_FORMAT_VERSION_INVALID", "shared_schema", "high", True, "meta.format_version", "meta.format_version must be a non-empty string"))
    if "storage_role" in meta and meta.get("storage_role") not in ALLOWED_STORAGE_ROLES:
        findings.append(_finding("NEX_STORAGE_ROLE_INVALID", "storage_role", "high", True, "meta.storage_role", "meta.storage_role must be working_save or commit_snapshot"))

    for section_name in ("prompts", "providers", "plugins"):
        if section_name not in resources or not isinstance(resources.get(section_name), dict):
            findings.append(_finding("NEX_RESOURCES_SECTION_INVALID", "shared_schema", "high", True, f"resources.{section_name}", f"resources.{section_name} must be an object"))

    for section_name in ("input", "working", "memory"):
        if section_name not in state or not isinstance(state.get(section_name), dict):
            findings.append(_finding("NEX_STATE_SECTION_INVALID", "state_shape", "high", True, f"state.{section_name}", f"state.{section_name} must be an object"))

    if not isinstance(circuit.get("nodes", []), list):
        findings.append(_finding("NEX_CIRCUIT_NODES_INVALID", "shared_schema", "high", True, "circuit.nodes", "circuit.nodes must be a list"))
    if "edges" in circuit and not isinstance(circuit.get("edges"), list):
        findings.append(_finding("NEX_CIRCUIT_EDGES_INVALID", "shared_schema", "high", True, "circuit.edges", "circuit.edges must be a list"))
    if "outputs" in circuit and not isinstance(circuit.get("outputs"), list):
        findings.append(_finding("NEX_CIRCUIT_OUTPUTS_INVALID", "shared_schema", "high", True, "circuit.outputs", "circuit.outputs must be a list"))
    if "subcircuits" in circuit and not isinstance(circuit.get("subcircuits"), dict):
        findings.append(_finding("NEX_CIRCUIT_SUBCIRCUITS_INVALID", "shared_schema", "high", True, "circuit.subcircuits", "circuit.subcircuits must be an object"))
    elif isinstance(circuit.get("subcircuits"), dict):
        for child_name, child in circuit.get("subcircuits", {}).items():
            if not isinstance(child, dict):
                findings.append(_finding("NEX_SUBCIRCUIT_DEFINITION_INVALID", "shared_schema", "high", True, f"circuit.subcircuits.{child_name}", f"Subcircuit '{child_name}' must be an object"))
                continue
            for field_name in ("nodes", "edges", "outputs"):
                if field_name in child and not isinstance(child.get(field_name), list):
                    findings.append(_finding("NEX_SUBCIRCUIT_SECTION_INVALID", "shared_schema", "high", True, f"circuit.subcircuits.{child_name}.{field_name}", f"Subcircuit '{child_name}' field '{field_name}' must be a list"))

    if strict_unknown_fields:
        allowed_meta = {"format_version", "storage_role", "name", "description", "created_at", "updated_at", WORKING_SAVE_IDENTITY_FIELD, COMMIT_SNAPSHOT_IDENTITY_FIELD, "source_working_save_id"}
        for key in meta.keys() - allowed_meta:
            findings.append(_finding("NEX_UNKNOWN_META_FIELD", "shared_schema", "low", False, f"meta.{key}", f"Unknown meta field '{key}'"))

    return findings


def _validate_working_save_schema(data: dict[str, Any], *, strict_unknown_fields: bool = False) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for section in WORKING_SAVE_REQUIRED_SECTIONS:
        if section not in data or not isinstance(data.get(section), dict):
            findings.append(_finding("WORKING_SAVE_REQUIRED_SECTION_MISSING", "role_schema", "high", True, section, f"Working Save requires object section '{section}'"))

    meta = data.get("meta", {})
    if meta.get("storage_role", WORKING_SAVE_ROLE) != WORKING_SAVE_ROLE:
        findings.append(_finding("WORKING_SAVE_ROLE_MISMATCH", "storage_role", "high", True, "meta.storage_role", "Working Save artifact must resolve to storage_role=working_save"))
    if not isinstance(meta.get(WORKING_SAVE_IDENTITY_FIELD), str) or not meta.get(WORKING_SAVE_IDENTITY_FIELD):
        findings.append(_finding("WORKING_SAVE_IDENTITY_MISSING", "role_schema", "high", True, f"meta.{WORKING_SAVE_IDENTITY_FIELD}", "Working Save meta must include working_save_id"))

    runtime = data.get("runtime", {})
    ui = data.get("ui", {})
    if "status" in runtime and not isinstance(runtime.get("status"), str):
        findings.append(_finding("WORKING_SAVE_RUNTIME_STATUS_INVALID", "runtime_section", "high", True, "runtime.status", "runtime.status must be a string"))
    if not isinstance(ui.get("layout", {}), dict):
        findings.append(_finding("WORKING_SAVE_UI_LAYOUT_INVALID", "runtime_section", "high", True, "ui.layout", "ui.layout must be an object"))
    if not isinstance(ui.get("metadata", {}), dict):
        findings.append(_finding("WORKING_SAVE_UI_METADATA_INVALID", "runtime_section", "high", True, "ui.metadata", "ui.metadata must be an object"))
    if strict_unknown_fields:
        allowed = set(WORKING_SAVE_REQUIRED_SECTIONS) | {"designer"}
        for key in data.keys() - allowed:
            findings.append(_finding("WORKING_SAVE_UNKNOWN_TOP_LEVEL", "role_schema", "low", False, key, f"Unknown Working Save top-level field '{key}'"))
    return findings


def _validate_working_save_semantics(data: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    circuit = data.get("circuit", {})
    runtime = data.get("runtime", {})

    if not circuit.get("entry"):
        findings.append(_finding("WORKING_SAVE_ENTRY_MISSING", "structural", "medium", True, "circuit.entry", "Working Save may load without an entry, but entry is currently missing", "Add an entry node before treating the artifact as execution-ready"))

    outputs = circuit.get("outputs")
    if not outputs:
        findings.append(_finding("WORKING_SAVE_OUTPUTS_MISSING", "structural", "medium", True, "circuit.outputs", "Working Save may load without outputs, but no final outputs are declared", "Add at least one output binding before commit or execution"))

    status = runtime.get("status")
    if isinstance(status, str) and status not in WORKING_SAVE_ALLOWED_RUNTIME_STATUSES:
        findings.append(_finding("WORKING_SAVE_RUNTIME_STATUS_UNKNOWN", "runtime_section", "medium", False, "runtime.status", f"Unknown runtime.status '{status}'"))

    resources = data.get("resources", {})
    circuit_nodes = circuit.get("nodes", []) if isinstance(circuit.get("nodes"), list) else []
    prompt_ids = set(resources.get("prompts", {}).keys())
    provider_ids = set(resources.get("providers", {}).keys())
    plugin_ids = set(resources.get("plugins", {}).keys())
    for idx, node in enumerate(circuit_nodes):
        if not isinstance(node, dict):
            continue
        resource_ref = node.get("resource_ref", {})
        node_type = node.get("type")
        location = f"circuit.nodes[{idx}]"
        if node_type == "ai":
            if resource_ref.get("prompt") and resource_ref.get("prompt") not in prompt_ids:
                findings.append(_finding("WORKING_SAVE_PROMPT_UNRESOLVED", "resource_resolution", "medium", False, location, f"AI node references unresolved prompt '{resource_ref.get('prompt')}'"))
            if resource_ref.get("provider") and resource_ref.get("provider") not in provider_ids:
                findings.append(_finding("WORKING_SAVE_PROVIDER_UNRESOLVED", "resource_resolution", "medium", False, location, f"AI node references unresolved provider '{resource_ref.get('provider')}'"))
        if node_type == "plugin":
            if resource_ref.get("plugin") and resource_ref.get("plugin") not in plugin_ids:
                findings.append(_finding("WORKING_SAVE_PLUGIN_UNRESOLVED", "resource_resolution", "medium", False, location, f"Plugin node references unresolved plugin '{resource_ref.get('plugin')}'"))

    if "approval" in data or "lineage" in data:
        findings.append(_finding("WORKING_SAVE_DRAFT_TRUTH_COLLISION", "semantic", "high", True, None, "Working Save must not carry approval/lineage sections as committed truth"))
    return findings


def _validate_commit_snapshot_schema(data: dict[str, Any], *, strict_unknown_fields: bool = False) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for section in COMMIT_SNAPSHOT_REQUIRED_SECTIONS:
        if section not in data or not isinstance(data.get(section), dict):
            findings.append(_finding("COMMIT_SNAPSHOT_REQUIRED_SECTION_MISSING", "role_schema", "high", True, section, f"Commit Snapshot requires object section '{section}'"))
    for forbidden in COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS:
        if forbidden in data:
            findings.append(_finding("COMMIT_SNAPSHOT_FORBIDDEN_SECTION_PRESENT", "role_schema", "high", True, forbidden, f"Commit Snapshot must not include '{forbidden}' section"))

    meta = data.get("meta", {})
    if meta.get("storage_role") != COMMIT_SNAPSHOT_ROLE:
        findings.append(_finding("COMMIT_SNAPSHOT_ROLE_MISMATCH", "storage_role", "high", True, "meta.storage_role", "Commit Snapshot must explicitly declare storage_role=commit_snapshot"))
    if not isinstance(meta.get(COMMIT_SNAPSHOT_IDENTITY_FIELD), str) or not meta.get(COMMIT_SNAPSHOT_IDENTITY_FIELD):
        findings.append(_finding("COMMIT_SNAPSHOT_IDENTITY_MISSING", "approval_section", "high", True, f"meta.{COMMIT_SNAPSHOT_IDENTITY_FIELD}", "Commit Snapshot meta must include commit_id"))
    if strict_unknown_fields:
        allowed = set(COMMIT_SNAPSHOT_REQUIRED_SECTIONS)
        for key in data.keys() - allowed:
            findings.append(_finding("COMMIT_SNAPSHOT_UNKNOWN_TOP_LEVEL", "role_schema", "low", False, key, f"Unknown Commit Snapshot top-level field '{key}'"))
    return findings


def _validate_commit_snapshot_semantics(data: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    validation = data.get("validation", {})
    approval = data.get("approval", {})
    lineage = data.get("lineage", {})
    circuit = data.get("circuit", {})

    result = validation.get("validation_result")
    if result not in COMMIT_SNAPSHOT_ALLOWED_VALIDATION_RESULTS:
        findings.append(_finding("COMMIT_SNAPSHOT_VALIDATION_RESULT_INVALID", "approval_section", "high", True, "validation.validation_result", "Commit Snapshot validation_result must be passed or passed_with_warnings"))
    if approval.get("approval_completed") is not True:
        findings.append(_finding("COMMIT_SNAPSHOT_APPROVAL_INCOMPLETE", "approval_section", "high", True, "approval.approval_completed", "Commit Snapshot approval_completed must be true"))
    if not approval.get("approval_status"):
        findings.append(_finding("COMMIT_SNAPSHOT_APPROVAL_STATUS_MISSING", "approval_section", "high", True, "approval.approval_status", "Commit Snapshot approval_status must be present"))
    if not isinstance(lineage, dict):
        findings.append(_finding("COMMIT_SNAPSHOT_LINEAGE_INVALID", "lineage_section", "high", True, "lineage", "Commit Snapshot lineage must be an object"))
    if not circuit.get("entry"):
        findings.append(_finding("COMMIT_SNAPSHOT_ENTRY_MISSING", "structural", "high", True, "circuit.entry", "Commit Snapshot must declare an entry node"))
    if not circuit.get("outputs"):
        findings.append(_finding("COMMIT_SNAPSHOT_OUTPUTS_MISSING", "structural", "high", True, "circuit.outputs", "Commit Snapshot must declare final outputs"))
    return findings


def _construct_shared_models(data: dict[str, Any]) -> tuple[CircuitModel, ResourcesModel, StateModel]:
    circuit = data.get("circuit", {})
    resources = data.get("resources", {})
    state = data.get("state", {})
    return (
        CircuitModel(
            nodes=list(circuit.get("nodes", [])),
            edges=list(circuit.get("edges", [])),
            entry=circuit.get("entry"),
            outputs=list(circuit.get("outputs", [])),
            subcircuits=dict(circuit.get("subcircuits", {})),
        ),
        ResourcesModel(
            prompts=dict(resources.get("prompts", {})),
            providers=dict(resources.get("providers", {})),
            plugins=dict(resources.get("plugins", {})),
        ),
        StateModel(
            input=dict(state.get("input", {})),
            working=dict(state.get("working", {})),
            memory=dict(state.get("memory", {})),
        ),
    )


def _construct_working_save_model(data: dict[str, Any]) -> WorkingSaveModel:
    meta = data.get("meta", {})
    circuit, resources, state = _construct_shared_models(data)
    runtime = data.get("runtime", {})
    ui = data.get("ui", {})
    designer = data.get("designer")
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version=meta.get("format_version", ""),
            storage_role=WORKING_SAVE_ROLE,
            name=meta.get("name"),
            description=meta.get("description"),
            created_at=meta.get("created_at"),
            updated_at=meta.get("updated_at"),
            working_save_id=meta.get(WORKING_SAVE_IDENTITY_FIELD, ""),
        ),
        circuit=circuit,
        resources=resources,
        state=state,
        runtime=RuntimeModel(
            status=runtime.get("status", "draft"),
            validation_summary=dict(runtime.get("validation_summary", {})),
            last_run=dict(runtime.get("last_run", {})),
            errors=list(runtime.get("errors", [])),
        ),
        ui=UIModel(
            layout=dict(ui.get("layout", {})),
            metadata=dict(ui.get("metadata", {})),
        ),
        designer=DesignerDraftModel(dict(designer)) if isinstance(designer, dict) else None,
    )


def _construct_commit_snapshot_model(data: dict[str, Any]) -> CommitSnapshotModel:
    meta = data.get("meta", {})
    circuit, resources, state = _construct_shared_models(data)
    validation = data.get("validation", {})
    approval = data.get("approval", {})
    lineage = data.get("lineage", {})
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version=meta.get("format_version", ""),
            storage_role=COMMIT_SNAPSHOT_ROLE,
            name=meta.get("name"),
            description=meta.get("description"),
            created_at=meta.get("created_at"),
            updated_at=meta.get("updated_at"),
            commit_id=meta.get(COMMIT_SNAPSHOT_IDENTITY_FIELD, ""),
            source_working_save_id=meta.get("source_working_save_id"),
        ),
        circuit=circuit,
        resources=resources,
        state=state,
        validation=CommitValidationModel(
            validation_result=validation.get("validation_result", ""),
            summary=dict(validation.get("summary", {})),
        ),
        approval=CommitApprovalModel(
            approval_completed=bool(approval.get("approval_completed", False)),
            approval_status=approval.get("approval_status"),
            summary=dict(approval.get("summary", {})),
        ),
        lineage=CommitLineageModel(
            parent_commit_id=lineage.get("parent_commit_id"),
            source_working_save_id=lineage.get("source_working_save_id"),
            metadata=dict(lineage.get("metadata", {})),
        ),
    )


def _make_validation_report(role: str, findings: list[ValidationFinding]):
    from src.contracts.nex_contract import ValidationReport

    blocking_count = sum(1 for f in findings if f.blocking)
    warning_count = len(findings) - blocking_count
    if blocking_count:
        result = "failed"
    elif findings:
        result = "passed_with_findings"
    else:
        result = "passed"
    return ValidationReport(
        role=role,  # type: ignore[arg-type]
        findings=findings,
        blocking_count=blocking_count,
        warning_count=warning_count,
        result=result,  # type: ignore[arg-type]
    )


def load_nex(
    source: str | Path | dict[str, Any],
    *,
    allow_legacy_fallback: bool = True,
    strict_unknown_fields: bool = False,
    validate: bool = True,
) -> LoadedNexArtifact:
    raw_data, source_path = _parse_source(source)
    findings = _check_shared_backbone(raw_data)
    if any(f.blocking for f in findings):
        role, migration_notes, role_findings = _resolve_storage_role(raw_data, allow_legacy_fallback=allow_legacy_fallback)
        findings.extend(role_findings)
        return LoadedNexArtifact(storage_role=role, raw_data=raw_data, parsed_model=None, findings=findings, load_status="rejected", source_path=source_path, migration_notes=migration_notes or None)

    role, migration_notes, role_findings = _resolve_storage_role(raw_data, allow_legacy_fallback=allow_legacy_fallback)
    findings.extend(role_findings)

    if validate:
        findings.extend(_validate_shared_schema(raw_data, strict_unknown_fields=strict_unknown_fields))
        if role == WORKING_SAVE_ROLE:
            findings.extend(_validate_working_save_schema(raw_data, strict_unknown_fields=strict_unknown_fields))
            findings.extend(_validate_working_save_semantics(raw_data))
        else:
            findings.extend(_validate_commit_snapshot_schema(raw_data, strict_unknown_fields=strict_unknown_fields))
            findings.extend(_validate_commit_snapshot_semantics(raw_data))

    if role == COMMIT_SNAPSHOT_ROLE and any(f.blocking for f in findings):
        return LoadedNexArtifact(storage_role=COMMIT_SNAPSHOT_ROLE, raw_data=raw_data, parsed_model=None, findings=findings, load_status="rejected", source_path=source_path, migration_notes=migration_notes or None)

    model = _construct_working_save_model(raw_data) if role == WORKING_SAVE_ROLE else _construct_commit_snapshot_model(raw_data)
    status = "loaded" if not findings else "loaded_with_findings"
    return LoadedNexArtifact(storage_role=role, raw_data=raw_data, parsed_model=model, findings=findings, load_status=status, source_path=source_path, migration_notes=migration_notes or None)


def validate_working_save(model_or_data: WorkingSaveModel | dict[str, Any], *, strict_unknown_fields: bool = False):
    if isinstance(model_or_data, WorkingSaveModel):
        data = {
            "meta": {
                "format_version": model_or_data.meta.format_version,
                "storage_role": model_or_data.meta.storage_role,
                "name": model_or_data.meta.name,
                "description": model_or_data.meta.description,
                "created_at": model_or_data.meta.created_at,
                "updated_at": model_or_data.meta.updated_at,
                WORKING_SAVE_IDENTITY_FIELD: model_or_data.meta.working_save_id,
            },
            "circuit": {
                "nodes": model_or_data.circuit.nodes,
                "edges": model_or_data.circuit.edges,
                "entry": model_or_data.circuit.entry,
                "outputs": model_or_data.circuit.outputs,
            },
            "resources": {
                "prompts": model_or_data.resources.prompts,
                "providers": model_or_data.resources.providers,
                "plugins": model_or_data.resources.plugins,
            },
            "state": {
                "input": model_or_data.state.input,
                "working": model_or_data.state.working,
                "memory": model_or_data.state.memory,
            },
            "runtime": {
                "status": model_or_data.runtime.status,
                "validation_summary": model_or_data.runtime.validation_summary,
                "last_run": model_or_data.runtime.last_run,
                "errors": model_or_data.runtime.errors,
            },
            "ui": {
                "layout": model_or_data.ui.layout,
                "metadata": model_or_data.ui.metadata,
            },
        }
        if model_or_data.designer is not None:
            data["designer"] = model_or_data.designer.data
    else:
        data = dict(model_or_data)
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
        if meta is None:
            # No meta present at all: default to working_save so the
            # downstream shared-backbone/role schema checks can still fire
            # deterministically (kept for legacy-compat input parity).
            data["meta"] = {"storage_role": WORKING_SAVE_ROLE}
        elif "storage_role" not in meta:
            # Role absent: default to working_save to preserve the existing
            # permissive working_save dict input contract.
            meta["storage_role"] = WORKING_SAVE_ROLE
        # If the caller explicitly declared a different role, do NOT overwrite.
        # Let _validate_working_save_schema emit WORKING_SAVE_ROLE_MISMATCH so
        # the CLI / public validator surface treats role conflicts as findings
        # rather than silently re-coercing the payload — this keeps
        # validate_working_save symmetric with validate_commit_snapshot.

    findings = []
    findings.extend(_check_shared_backbone(data))
    findings.extend(_validate_shared_schema(data, strict_unknown_fields=strict_unknown_fields))
    findings.extend(_validate_working_save_schema(data, strict_unknown_fields=strict_unknown_fields))
    findings.extend(_validate_working_save_semantics(data))
    return _make_validation_report(WORKING_SAVE_ROLE, findings)


def validate_commit_snapshot(model_or_data: CommitSnapshotModel | dict[str, Any], *, strict_unknown_fields: bool = False):
    if isinstance(model_or_data, CommitSnapshotModel):
        data = {
            "meta": {
                "format_version": model_or_data.meta.format_version,
                "storage_role": model_or_data.meta.storage_role,
                "name": model_or_data.meta.name,
                "description": model_or_data.meta.description,
                "created_at": model_or_data.meta.created_at,
                "updated_at": model_or_data.meta.updated_at,
                COMMIT_SNAPSHOT_IDENTITY_FIELD: model_or_data.meta.commit_id,
                "source_working_save_id": model_or_data.meta.source_working_save_id,
            },
            "circuit": {
                "nodes": model_or_data.circuit.nodes,
                "edges": model_or_data.circuit.edges,
                "entry": model_or_data.circuit.entry,
                "outputs": model_or_data.circuit.outputs,
            },
            "resources": {
                "prompts": model_or_data.resources.prompts,
                "providers": model_or_data.resources.providers,
                "plugins": model_or_data.resources.plugins,
            },
            "state": {
                "input": model_or_data.state.input,
                "working": model_or_data.state.working,
                "memory": model_or_data.state.memory,
            },
            "validation": {
                "validation_result": model_or_data.validation.validation_result,
                "summary": model_or_data.validation.summary,
            },
            "approval": {
                "approval_completed": model_or_data.approval.approval_completed,
                "approval_status": model_or_data.approval.approval_status,
                "summary": model_or_data.approval.summary,
            },
            "lineage": {
                "parent_commit_id": model_or_data.lineage.parent_commit_id,
                "source_working_save_id": model_or_data.lineage.source_working_save_id,
                "metadata": model_or_data.lineage.metadata,
            },
        }
    else:
        data = dict(model_or_data)

    findings = []
    findings.extend(_check_shared_backbone(data))
    findings.extend(_validate_shared_schema(data, strict_unknown_fields=strict_unknown_fields))
    findings.extend(_validate_commit_snapshot_schema(data, strict_unknown_fields=strict_unknown_fields))
    findings.extend(_validate_commit_snapshot_semantics(data))
    return _make_validation_report(COMMIT_SNAPSHOT_ROLE, findings)
