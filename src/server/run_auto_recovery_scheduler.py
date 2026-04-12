from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from src.server.run_auto_recovery_policy import AutoRecoveryOutcome, apply_auto_recovery

RunRecordWriter = Callable[[Mapping[str, Any]], Any]
QueueJobIdFactory = Callable[[], str]


@dataclass(frozen=True)
class AutoRecoverySchedulerStats:
    scanned_count: int
    eligible_count: int
    applied_count: int
    auto_retry_count: int
    auto_mark_review_required_count: int
    skipped_count: int


@dataclass(frozen=True)
class AutoRecoveryScheduledUpdate:
    run_id: str
    action: str
    updated_run_record: Mapping[str, Any]


@dataclass(frozen=True)
class AutoRecoverySchedulerOutcome:
    stats: AutoRecoverySchedulerStats
    applied_updates: tuple[AutoRecoveryScheduledUpdate, ...]


class AutoRecoveryScheduler:
    @staticmethod
    def _is_sequence_of_rows(value: Sequence[Mapping[str, Any]] | None) -> tuple[Mapping[str, Any], ...]:
        if not value:
            return ()
        return tuple(row for row in value if isinstance(row, Mapping))

    @classmethod
    def run_batch(
        cls,
        run_rows: Sequence[Mapping[str, Any]] | None,
        *,
        now_iso: str,
        run_record_writer: Optional[RunRecordWriter] = None,
        queue_job_id_factory: Optional[QueueJobIdFactory] = None,
        batch_limit: int = 50,
        max_applied_per_batch: Optional[int] = None,
    ) -> AutoRecoverySchedulerOutcome:
        if batch_limit < 0:
            raise ValueError("batch_limit must be non-negative")
        if max_applied_per_batch is not None and max_applied_per_batch < 0:
            raise ValueError("max_applied_per_batch must be non-negative")

        rows = cls._is_sequence_of_rows(run_rows)
        rows = () if batch_limit == 0 else rows[:batch_limit]

        applied_updates: list[AutoRecoveryScheduledUpdate] = []
        eligible_count = 0
        auto_retry_count = 0
        auto_mark_review_required_count = 0

        for row in rows:
            if max_applied_per_batch is not None and len(applied_updates) >= max_applied_per_batch:
                break
            outcome: AutoRecoveryOutcome = apply_auto_recovery(
                row,
                now_iso=now_iso,
                queue_job_id_factory=queue_job_id_factory,
            )
            if not outcome.applied or outcome.updated_run_record is None or outcome.action is None:
                continue
            eligible_count += 1
            updated_row = dict(outcome.updated_run_record)
            if run_record_writer is not None:
                run_record_writer(updated_row)
            if outcome.action == "auto_retry":
                auto_retry_count += 1
            elif outcome.action == "auto_mark_review_required":
                auto_mark_review_required_count += 1
            applied_updates.append(AutoRecoveryScheduledUpdate(
                run_id=str(updated_row.get("run_id") or ""),
                action=outcome.action,
                updated_run_record=updated_row,
            ))

        applied_count = len(applied_updates)
        scanned_count = len(rows)
        skipped_count = scanned_count - applied_count
        return AutoRecoverySchedulerOutcome(
            stats=AutoRecoverySchedulerStats(
                scanned_count=scanned_count,
                eligible_count=eligible_count,
                applied_count=applied_count,
                auto_retry_count=auto_retry_count,
                auto_mark_review_required_count=auto_mark_review_required_count,
                skipped_count=skipped_count,
            ),
            applied_updates=tuple(applied_updates),
        )
