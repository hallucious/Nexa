Spec ID: provider_abstraction_contract
Version: 1.0.0
Status: Deprecated
Category: history
Depends On:

DOCUMENT
Provider Abstraction Contract v1

PURPOSE
ExecutionConfig 기반 엔진에서 AI 모델 제공자(OpenAI, Anthropic, Google, Local model 등)를 동일한 인터페이스로 호출하기 위한 표준 계약을 정의한다. 이 계약은 NodeExecutionRuntime과 Provider 구현 사이의 안정적인 경계를 제공한다.

SCOPE
본 계약은 다음 구성요소의 인터페이스를 정의한다.

1. ProviderRequest
2. ProviderResult
3. ProviderError
4. ProviderRegistry
5. ProviderExecutor
6. Runtime Integration Contract

본 계약은 provider 내부 구현(OpenAI SDK 등)을 규정하지 않으며, runtime과 provider 사이의 데이터 교환 형식만 정의한다.

PROVIDER REQUEST MODEL

ProviderRequest

필드

provider_id  
string  
provider registry에 등록된 provider 식별자

prompt  
string  
모델에 전달되는 최종 렌더링된 prompt

context  
dict  
추가 실행 context  
예:  
- conversation history  
- system metadata  
- runtime environment

options  
dict  
generation 옵션

예

temperature  
max_tokens  
top_p  
stop  
response_format

metadata  
dict  
runtime이 전달하는 메타 정보

예

node_id  
execution_id  
timestamp  
trace flags

REQUEST EXAMPLE

{
  "provider_id": "openai:gpt-4.1",
  "prompt": "Explain the theory of relativity.",
  "context": {},
  "options": {
    "temperature": 0.2,
    "max_tokens": 300
  },
  "metadata": {
    "node_id": "qa_node"
  }
}

PROVIDER RESULT MODEL

ProviderResult

필드

output  
any  
provider가 반환한 primary 결과

raw_text  
string  
모델이 생성한 raw text

structured  
dict | None  
JSON / structured output

artifacts  
list  
runtime artifact

예

provider_output  
tool_calls  
intermediate reasoning

trace  
dict  
provider execution trace

예

provider name  
latency  
token usage

error  
ProviderError | None  
provider 오류

RESULT EXAMPLE

{
  "output": "Relativity is a theory developed by Einstein...",
  "raw_text": "Relativity is a theory developed by Einstein...",
  "structured": null,
  "artifacts": [],
  "trace": {
    "provider": "openai",
    "model": "gpt-4.1",
    "latency_ms": 820,
    "usage": {
      "prompt_tokens": 120,
      "completion_tokens": 80
    }
  },
  "error": null
}

PROVIDER ERROR MODEL

ProviderError

필드

type  
string

가능한 값

provider_unavailable  
rate_limited  
timeout  
invalid_request  
policy_block  
provider_internal_error

message  
string

retryable  
boolean

예

{
  "type": "rate_limited",
  "message": "OpenAI rate limit exceeded",
  "retryable": true
}

PROVIDER REGISTRY

ProviderRegistry는 provider_id → provider implementation 매핑을 담당한다.

기능

register(provider_id, provider)  
resolve(provider_id)

예

provider_registry.register("openai:gpt-4.1", OpenAIProvider())

provider = provider_registry.resolve("openai:gpt-4.1")

PROVIDER EXECUTOR

ProviderExecutor는 runtime과 provider 사이의 실행 adapter 역할을 수행한다.

interface

execute(request: ProviderRequest) -> ProviderResult

예

result = provider_executor.execute(request)

RUNTIME INTEGRATION CONTRACT

NodeExecutionRuntime은 ExecutionConfig의 provider_ref를 기반으로 provider를 호출한다.

실행 흐름

ExecutionConfig  
↓  
provider_ref  
↓  
ProviderRegistry.resolve()  
↓  
ProviderExecutor.execute()  
↓  
ProviderResult  
↓  
NodeExecutionRuntime output mapping

FLOW DIAGRAM

ExecutionConfig  
↓  
NodeExecutionRuntime  
↓  
ProviderRegistry  
↓  
ProviderExecutor  
↓  
Provider  
↓  
ProviderResult  
↓  
Runtime output

MINIMUM CONTRACT TESTS

1. provider registry resolve 테스트  
2. provider request → result 정상 반환 테스트  
3. provider error surface 테스트  
4. runtime integration 테스트  
5. structured output 처리 테스트

NON-GOALS

본 계약은 다음을 포함하지 않는다.

1. Prompt rendering  
2. Plugin execution  
3. Tool execution  
4. Conversation state 관리  
5. Provider SDK 구현

EXPECTED BENEFITS

1. provider 변경 시 runtime 영향 최소화  
2. multi-provider 지원  
3. 테스트 가능한 provider contract 확보  
4. ExecutionConfig 기반 node 실행 안정화  
5. 향후 tool / agent 기능 확장 기반 제공