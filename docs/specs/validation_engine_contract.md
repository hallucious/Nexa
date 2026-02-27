# Validation Engine Contract
Version: 1.0.0
Status: Official Contract

Purpose:
Structural Validation Engine의 출력 및 강제 책임을 정의한다.
Validation은 Execution 전에 필수이며, 실패 시 실행은 금지된다.

## Output Contract
Validation 결과는 아래를 포함해야 한다:
- success (bool)
- engine_revision (str)
- structural_fingerprint (str)
- violations[] (rule_id, severity, location, message)

success=true 조건:
- severity=error 위반이 0개일 때만 true

## Execution Dependency
- validation.success == false 이면 execute()는 거부해야 한다
- validation 결과는 Trace에 참조로 기록되어야 한다
