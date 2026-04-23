from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, List
import json


@dataclass
class NodeOutputHash:
    node_id: str
    algorithm: str
    hash_value: str


@dataclass
class ExecutionHashReport:
    execution_id: str
    node_hashes: List[NodeOutputHash]


class NodeOutputHasher:
    """
    Hash a single node output using canonical JSON serialization.

    v1 scope:
    - node output only
    - sha256 only
    """

    def __init__(self, algorithm: str = "sha256"):
        if algorithm != "sha256":
            raise ValueError(f"unsupported hash algorithm: {algorithm}")
        self.algorithm = algorithm

    def _serialize(self, output: Any) -> str:
        try:
            return json.dumps(
                output,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except TypeError as exc:
            raise TypeError(
                f"node output is not JSON-serializable: {type(output).__name__}"
            ) from exc

    def hash_output(self, node_id: str, output: Any) -> NodeOutputHash:
        serialized = self._serialize(output)
        digest = sha256(serialized.encode("utf-8")).hexdigest()

        return NodeOutputHash(
            node_id=node_id,
            algorithm=self.algorithm,
            hash_value=digest,
        )


class ExecutionHashBuilder:
    """
    Build an execution-level hash report from expected node outputs.

    Input:
        execution_id
        outputs: {node_id: output}

    Output:
        ExecutionHashReport
    """

    def __init__(self, hasher: NodeOutputHasher | None = None):
        self.hasher = hasher or NodeOutputHasher()

    def build(
        self,
        *,
        execution_id: str,
        outputs: Dict[str, Any],
    ) -> ExecutionHashReport:
        node_hashes = [
            self.hasher.hash_output(node_id, output)
            for node_id, output in sorted(outputs.items())
        ]

        return ExecutionHashReport(
            execution_id=execution_id,
            node_hashes=node_hashes,
        )