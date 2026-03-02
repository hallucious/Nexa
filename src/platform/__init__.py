from __future__ import annotations

"""Platform package public surface.

Note:
- Legacy GateOrchestrator is deprecated and no longer exported at package import time.
- Import it directly from `src.platform.orchestrator` only if you are operating the legacy pipeline.
"""

from .version import PLATFORM_API_VERSION  # noqa: F401
