from __future__ import annotations

# Backward-compatibility shim (legacy pipeline)
# New canonical location: src.platform.observability
from src.platform.observability import (  # noqa: F401
    OBS_FILE_NAME,
    append_observability_event,
    read_observability_events,
)
