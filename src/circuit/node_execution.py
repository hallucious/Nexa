from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol, Union


class Stage(str, Enum):
    PRE = "pre"
    CORE = "core"
    POST = "post"


# Circuit-stage handler signatures:
# - pre:  (node_id, node_raw, input_payload) -> patch (merged into input)
# - core: (node_id, node_raw, input_payload) -> output_payload
# - post: (node_id, node_raw, core_output)  -> patch (merged into core output)
PreHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
CoreHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
PostHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


PipelineHandler = Dict[str, Any]  # keys: pre/core/post


def is_pipeline_handler(obj: Any) -> bool:
    return isinstance(obj, dict) and any(k in obj for k in ("pre", "core", "post"))


def _merge(base: Dict[str, Any], patch: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not patch:
        return dict(base)
    merged = dict(base)
    merged.update(patch)
    return merged


@dataclass
class StageRunReport:
    ran_pre: bool
    ran_core: bool
    ran_post: bool


def run_node_pipeline(
    *,
    node_id: str,
    node_raw: Dict[str, Any],
    input_payload: Dict[str, Any],
    handler: Union[CoreHandler, PipelineHandler],
) -> Dict[str, Any]:
    """Run a node under mandatory Pre → Core → Post stages.

    Enforcement:
    - If handler is callable: treated as CORE only; PRE/POST are no-ops.
    - If handler is pipeline dict: PRE/CORE/POST are executed in order (if present).
    - AI/tool specifics are not handled here; this enforces structural stage boundaries.
    """
    pre_fn: Optional[PreHandler] = None
    core_fn: Optional[CoreHandler] = None
    post_fn: Optional[PostHandler] = None

    if callable(handler):
        core_fn = handler  # type: ignore[assignment]
    elif is_pipeline_handler(handler):
        pre_fn = handler.get("pre")
        core_fn = handler.get("core")
        post_fn = handler.get("post")
    else:
        raise TypeError("Unsupported handler type for circuit execution")

    # PRE
    core_input = dict(input_payload)
    if pre_fn is not None:
        pre_patch = pre_fn(node_id, node_raw, dict(core_input))
        core_input = _merge(core_input, pre_patch)

    # CORE (required)
    if core_fn is None:
        raise ValueError("Pipeline handler missing 'core'")
    core_output = core_fn(node_id, node_raw, dict(core_input))

    # POST
    final_output = dict(core_output)
    if post_fn is not None:
        post_patch = post_fn(node_id, node_raw, dict(final_output))
        final_output = _merge(final_output, post_patch)

    return final_output
