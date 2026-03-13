
from __future__ import annotations

from typing import Any, Protocol


class GateContextLike(Protocol):
    """Minimal context surface needed by platform plugins.

    This protocol decouples platform plugins from execution context dependencies.
    """

    run_dir: str
    meta: Any  # expected to carry attempts mapping and other run metadata
