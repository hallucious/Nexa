"""Compatibility wrapper for the legacy engine CLI surface.

The canonical public CLI entrypoint is ``src.cli.nexa_cli:main`` as exposed
through ``pyproject.toml`` and ``nexa.py``. This module remains only as a
bounded compatibility surface for engine-specific tests and old callers that
still import ``src.engine.cli`` directly.
"""

from __future__ import annotations

from src.engine.cli_compat_runner import (
    _parse_node_ids,
    _render_policy_output,
    build_parser,
    main,
    run_engine,
)

CANONICAL_PUBLIC_CLI = "src.cli.nexa_cli:main"

__all__ = [
    "CANONICAL_PUBLIC_CLI",
    "_parse_node_ids",
    "_render_policy_output",
    "build_parser",
    "main",
    "run_engine",
]
