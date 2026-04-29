from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PHASE2G_STATUS_COMPLETE = "complete"
PHASE2G_STATUS_INCOMPLETE = "incomplete"

PHASE2G_PACKAGE_O1 = "O1_sentry_baseline"
PHASE2G_PACKAGE_O2 = "O2_otel_baseline"
PHASE2G_PACKAGE_O3 = "O3_redaction_enforcement"
PHASE2G_PACKAGE_O4 = "O4_public_edge_hardening"
PHASE2G_PACKAGE_O5 = "O5_gdpr_deletion_path"


@dataclass(frozen=True)
class Phase2GPackageEvidence:
    package_id: str
    required_paths: tuple[str, ...]
    status: str
    missing_paths: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.status == PHASE2G_STATUS_COMPLETE

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "package_id": self.package_id,
            "status": self.status,
            "required_paths": list(self.required_paths),
        }
        if self.missing_paths:
            payload["missing_paths"] = list(self.missing_paths)
        return payload


@dataclass(frozen=True)
class Phase2GCompletionAudit:
    packages: tuple[Phase2GPackageEvidence, ...]

    @property
    def complete(self) -> bool:
        return all(package.complete for package in self.packages)

    def as_payload(self) -> dict[str, object]:
        return {
            "phase": "Phase 2G",
            "status": PHASE2G_STATUS_COMPLETE if self.complete else PHASE2G_STATUS_INCOMPLETE,
            "packages": [package.as_payload() for package in self.packages],
        }


_PHASE2G_REQUIRED_PATHS: dict[str, tuple[str, ...]] = {
    PHASE2G_PACKAGE_O1: (
        "src/server/sentry_observability_runtime.py",
        "src/server/fastapi_sentry_binding.py",
        "src/server/worker_sentry_binding.py",
        "tests/test_server_sentry_observability_runtime.py",
    ),
    PHASE2G_PACKAGE_O2: (
        "src/server/otel_observability_runtime.py",
        "src/server/otel_datastore_runtime.py",
        "src/server/fastapi_edge_middleware.py",
        "tests/test_server_otel_observability_runtime.py",
        "tests/test_server_otel_datastore_runtime.py",
        "tests/test_server_datastore_hook_wiring.py",
    ),
    PHASE2G_PACKAGE_O3: (
        "src/server/observability_payload_guard.py",
        "tests/test_server_observability_payload_guard.py",
    ),
    PHASE2G_PACKAGE_O4: (
        "src/server/edge_security_runtime.py",
        "src/server/edge_rate_limit_runtime.py",
        "tests/test_server_public_edge_hardening_o4.py",
    ),
    PHASE2G_PACKAGE_O5: (
        "src/server/gdpr_deletion_runtime.py",
        "src/server/gdpr_deletion_api.py",
        "src/server/gdpr_deletion_adapters.py",
        "src/server/gdpr_deletion_schema.py",
        "src/server/gdpr_deletion_dependency_factory.py",
        "tests/test_server_gdpr_deletion_runtime.py",
        "tests/test_server_gdpr_deletion_api.py",
        "tests/test_server_gdpr_deletion_adapters.py",
        "tests/test_server_gdpr_deletion_schema.py",
        "tests/test_server_gdpr_deletion_dependency_factory.py",
    ),
}


def phase2g_required_paths() -> dict[str, tuple[str, ...]]:
    return dict(_PHASE2G_REQUIRED_PATHS)


def build_phase2g_completion_audit(available_paths: Iterable[str]) -> Phase2GCompletionAudit:
    """Build a file-evidence audit for Phase 2G O1-O5 closure.

    The audit is intentionally file-evidence based. It does not replace the
    full test suite; it records whether the code/test artifacts for each Phase
    2G package exist so a future implementer can quickly see whether O1-O5 have
    materialized in the repository rather than remaining document-only.
    """

    available = {str(path).replace("\\", "/") for path in available_paths}
    packages: list[Phase2GPackageEvidence] = []
    for package_id, required_paths in _PHASE2G_REQUIRED_PATHS.items():
        missing = tuple(path for path in required_paths if path not in available)
        packages.append(
            Phase2GPackageEvidence(
                package_id=package_id,
                required_paths=required_paths,
                status=PHASE2G_STATUS_INCOMPLETE if missing else PHASE2G_STATUS_COMPLETE,
                missing_paths=missing,
            )
        )
    return Phase2GCompletionAudit(packages=tuple(packages))


__all__ = [
    "PHASE2G_PACKAGE_O1",
    "PHASE2G_PACKAGE_O2",
    "PHASE2G_PACKAGE_O3",
    "PHASE2G_PACKAGE_O4",
    "PHASE2G_PACKAGE_O5",
    "PHASE2G_STATUS_COMPLETE",
    "PHASE2G_STATUS_INCOMPLETE",
    "Phase2GCompletionAudit",
    "Phase2GPackageEvidence",
    "build_phase2g_completion_audit",
    "phase2g_required_paths",
]
