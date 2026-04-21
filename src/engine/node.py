from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from .types import NodeResult, NodeStatus, StageResult, StageStatus


class Node(Protocol):
    """Unified Node abstraction (v1).

    Contract reference: docs/specs/architecture/node_abstraction.md.
    This is an interface only. Runtime orchestration lives in Engine/Execution layer.
    """

    @property
    def node_id(self) -> str: ...

    def pre(self, *, input: Dict[str, Any], context: Dict[str, Any]) -> StageResult: ...
    def core(self, *, input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]: ...
    def post(
        self,
        *,
        input: Dict[str, Any],
        context: Dict[str, Any],
        core_output: Optional[Dict[str, Any]],
        pre: StageResult,
        core_error: Optional[BaseException],
    ) -> NodeResult: ...


@dataclass(frozen=True)
class SimpleNodeResult(NodeResult):
    """Concrete NodeResult helper for simple Nodes."""


@dataclass(frozen=True)
class SimpleStageResult(StageResult):
    """Concrete StageResult helper for simple Nodes."""


def ok_pre(meta: Optional[Dict[str, Any]] = None) -> StageResult:
    return SimpleStageResult(status=StageStatus.SUCCESS, meta=meta)


def fail_pre(reason_code: str, message: str, meta: Optional[Dict[str, Any]] = None) -> StageResult:
    return SimpleStageResult(status=StageStatus.FAILURE, reason_code=reason_code, message=message, meta=meta)


def ok_node(output: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> NodeResult:
    return SimpleNodeResult(success=True, status=NodeStatus.SUCCESS, output=output, meta=meta)


def fail_node(reason_code: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NodeResult:
    return SimpleNodeResult(success=False, status=NodeStatus.FAILURE, reason_code=reason_code, message=message, meta=meta)
