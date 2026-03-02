
from __future__ import annotations

from typing import Any, Protocol


class GateContextLike(Protocol):
    """Minimal context surface needed by platform plugins.

    This protocol is used to decouple platform plugins from legacy pipeline GateContext.
    """

    run_dir: str
    meta: Any  # expected to carry attempts mapping and other run metadata
