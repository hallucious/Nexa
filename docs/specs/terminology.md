# Terminology Specification
Version: 1.0.0
Status: Official Contract

Purpose:
Hyper-AI의 핵심 용어(Engine/Node/Channel/Flow/Trace 등)를 정의한다.
모든 spec은 이 용어를 기준으로 작성된다.

## Definitions
- Engine: Node와 Channel, Flow로 구성된 실행 가능한 그래프 단위(Revision/Execution/Trace를 가진다).
- Node: Engine 내부 최소 실행 단위(Pre/Core/Post 파이프라인을 따른다).
- Channel: Node 출력 → 다른 Node 입력으로 전달되는 **데이터 경로**.
- Flow: 실행 순서를 정의하는 **제어 규칙**(데이터 변형은 Channel/Node 영역).
- Revision: 구조 변경 시 생성되는 Engine의 구조 버전(불변).
- Execution: Engine 1회 실행(고유 execution_id).
- Trace: 실행 결과의 **그래프 기반** 기록(미실행 노드 포함, 불변).

## Validation Mapping
Related rule domains: ENG, NODE, CH
