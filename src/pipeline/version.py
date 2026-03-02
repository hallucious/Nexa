from __future__ import annotations

"""Pipeline Shim Version.

This module acts as a shim layer.
Canonical legacy implementation lives under:

    src.legacy.pipeline.version

Engine-native execution entrypoint is:

    src.engine.cli
"""

from src.legacy.pipeline.version import PIPELINE_API_VERSION  # re-export
