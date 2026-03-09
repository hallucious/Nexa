======================================================================
Hyper-AI User Profile (Preset) Specification v0.1
(사용자 단일 선택 → 프롬프트/정책/런타임 일괄 적용 규칙)
======================================================================

목적:
사용자가 동일한 의미의 결정을 두 번 하지 않도록 한다.
단 한 번의 "프로필 선택"으로
프롬프트 설정 + 정책 엔진 설정 + 런타임 설정을 일관되게 적용한다.

----------------------------------------------------------------------
1. 핵심 원칙

1) 사용자는 한 번만 선택한다.
2) 동일 의미의 옵션을 프롬프트와 게이트에서 중복 선택하지 않는다.
3) 프로필은 "설정 번들(config bundle)"이다.
4) 프로필은 내부 매핑 테이블을 통해 적용된다.
5) 프로필은 Definition 구조를 변경하지 않는다.
6) 프로필은 실행 설정에만 영향을 준다.

----------------------------------------------------------------------
2. 적용 계층

User Profile은 다음 3계층에 동시에 적용된다:

2.1 Prompt Layer
- temperature
- verbosity level
- reasoning depth
- evidence requirement
- output style

2.2 Runtime Layer
- max_tokens
- timeout_ms
- retry_count
- parallel_limit

2.3 Policy Layer
- max_total_cost
- sandbox_plugins
- allowed_model_list
- risk_filter_level

----------------------------------------------------------------------
3. 기본 프로필 예시 (v0.1 제안)

3.1 FAST
- 목적: 빠른 응답
- Prompt:
    temperature: 0.7
    reasoning_depth: low
    evidence_required: false
- Runtime:
    max_tokens: low
    timeout_ms: short
    retry_count: 0
- Policy:
    max_total_cost: low
    sandbox_plugins: true

3.2 BALANCED
- 목적: 속도와 품질 균형
- Prompt:
    temperature: 0.5
    reasoning_depth: medium
    evidence_required: optional
- Runtime:
    max_tokens: medium
    timeout_ms: medium
    retry_count: 1
- Policy:
    max_total_cost: medium
    sandbox_plugins: true

3.3 ACCURATE
- 목적: 정확도/안정성 우선
- Prompt:
    temperature: 0.2
    reasoning_depth: high
    evidence_required: true
- Runtime:
    max_tokens: high
    timeout_ms: long
    retry_count: 2
- Policy:
    max_total_cost: high
    sandbox_plugins: strict
    risk_filter_level: high

3.4 LOW_COST
- 목적: 비용 최소화
- Prompt:
    temperature: 0.4
    reasoning_depth: low
    evidence_required: false
- Runtime:
    max_tokens: minimal
    timeout_ms: short
    retry_count: 0
- Policy:
    max_total_cost: strict_low

3.5 SAFE_MODE
- 목적: 보안 및 정책 우선
- Prompt:
    temperature: 0.3
    reasoning_depth: medium
- Runtime:
    retry_count: 0
- Policy:
    sandbox_plugins: strict
    network_access: disabled
    risk_filter_level: maximum

----------------------------------------------------------------------
4. 매핑 구조 (내부 모델)

profile_id → config_bundle

config_bundle 구조 예:

{
  "prompt_config": {...},
  "runtime_config": {...},
  "policy_config": {...}
}

Runtime은 profile_id를 직접 해석하지 않는다.
반드시 config_bundle로 변환 후 실행한다.

----------------------------------------------------------------------
5. 충돌 방지 규칙

1) Definition에 명시된 설정이 있는 경우,
   profile_config가 우선 적용되되,
   정책 상한을 초과할 수 없다.

2) 사용자가 세부 설정을 수동 변경하면,
   해당 항목은 profile override 상태가 된다.

3) profile 변경 시 override 항목은 유지 여부를 명확히 표시해야 한다.

----------------------------------------------------------------------
6. 금지 규칙

- 동일 의미 옵션을 두 곳에서 노출하지 않는다.
- profile 없이 직접 정책을 노출하지 않는다 (일반 사용자 모드).
- profile 적용 시 내부 설정을 암묵적으로 변경하지 않는다.
- profile이 구조(Definition)를 변경해서는 안 된다.

----------------------------------------------------------------------
7. 확장 전략

- 조직별 커스텀 프로필 생성 가능
- 실행 기록 기반 자동 추천 프로필 도입 가능
- 비용 초과 시 자동 SAFE_MODE 전환 옵션 가능

----------------------------------------------------------------------
8. 철학 요약

1) 사용자는 한 번만 결정한다.
2) 프로필은 설정 묶음이다.
3) 구조는 변하지 않는다.
4) 정책은 항상 강제된다.
5) 단순함은 설계에서 나온다.

======================================================================
End of Document
======================================================================