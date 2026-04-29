from __future__ import annotations

from src.server.phase2g_completion_audit import (
    PHASE2G_PACKAGE_O5,
    PHASE2G_STATUS_COMPLETE,
    PHASE2G_STATUS_INCOMPLETE,
    build_phase2g_completion_audit,
    phase2g_required_paths,
)


def test_phase2g_completion_audit_reports_complete_when_all_required_paths_exist() -> None:
    available_paths = {
        path
        for required_paths in phase2g_required_paths().values()
        for path in required_paths
    }

    audit = build_phase2g_completion_audit(available_paths)
    payload = audit.as_payload()

    assert audit.complete is True
    assert payload["status"] == PHASE2G_STATUS_COMPLETE
    assert all(package["status"] == PHASE2G_STATUS_COMPLETE for package in payload["packages"])


def test_phase2g_completion_audit_reports_missing_o5_evidence() -> None:
    available_paths = {
        path
        for required_paths in phase2g_required_paths().values()
        for path in required_paths
    }
    available_paths.remove("src/server/gdpr_deletion_dependency_factory.py")

    audit = build_phase2g_completion_audit(available_paths)
    o5 = next(package for package in audit.packages if package.package_id == PHASE2G_PACKAGE_O5)

    assert audit.complete is False
    assert o5.status == PHASE2G_STATUS_INCOMPLETE
    assert o5.missing_paths == ("src/server/gdpr_deletion_dependency_factory.py",)
