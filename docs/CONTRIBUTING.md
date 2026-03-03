# CONTRIBUTING.md (Draft) — Active Spec 변경 절차 (SoT: BLUEPRINT)

> 목적: “Active spec 변경”이 발생할 때, 문서/코드/테스트가 **항상 동기화**되도록 절차를 고정한다.  
> 프로젝트 원칙: 재현성 > 계약 안정성 > 테스트 증명 > 확장성.

---

## 1) 용어

- **Spec 문서**: `docs/specs/*.md` (각 문서는 독립 SemVer 버전을 가짐)
- **Active spec**: 현재 프로젝트에서 “계약으로 강제되는” spec 문서 집합
- **SoT(Source of Truth)**: Active spec 목록의 최종 진실 소스  
  - **SoT = `docs/BLUEPRINT.md`**
- **Index/Map**: 문서 지형도를 제공하는 인덱스 문서  
  - `docs/FOUNDATION_MAP.md`는 **BLUEPRINT의 Active spec을 그대로 반영**해야 하며, 독자적 결정권이 없다.
- **Spec-Version Sync**: Active spec의 문서 버전과 `src/contracts/spec_versions.py` 매핑이 1:1로 일치해야 한다는 계약

---

## 2) Active spec 변경의 범위 정의

아래 중 하나라도 해당하면 **Active spec 변경**으로 간주한다.

1. `docs/BLUEPRINT.md`의 “Active spec 목록”에 spec 경로를 **추가/삭제/경로 변경**
2. Active spec 문서의 `Version:` 값을 변경(= spec SemVer bump)
3. Active spec 문서 내용 변경으로 인해 **계약/동작/스키마**가 달라짐(버전 bump가 필요할 가능성이 높음)

---

## 3) 변경 유형별 규칙

### A) Active spec “추가”
**목표:** 새 spec을 Active로 만들되, 동기화 계약이 즉시 통과하도록 한다.

필수 작업(순서 고정):
1. `docs/specs/<new_spec>.md` 생성  
   - 반드시 `Version: X.Y.Z` 단 **1회만** 존재해야 한다.
2. `docs/BLUEPRINT.md`의 Active spec 목록에 `docs/specs/<new_spec>.md` 추가 (**SoT 업데이트**)
3. `docs/FOUNDATION_MAP.md`에서 동일 spec을 **Active**로 표시(블루프린트와 동일해야 함)
4. `src/contracts/spec_versions.py`의 `SPEC_VERSIONS`에 `docs/specs/<new_spec>.md: "X.Y.Z"` 추가
5. `python -m pytest -q` 실행 → **통과**해야 함

금지:
- BLUEPRINT 반영 없이 FOUNDATION_MAP만 수정
- spec 문서에 `Version:` 중복(예: `Version: 1.2.0` + `Version: v1.0.0`)

---

### B) Active spec “삭제”
**목표:** 더 이상 강제하지 않을 spec을 Active 목록에서 제거한다.

필수 작업(순서 고정):
1. `docs/BLUEPRINT.md` Active spec 목록에서 해당 경로 제거
2. `docs/FOUNDATION_MAP.md`에서도 Active 표기 제거(또는 Inactive로 전환)
3. `src/contracts/spec_versions.py`에서 해당 경로 키 제거
4. `python -m pytest -q` 통과

주의:
- 문서는 “삭제”해도 되지만, 삭제 시 BLUEPRINT/FOUNDATION_MAP/versions/테스트가 동시에 정리되어야 한다.

---

### C) Active spec “버전 bump”
**목표:** 내용 변화가 계약 변화라면 버전과 매핑이 함께 올라가야 한다.

필수 작업(순서 고정):
1. spec 문서의 `Version: X.Y.Z`를 새 버전으로 변경 (단 1회만 존재)
2. `src/contracts/spec_versions.py`의 해당 경로 값도 동일 버전으로 변경
3. `python -m pytest -q` 통과

버전 bump 가이드(문서 SemVer):
- **MAJOR**: 구조 변경/호환성 깨짐(필드 삭제/의미 반전/필수조건 강화 등)
- **MINOR**: 계약/규칙 추가(기존 호환 유지)
- **PATCH**: 표현 수정/오탈자/명확화(동작 변화 없음)

---

## 4) “Active spec 변경” PR 체크리스트 (필수)

PR에 아래 항목을 **모두** 체크해야 merge 가능.

- [ ] `docs/BLUEPRINT.md` Active spec 목록이 변경 내용을 반영했다(SoT 업데이트 완료)
- [ ] `docs/FOUNDATION_MAP.md` Active 표기가 BLUEPRINT와 **완전히 동일**하다
- [ ] spec 문서에 `Version:` 라인이 **정확히 1개**만 존재한다
- [ ] `src/contracts/spec_versions.py`의 `SPEC_VERSIONS`가 문서 버전과 **완전히 동일**하다
- [ ] `python -m pytest -q` 결과가 PASS이다 (sync 계약 테스트 포함)

---

## 5) 테스트가 보장하는 것 (변경 안전장치)

현재 프로젝트는 아래를 “테스트로 강제”한다.

