Nexa Architecture Constitution v1

Purpose
Nexa는 AI 간 협업을 통해 버그 발생 확률을 구조적으로 낮추는 execution engine을 구축하기 위한 시스템이다.

Nexa는 workflow tool이 아니라 execution engine platform이다.

이 문서는 Nexa의 최상위 불변 설계 규칙을 정의한다.


────────────────
1. Execution Engine Principle
────────────────

Nexa는 workflow automation 도구가 아니다.

Nexa는 다음 구조를 중심으로 동작하는 execution engine이다.

Circuit
↓
Node
↓
Execution Runtime
↓
Prompt / Provider / Plugin
↓
Artifact
↓
Trace

이 구조는 Nexa의 핵심 실행 모델이며 변경될 수 없다.


────────────────
2. Node Execution Invariant
────────────────

Node는 Nexa의 유일한 실행 단위이다.

Node 내부에서만 다음 자원이 실행될 수 있다.

prompt
provider
plugin

Circuit은 실행을 수행하지 않으며 Node 간 연결만 담당한다.


────────────────
3. Dependency Execution Rule
────────────────

Nexa의 실행은 dependency 기반이어야 한다.

허용되는 실행 방식

dependency-based execution

금지되는 실행 방식

prompt → provider → plugin
pipeline execution

Node 내부에서도 resource dependency 기반 실행을 유지한다.


────────────────
4. Artifact Immutability Rule
────────────────

Artifact는 append-only 데이터 구조이다.

기존 artifact 수정은 절대 금지한다.

허용

artifact.append()

금지

artifact.update()
artifact.replace()


────────────────
5. Deterministic Execution Rule
────────────────

같은 입력과 같은 execution configuration에서
실행 결과는 항상 동일해야 한다.

이를 위해 다음을 유지한다.

deterministic scheduling
artifact hash consistency
execution trace reproducibility


────────────────
6. Plugin Isolation Rule
────────────────

Plugin은 자신의 namespace만 write 가능하다.

허용

plugin.<plugin_id>.*

금지

prompt.*
provider.*
output.*
artifact.*

plugin은 다른 영역을 직접 수정할 수 없다.


────────────────
7. Working Context Schema Rule
────────────────

Working Context key는 다음 구조를 따른다.

<context-domain>.<resource-id>.<field>

예

input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value

이 스키마는 Nexa 전반에서 유지되어야 한다.


────────────────
8. Contract Driven Architecture
────────────────

Nexa는 contract 기반 아키텍처를 유지한다.

핵심 계약

artifact contract
plugin result contract
execution trace schema
validation engine contract
spec-version registry

구현은 항상 계약을 먼저 존중해야 한다.


────────────────
9. Spec-Version Synchronization
────────────────

문서와 코드의 버전 불일치를 허용하지 않는다.

spec 문서 변경 시

spec_versions.py
contract tests

가 동시에 업데이트되어야 한다.


────────────────
10. Observability Requirement
────────────────

모든 실행은 추적 가능해야 한다.

최소 포함 정보

execution trace
node execution record
artifact lineage
runtime metadata


────────────────
11. Engine First Development Rule
────────────────

Nexa 개발은 다음 순서를 따른다.

Engine
↓
CLI
↓
Developer tools
↓
Product features
↓
UI / Visual editor

엔진이 완성되기 전에 product 기능을 우선하지 않는다.


────────────────
12. Forbidden Architectural Patterns
────────────────

다음 구조는 Nexa에서 금지된다.

pipeline execution engine
step-list workflow model
mutable artifact storage
plugin unrestricted write access
undocumented runtime mutation


────────────────
13. Design Decision Check
────────────────

새 기능을 추가할 때 항상 다음 질문을 검사한다.

이 기능이 execution engine 모델을 깨지 않는가?
Node 중심 구조를 유지하는가?
artifact immutability를 유지하는가?
plugin isolation을 깨지 않는가?
contract system과 충돌하지 않는가?

하나라도 위반하면 설계를 수정한다.


────────────────
End of Constitution
────────────────