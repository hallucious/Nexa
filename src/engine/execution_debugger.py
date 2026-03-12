# src/engine/execution_debugger.py

from __future__ import annotations
from typing import Any


class ExecutionDebugger:
    """
    Read-only execution debug analyzer.

    This class inspects run_data structures and returns
    structured debug information without modifying state.
    """

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def trace_node(self, run_data: dict[str, Any], node_id: str) -> dict[str, Any]:
        nodes = self._get_nodes(run_data)
        timeline = self._get_timeline(run_data)

        if node_id not in nodes:
            return {
                "node_id": node_id,
                "found": False,
                "reason": "node_not_found",
            }

        node = self._normalize_node_record(node_id, nodes[node_id])

        node_timeline = self._timeline_for_node(timeline, node_id)

        started = any(e["event"] == "node_start" for e in node_timeline)
        finished = any(e["event"] == "node_finish" for e in node_timeline)
        failed = any(e["event"] == "node_failed" for e in node_timeline)

        return {
            "node_id": node_id,
            "found": True,
            "status": node["status"],
            "inputs": node["inputs"],
            "outputs": node["outputs"],
            "timeline": node_timeline,
            "summary": {
                "started": started,
                "finished": finished,
                "failed": failed,
            },
        }

    def trace_artifact(self, run_data: dict[str, Any], artifact_id: str) -> dict[str, Any]:
        artifacts = self._get_artifacts(run_data)
        nodes = self._get_nodes(run_data)

        if artifact_id not in artifacts:
            return {
                "artifact_id": artifact_id,
                "found": False,
                "reason": "artifact_not_found",
            }

        artifact = self._normalize_artifact_record(artifact_id, artifacts[artifact_id])

        downstream_nodes = self._find_downstream_nodes(artifacts, nodes, artifact_id)

        return {
            "artifact_id": artifact_id,
            "found": True,
            "produced_by": artifact["producer"],
            "depends_on": artifact["depends_on"],
            "downstream_nodes": downstream_nodes,
            "summary": {
                "is_source": artifact["producer"] is None,
                "has_dependencies": len(artifact["depends_on"]) > 0,
            },
        }

    def inspect_timeline(self, run_data: dict[str, Any]) -> dict[str, Any]:
        timeline = self._get_timeline(run_data)

        events = []
        for i, e in enumerate(timeline):
            events.append(
                {
                    "index": i + 1,
                    "event": e.get("event"),
                    "node_id": e.get("node_id"),
                    "ts": e.get("ts"),
                }
            )

        summary = self._count_timeline_events(timeline)

        return {
            "event_count": len(events),
            "events": events,
            "summary": summary,
        }

    def analyze_failure(self, run_data: dict[str, Any]) -> dict[str, Any]:
        nodes = self._get_nodes(run_data)
        artifacts = self._get_artifacts(run_data)
        timeline = self._get_timeline(run_data)
        provenance = self._get_provenance(run_data)

        failed_nodes = self._detect_failed_nodes(nodes, timeline)

        results = []

        for node_id in failed_nodes:
            node_record = nodes.get(node_id, {})
            reason = self._infer_failure_reason(
                node_id, node_record, artifacts, provenance, timeline
            )

            results.append(reason)

        return {
            "has_failure": len(results) > 0,
            "failed_nodes": results,
            "summary": {
                "failed_node_count": len(results),
                "primary_failed_node": results[0]["node_id"] if results else None,
            },
        }

    def dependency_path(
        self, run_data: dict[str, Any], artifact_id: str
    ) -> dict[str, Any]:
        artifacts = self._get_artifacts(run_data)
        provenance = self._get_provenance(run_data)

        if artifact_id not in artifacts:
            return {
                "artifact_id": artifact_id,
                "found": False,
                "reason": "artifact_not_found",
            }

        path = self._build_dependency_path(artifact_id, artifacts, provenance)

        source_artifacts = [
            p["id"]
            for p in path
            if p["type"] == "artifact"
            and artifacts.get(p["id"], {}).get("producer") is None
        ]

        return {
            "artifact_id": artifact_id,
            "found": True,
            "path": path,
            "summary": {
                "hop_count": len(path),
                "source_artifact_ids": source_artifacts,
            },
        }

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _get_nodes(self, run_data: dict[str, Any]) -> dict[str, Any]:
        return run_data.get("nodes", {})

    def _get_artifacts(self, run_data: dict[str, Any]) -> dict[str, Any]:
        return run_data.get("artifacts", {})

    def _get_timeline(self, run_data: dict[str, Any]) -> list[dict[str, Any]]:
        return run_data.get("timeline", [])

    def _get_provenance(self, run_data: dict[str, Any]) -> dict[str, Any]:
        return run_data.get("provenance", {})

    def _normalize_node_record(
        self, node_id: str, node_record: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "status": node_record.get("status", "unknown"),
            "inputs": node_record.get("inputs", []),
            "outputs": node_record.get("outputs", []),
        }

    def _normalize_artifact_record(
        self, artifact_id: str, artifact_record: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "producer": artifact_record.get("producer"),
            "depends_on": artifact_record.get("depends_on", []),
        }

    def _timeline_for_node(
        self, timeline: list[dict[str, Any]], node_id: str
    ) -> list[dict[str, Any]]:
        return [
            {"event": e.get("event"), "ts": e.get("ts")}
            for e in timeline
            if e.get("node_id") == node_id
        ]

    def _count_timeline_events(self, timeline: list[dict[str, Any]]) -> dict[str, int]:
        started = sum(1 for e in timeline if e.get("event") == "node_start")
        finished = sum(1 for e in timeline if e.get("event") == "node_finish")
        failed = sum(1 for e in timeline if e.get("event") == "node_failed")

        return {
            "nodes_started": started,
            "nodes_finished": finished,
            "nodes_failed": failed,
        }

    def _find_downstream_nodes(
        self,
        artifacts: dict[str, Any],
        nodes: dict[str, Any],
        artifact_id: str,
    ) -> list[str]:
        downstream = []

        for node_id, node in nodes.items():
            inputs = node.get("inputs", [])
            if artifact_id in inputs:
                downstream.append(node_id)

        return downstream

    def _detect_failed_nodes(
        self, nodes: dict[str, Any], timeline: list[dict[str, Any]]
    ) -> list[str]:
        failed = []

        for node_id, node in nodes.items():
            if node.get("status") == "failed":
                failed.append(node_id)

        for e in timeline:
            if e.get("event") == "node_failed":
                node_id = e.get("node_id")
                if node_id not in failed:
                    failed.append(node_id)

        return failed

    def _infer_failure_reason(
        self,
        node_id: str,
        node_record: dict[str, Any],
        artifacts: dict[str, Any],
        provenance: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:

        inputs = node_record.get("inputs", [])

        missing = [a for a in inputs if a not in artifacts]

        if missing:
            return {
                "node_id": node_id,
                "reason_code": "missing_input_artifact",
                "missing_artifacts": missing,
                "upstream_path": [],
            }

        return {
            "node_id": node_id,
            "reason_code": "node_execution_failed",
            "missing_artifacts": [],
            "upstream_path": [],
        }

    def _build_dependency_path(
        self,
        artifact_id: str,
        artifacts: dict[str, Any],
        provenance: dict[str, Any],
    ) -> list[dict[str, str]]:

        path = []
        current = artifact_id
        visited = set()

        while current and current not in visited:
            visited.add(current)

            path.append({"type": "artifact", "id": current})

            artifact = artifacts.get(current)
            if not artifact:
                break

            producer = artifact.get("producer")

            if producer:
                path.append({"type": "node", "id": producer})

            deps = artifact.get("depends_on", [])

            if not deps:
                break

            current = deps[0]

        path.reverse()

        return path