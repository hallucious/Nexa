from __future__ import annotations

from datetime import datetime, timezone, timedelta

# Korea Standard Time is UTC+9
KST = timezone(timedelta(hours=9))

def now_seoul() -> datetime:
    """
    Returns timezone-aware datetime in Asia/Seoul (KST).
    Works on Python 3.8+ without zoneinfo.
    """
    return datetime.now(tz=KST)

def make_run_id(dt: datetime | None = None) -> str:
    """
    Run ID format: YYYY-MM-DD_HHMM (Asia/Seoul)
    """
    if dt is None:
        dt = now_seoul()
    return dt.strftime("%Y-%m-%d_%H%M")
