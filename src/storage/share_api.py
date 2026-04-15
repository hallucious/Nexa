from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from src.contracts.nex_contract import (
    PublicNexShareBoundary,
    PublicNexShareDescriptor,
    ShareOperation,
)
from src.storage.nex_api import (
    describe_public_nex_artifact,
    export_public_nex_artifact,
    get_public_nex_format_boundary,
)

_PUBLIC_NEX_SHARE_BOUNDARY = PublicNexShareBoundary(
    share_family="nex.public-link-share",
    transport_modes=("link",),
    access_modes=("public_readonly",),
    supported_roles=get_public_nex_format_boundary().supported_roles,
    artifact_format_family=get_public_nex_format_boundary().format_family,
    viewer_capabilities=("inspect_metadata", "download_artifact", "import_copy"),
    supported_operations=("inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy"),
)


def get_public_nex_share_boundary() -> PublicNexShareBoundary:
    return _PUBLIC_NEX_SHARE_BOUNDARY


def _operation_capabilities_for_role(storage_role: str) -> tuple[ShareOperation, ...]:
    if storage_role == "working_save":
        return ("inspect_metadata", "download_artifact", "import_copy", "run_artifact")
    if storage_role == "commit_snapshot":
        return ("inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy")
    raise ValueError(f"Unsupported public link share storage_role: {storage_role}")


def ensure_public_nex_link_share_operation_allowed(
    source: str | Path | dict[str, Any],
    operation: ShareOperation,
) -> PublicNexShareDescriptor:
    descriptor = describe_public_nex_link_share(source)
    if operation not in descriptor.operation_capabilities:
        raise ValueError(
            f"public link share does not allow operation={operation} for storage_role={descriptor.storage_role}"
        )
    return descriptor


def is_public_nex_link_share_payload(data: Mapping[str, Any]) -> bool:
    if not isinstance(data, Mapping):
        return False
    share = data.get("share")
    artifact = data.get("artifact")
    if not isinstance(share, Mapping) or not isinstance(artifact, Mapping):
        return False
    return share.get("share_family") == _PUBLIC_NEX_SHARE_BOUNDARY.share_family


def extract_public_nex_link_share_artifact(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    payload = load_public_nex_link_share(source)
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("public link share payload must contain a canonical artifact object")
    return dict(artifact)


def _stable_share_id(artifact_payload: dict[str, Any]) -> str:
    canonical = json.dumps(artifact_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"share_{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def export_public_nex_link_share(
    model_or_data: Any,
    *,
    share_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    artifact = export_public_nex_artifact(model_or_data)
    descriptor = describe_public_nex_artifact(artifact)
    meta = artifact.get("meta", {}) if isinstance(artifact.get("meta"), dict) else {}
    resolved_share_id = share_id or _stable_share_id(artifact)
    if not isinstance(resolved_share_id, str) or not resolved_share_id.strip():
        raise ValueError("public link share requires a non-empty share_id")
    resolved_title = title or str(meta.get("name") or descriptor.canonical_ref)
    resolved_summary = summary if summary is not None else (
        str(meta.get("description")) if meta.get("description") is not None else None
    )
    operation_capabilities = _operation_capabilities_for_role(descriptor.storage_role)
    return {
        "share": {
            "share_family": _PUBLIC_NEX_SHARE_BOUNDARY.share_family,
            "transport": "link",
            "access_mode": "public_readonly",
            "share_id": resolved_share_id.strip(),
            "share_path": f"/share/{resolved_share_id.strip()}",
            "artifact_format_family": descriptor.identity_field and _PUBLIC_NEX_SHARE_BOUNDARY.artifact_format_family,
            "storage_role": descriptor.storage_role,
            "canonical_ref": descriptor.canonical_ref,
            "title": resolved_title,
            "summary": resolved_summary,
            "viewer_capabilities": list(_PUBLIC_NEX_SHARE_BOUNDARY.viewer_capabilities),
            "operation_capabilities": list(operation_capabilities),
        },
        "artifact": artifact,
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("public link share payload must be a JSON object")
    return data


def load_public_nex_link_share(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    payload = _read_json_object(Path(source)) if isinstance(source, (str, Path)) else dict(source)
    share = payload.get("share")
    artifact = payload.get("artifact")
    if not isinstance(share, dict):
        raise ValueError("public link share payload must include object section 'share'")
    if not isinstance(artifact, dict):
        raise ValueError("public link share payload must include object section 'artifact'")
    if share.get("share_family") != _PUBLIC_NEX_SHARE_BOUNDARY.share_family:
        raise ValueError("unsupported public link share family")
    if share.get("transport") != "link":
        raise ValueError("public link share payload must declare transport=link")
    if share.get("access_mode") != "public_readonly":
        raise ValueError("public link share payload must declare access_mode=public_readonly")
    share_id = share.get("share_id")
    if not isinstance(share_id, str) or not share_id.strip():
        raise ValueError("public link share payload must include non-empty share.share_id")
    exported_artifact = export_public_nex_artifact(artifact)
    artifact_descriptor = describe_public_nex_artifact(exported_artifact)
    title = share.get("title")
    if not isinstance(title, str) or not title.strip():
        meta = exported_artifact.get("meta", {}) if isinstance(exported_artifact.get("meta"), dict) else {}
        title = str(meta.get("name") or artifact_descriptor.canonical_ref)
    summary = share.get("summary")
    if summary is not None and not isinstance(summary, str):
        raise ValueError("public link share payload share.summary must be a string when present")
    return export_public_nex_link_share(
        exported_artifact,
        share_id=share_id.strip(),
        title=title.strip(),
        summary=summary,
    )


def describe_public_nex_link_share(source: str | Path | dict[str, Any]) -> PublicNexShareDescriptor:
    payload = load_public_nex_link_share(source)
    share = payload["share"]
    descriptor = describe_public_nex_artifact(payload["artifact"])
    return PublicNexShareDescriptor(
        share_id=share["share_id"],
        share_path=share["share_path"],
        transport="link",
        access_mode="public_readonly",
        storage_role=descriptor.storage_role,
        canonical_ref=descriptor.canonical_ref,
        title=share["title"],
        summary=share.get("summary"),
        artifact_format_family=_PUBLIC_NEX_SHARE_BOUNDARY.artifact_format_family,
        viewer_capabilities=_PUBLIC_NEX_SHARE_BOUNDARY.viewer_capabilities,
        operation_capabilities=_operation_capabilities_for_role(descriptor.storage_role),
        source_working_save_id=descriptor.source_working_save_id,
    )


def save_public_nex_link_share_file(
    model_or_data: Any,
    destination: str | Path,
    *,
    share_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
) -> Path:
    path = Path(destination)
    payload = export_public_nex_link_share(
        model_or_data, share_id=share_id, title=title, summary=summary
    )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


__all__ = [
    "get_public_nex_share_boundary",
    "is_public_nex_link_share_payload",
    "extract_public_nex_link_share_artifact",
    "export_public_nex_link_share",
    "load_public_nex_link_share",
    "describe_public_nex_link_share",
    "save_public_nex_link_share_file",
    "ensure_public_nex_link_share_operation_allowed",
]
