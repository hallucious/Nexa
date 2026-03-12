# execution_debugger_contract.md
Version: 1.0
Status: Draft
Location: docs/specs/execution_debugger_contract.md

------------------------------------------------------------
1. Purpose
------------------------------------------------------------

Execution Debugger는 Nexa 실행(run) 결과를 분석하기 위한
읽기 전용(debug-only) 분석 계층이다.

이 계층은 실행 상태를 변경하지 않으며,
run 데이터를 기반으로 다음 정보를 구조화하여 제공한다.

- node 실행 상태
- artifact 생성 경로
- execution timeline
- failure 분석
- artifact dependency 경로

Execution Debugger는 다음 시스템의 기반이 된다.

- CLI debug tools
- visual execution inspector
- execution failure diagnosis
- audit analysis

------------------------------------------------------------
2. Design Principles
------------------------------------------------------------

ExecutionDebugger는 다음 원칙을 따른다.

1. Read-only

디버거는 실행 상태를 변경하지 않는다.

- node 상태 수정 금지
- artifact 수정 금지
- provenance 수정 금지

2. Deterministic

동일 run_data 입력은 항상 동일한 결과를 반환해야 한다.

3. Structured Output

모든 결과는 JSON-serializable dict 형태로 반환한다.

4. No Exceptions for Missing Objects

node/artifact가 존재하지 않는 경우 예외 대신
구조화된 not-found 응답을 반환한다.

------------------------------------------------------------
3. Input Contract
------------------------------------------------------------

ExecutionDebugger는 다음 run_data 구조를 입력으로 받는다.

run_data = {
    "run_id": str,

    "timeline": [
        {
            "event": str,
            "node_id": str,
            "ts": str
        }
    ],

    "nodes": {
        node_id: {
            "status": str,
            "inputs": [artifact_id],
            "outputs": [artifact_id]
        }
    },

    "artifacts": {
        artifact_id: {
            "producer": node_id,
            "depends_on": [artifact_id]
        }
    },

    "provenance": {
        "artifacts": {
            artifact_id: {
                "produced_by": node_id,
                "depends_on": [artifact_id]
            }
        }
    }
}

------------------------------------------------------------
4. API Surface
------------------------------------------------------------

ExecutionDebugger는 다음 메서드를 제공한다.

trace_node(run_data, node_id)

trace_artifact(run_data, artifact_id)

inspect_timeline(run_data)

analyze_failure(run_data)

dependency_path(run_data, artifact_id)

------------------------------------------------------------
5. Output Contracts
------------------------------------------------------------

5.1 trace_node

{
  "node_id": str,
  "found": bool,

  "status": str,
  "inputs": [artifact_id],
  "outputs": [artifact_id],

  "timeline": [
      {
          "event": str,
          "ts": str
      }
  ],

  "summary": {
      "started": bool,
      "finished": bool,
      "failed": bool
  }
}

not found:

{
  "node_id": str,
  "found": false,
  "reason": "node_not_found"
}

------------------------------------------------------------
5.2 trace_artifact

{
  "artifact_id": str,
  "found": bool,

  "produced_by": node_id,
  "depends_on": [artifact_id],

  "downstream_nodes": [node_id],

  "summary": {
      "is_source": bool,
      "has_dependencies": bool
  }
}

not found:

{
  "artifact_id": str,
  "found": false,
  "reason": "artifact_not_found"
}

------------------------------------------------------------
5.3 inspect_timeline

{
  "event_count": int,

  "events": [
      {
          "index": int,
          "event": str,
          "node_id": str,
          "ts": str
      }
  ],

  "summary": {
      "nodes_started": int,
      "nodes_finished": int,
      "nodes_failed": int
  }
}

------------------------------------------------------------
5.4 analyze_failure

{
  "has_failure": bool,

  "failed_nodes": [
      {
          "node_id": str,
          "reason_code": str,
          "missing_artifacts": [artifact_id],
          "upstream_path": [node_id]
      }
  ],

  "summary": {
      "failed_node_count": int,
      "primary_failed_node": node_id | null
  }
}

------------------------------------------------------------
5.5 dependency_path

{
  "artifact_id": str,
  "found": bool,

  "path": [
      {
          "type": "node" | "artifact",
          "id": str
      }
  ],

  "summary": {
      "hop_count": int,
      "source_artifact_ids": [artifact_id]
  }
}

------------------------------------------------------------
6. Reason Code Catalog
------------------------------------------------------------

ExecutionDebugger는 다음 failure reason_code를 사용한다.

node_not_found

artifact_not_found

missing_input_artifact

upstream_node_failed

node_execution_failed

timeline_incomplete

provenance_missing

------------------------------------------------------------
7. CLI Interface (Optional Layer)
------------------------------------------------------------

CLI layer는 ExecutionDebugger를 래핑한다.

예시 명령:

nexa debug node <run_file> <node_id>

nexa debug artifact <run_file> <artifact_id>

nexa debug timeline <run_file>

nexa debug failure <run_file>

------------------------------------------------------------
8. Backward Compatibility
------------------------------------------------------------

ExecutionDebugger 출력 구조는
minor version 변경 전까지 유지되어야 한다.

새 필드는 추가 가능하지만
기존 필드는 삭제하거나 의미를 변경할 수 없다.

------------------------------------------------------------
9. Relationship With Other Systems
------------------------------------------------------------

ExecutionDebugger는 다음 시스템과 연결된다.

Execution Timeline

Execution Provenance Graph

Execution Audit Pack

Run Comparator

------------------------------------------------------------
10. Future Extensions
------------------------------------------------------------

Step171
Debug contract stabilization

Step172
Execution visualization substrate

Step173
Failure explanation layer

Step174
Debug bundle export

Step175
Execution debug report

------------------------------------------------------------
END OF SPEC
------------------------------------------------------------