1. **Spec-Version Sync Contract**  
   - Active spec 문서(= BLUEPRINT 기준)가 디스크에 존재해야 한다  
   - `SPEC_VERSIONS`에 모두 있어야 한다  
   - 문서의 `Version:`과 코드 매핑이 같아야 한다  
2. **BLUEPRINT–FOUNDATION Active Sync Contract**  
   - BLUEPRINT의 Active spec 목록과 FOUNDATION_MAP의 Active 표기는 동일해야 한다

즉, 절차를 어기면 `pytest`가 실패해야 정상이다.

---

## 6) 자주 발생하는 실패 패턴 (그리고 예방)

- 패턴 1: 문서에 `Version:`이 두 번 들어감  
  - 예방: `Version:`은 문서 상단에 1회만 유지. `v` 접두는 허용하지 않음(예: `v1.0.0` 금지)
- 패턴 2: BLUEPRINT만 고치고 FOUNDATION_MAP을 안 고침  
  - 예방: Active 변경은 항상 “BLUEPRINT → FOUNDATION_MAP → spec_versions.py → pytest” 순서 고정
- 패턴 3: spec 문서 버전만 올리고 spec_versions.py를 안 올림  
  - 예방: 버전 bump는 “문서+코드 매핑 동시 변경”이 계약

---

## 7) 최소 작업 순서(요약)

Active spec 변경이 생기면 항상:

1) `docs/BLUEPRINT.md`  
2) `docs/FOUNDATION_MAP.md`  
3) `src/contracts/spec_versions.py`  
4) `python -m pytest -q`

이 4단계를 통과하면 변경이 “정합성 유지” 상태다.

---

## 8) Active Spec 변경 절차 (필수)

## 1. 목적
Active spec 목록은 **실행 가능한 계약(contracts)의 현재 정본**을 나타냅니다.  
Active spec 변경은 “문서-코드-테스트” 3요소가 동시에 정합성을 유지해야 합니다.

## 2. Source of Truth
- **Active spec 목록의 Source-of-Truth는 `docs/BLUEPRINT.md`** 입니다.
- `docs/FOUNDATION_MAP.md`는 **BLUEPRINT의 Active spec 목록을 ‘동일하게’ 반영**하는 지도(map) 문서입니다.
- 레포는 아래 2개의 계약 테스트로 정합성을 강제합니다.
  - `tests/test_spec_version_sync_contract.py`  
    - BLUEPRINT에 Active로 선언된 모든 spec 문서가 디스크에 존재하고  
      `src/contracts/spec_versions.py`의 `SPEC_VERSIONS`와 **버전이 완전히 일치**해야 합니다.
  - `tests/test_blueprint_foundation_sync_contract.py`  
    - BLUEPRINT의 Active spec 목록과 FOUNDATION_MAP의 Active 표기가 **완전히 동일**해야 합니다.

## 3. Version 표기 규칙 (필수)
- 모든 spec 문서는 헤더에 **정확히 1개의** Version 필드를 가져야 합니다.
  - 허용: `Version: 1.2.3`
  - 금지: `Version: v1.2.3` (v 접두), Version 라인의 중복(2개 이상)
- 버전은 **SemVer(major.minor.patch)** 를 사용합니다.
- 문서 버전이 바뀌면 반드시 `src/contracts/spec_versions.py`도 함께 업데이트해야 합니다.

## 4. Active Spec 변경 절차 (체크리스트)
Active spec을 **추가/삭제/경로 변경/버전 변경**할 때는 아래 순서를 지킵니다.

1) 문서 업데이트
- `docs/BLUEPRINT.md`의 Active spec 목록을 변경
- `docs/FOUNDATION_MAP.md`에 동일 변경을 반영(Active 표기 동기화)
- 해당 spec 문서의 `Version:` 라인이 규칙을 만족하는지 확인(정확히 1개, v 접두 없음)

2) 코드 동기화
- `src/contracts/spec_versions.py`의 `SPEC_VERSIONS`에
  - (추가/삭제/경로 변경) 반영
  - (버전 변경) 반영

3) 테스트
- 로컬에서 `pytest -q` 실행
- 다음 2개 테스트가 반드시 PASS인지 확인
  - `test_spec_version_sync_contract.py`
  - `test_blueprint_foundation_sync_contract.py`

4) 커밋/푸시
- 위 3단계가 PASS인 상태에서만 커밋/푸시
- CI(GitHub Actions)에서도 동일하게 PASS해야 함

## 5. 자주 발생하는 실패 사례 (원인-해결)
- 실패: “Multiple Version fields …”
  - 원인: spec 문서에 `Version:` 라인이 2개 이상 존재
  - 해결: Version 라인을 1개만 남기고 나머지 제거
- 실패: “missing in SPEC_VERSIONS …”
  - 원인: BLUEPRINT에 Active인데 `SPEC_VERSIONS`에 매핑 누락
  - 해결: `src/contracts/spec_versions.py`에 문서 경로/버전 추가
- 실패: “BLUEPRINT but not Active in FOUNDATION_MAP …”
  - 원인: FOUNDATION_MAP 동기화 누락
  - 해결: FOUNDATION_MAP의 Active 표기를 BLUEPRINT와 동일하게 수정
