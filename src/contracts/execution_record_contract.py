from __future__ import annotations

EXECUTION_RECORD_ALLOWED_STATUSES = {
    "running",
    "completed",
    "failed",
    "partial",
    "cancelled",
    "paused",
}

EXECUTION_RECORD_ALLOWED_TRIGGER_TYPES = {
    "manual_run",
    "designer_test_run",
    "replay_run",
    "system_run",
    "benchmark_run",
}

EXECUTION_RECORD_ALLOWED_NODE_OUTCOMES = {
    "success",
    "failed",
    "skipped",
    "partial",
    "cancelled",
    "paused",
}

EXECUTION_RECORD_ALLOWED_ISSUE_CATEGORIES = {
    "input",
    "provider",
    "plugin",
    "runtime",
    "artifact",
    "timeout",
    "validation",
    "unknown",
}

EXECUTION_RECORD_ALLOWED_ISSUE_SEVERITIES = {
    "low",
    "medium",
    "high",
}
