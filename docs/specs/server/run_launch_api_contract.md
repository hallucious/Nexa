# Run Launch API Contract v1

## Recommended save path
`docs/specs/server/run_launch_api_contract.md`

## 1. Purpose

This document defines the canonical API contract for launching a Nexa run through the server layer.

Its purpose is to make the following boundary explicit:

- clients do not call the engine directly
- clients request a run through the server
- the server validates product-layer permissions and request shape
- the server constructs a typed engine-facing launch request
- the engine accepts or rejects the launch according to canonical engine truth
- the server returns a product-facing launch response without redefining engine semantics

This contract exists as a direct follow-up to the Engine ↔ Server Layer Boundary Contract.

## 2. Core Decision

Run launch is a server-owned product action that crosses into engine-owned execution truth through an explicit typed boundary.

Official rule:

- launch authorization is server-owned
- execution semantics are engine-owned
- the launch API must preserve that split
- product requests must never directly mutate engine internals
- launch responses must preserve whether failure came from product-layer checks or engine-layer checks

In short:

The server approves the request to ask.
The engine decides whether execution can actually start.

## 3. Position in the Overall Flow

Canonical flow:

Client
→ POST /api/runs
→ Server auth / authorization / request validation
→ EngineRunLaunchRequest
→ Engine launch acceptance or rejection
→ Run record creation / update
→ API response to client

This contract covers the `POST /api/runs` boundary.

## 4. API Endpoint

Canonical endpoint:

`POST /api/runs`

This endpoint launches a run against a canonical execution target.

## 5. Launch Target Rule

A run must launch against an explicit target.

Allowed target families:

- approved snapshot
- working save, only if policy explicitly allows it
- future bounded preview/test execution modes, only if separately designed

Recommended initial product rule:

- canonical run launch targets are approved snapshots
- working-save execution should be treated as a separate, explicitly controlled product mode if allowed at all

This keeps product execution aligned with approval and reproducibility expectations.

## 6. Request Contract

### 6.1 Product-facing request object

Recommended request shape:

    {
      "workspace_id": "ws_123",
      "execution_target": {
        "target_type": "commit_snapshot",
        "target_ref": "snap_456"
      },
      "input_payload": {
        "question": "Summarize this document and critique the result."
      },
      "launch_options": {
        "mode": "standard",
        "priority": "normal"
      },
      "client_context": {
        "source": "web",
        "request_id": "req_789"
      }
    }

### 6.2 Field semantics

#### `workspace_id`
The authenticated product workspace context.

#### `execution_target`
Specifies what the run is being launched against.

Minimum fields:
- `target_type`
- `target_ref`

#### `input_payload`
Optional structured input bound to the run request.

Important:
- this is product/request input
- it must not be treated as a hidden rewrite of the saved circuit
- the engine still decides how input enters execution context

#### `launch_options`
Bounded product-layer launch options.

Examples:
- mode
- priority
- future dry-run/test flags if explicitly allowed later

This object must remain small and policy-bounded.
It must not become a backdoor for redefining runtime semantics.

#### `client_context`
Optional metadata for observability/correlation.

Examples:
- source client
- request id
- optional user-visible correlation token

This is not runtime meaning.
It is transport/observability support.

## 7. Server-side Validation Before Engine Call

The server must validate all of the following before building the engine-facing request:

### 7.1 Authentication
The caller must be authenticated for canonical product execution.

### 7.2 Workspace authorization
The caller must be allowed to launch runs in the requested workspace.

### 7.3 Target existence
The execution target must exist.

### 7.4 Target eligibility
The target must be launchable under current product policy.

Example:
- blocked if a requested snapshot does not exist
- blocked if working-save execution is not allowed in the chosen mode

### 7.5 Product-layer quota/policy checks
The server may reject a launch before the engine is asked if product-level quota or policy rules block it.

Examples:
- usage quota exhausted
- provider access not allowed for this account/workspace
- workspace suspended or restricted

Important:
These are server/product failures, not engine execution failures.

## 8. Engine-facing Launch Boundary

### 8.1 Canonical engine request object

Recommended internal boundary object:

EngineRunLaunchRequest

Minimum fields:

- `run_request_id`
- `workspace_ref`
- `execution_target`
- `input_payload`
- `runtime_options`
- `correlation_context`
- `auth_context_ref`
- `requested_by_user_ref`

### 8.2 Boundary rules

The server may enrich the request with:
- authenticated user ref
- workspace ref
- allowed runtime policy context
- correlation metadata

The server must not inject:
- hidden structural mutations
- fake validation success
- server-invented execution status
- runtime semantics that bypass canonical engine rules

## 9. Engine Response Contract

The engine launch response must distinguish:

- accepted
- rejected_by_engine

Recommended internal response family:

EngineRunLaunchResponse
- `launch_status`: `"accepted"` | `"rejected"`
- `run_id`: optional string
- `initial_status`: optional string
- `blocking_findings`: optional list
- `engine_error_code`: optional string
- `engine_message`: optional string

Important:
If the engine rejects launch, that must remain visible as engine-owned rejection, not be flattened into a vague generic server failure.

## 10. Product-facing Success Response

Recommended success response shape:

    {
      "status": "accepted",
      "run_id": "run_001",
      "workspace_id": "ws_123",
      "execution_target": {
        "target_type": "commit_snapshot",
        "target_ref": "snap_456"
      },
      "initial_run_status": "queued",
      "links": {
        "run_status": "/api/runs/run_001",
        "run_result": "/api/runs/run_001/result"
      }
    }

### Meaning

- `status = accepted` means the launch request crossed the boundary successfully
- it does not mean the run already completed
- clients should use the returned run id to poll or subscribe for status/result

## 11. Product-facing Failure Response Families

The API must distinguish failure families clearly.

### 11.1 Product-layer rejection
Examples:
- unauthenticated
- forbidden
- workspace not found in accessible scope
- quota exhausted
- invalid request shape

Recommended response style:
- standard API error shape
- no claim that engine launch was attempted if it was not

### 11.2 Engine-layer rejection
Examples:
- validation blocked at launch boundary
- unsupported execution target state
- canonical engine refusal to start

Recommended response shape:

    {
      "status": "rejected_by_engine",
      "error_family": "engine_launch_rejection",
      "blocking_findings": [
        {
          "severity": "blocking",
          "code": "VALIDATION_BLOCKED",
          "message": "The selected target cannot be executed."
        }
      ]
    }

Important:
This must preserve that the engine, not the server, rejected the launch.

## 12. Run Record Rule

If launch is accepted, the server may create or update a run record for product continuity.

That run record may include:
- run id
- workspace id
- target ref
- requesting user ref
- created_at
- current known status
- product query metadata

But:
- the run record is not the source of execution semantics
- it is a persistence/query projection of engine-originated run truth

## 13. Idempotency and Duplicate Request Rule

Recommended rule:

- support an optional client-provided idempotency/correlation key
- repeated identical launch submissions within a bounded window should be safely handled
- duplicate transport retries must not silently create accidental duplicate runs if policy says they should collapse

Exact idempotency mechanics may be implementation-specific, but the contract should support them.

## 14. Audit / Observability Rule

The server should record:

- who requested the run
- in which workspace
- against which target
- when it was requested
- whether rejection happened before or after engine invocation
- what run id resulted if accepted

This is product observability.
It does not replace canonical engine trace.

## 15. What Must Never Happen

The following are forbidden:

1. client directly calling engine launch internals
2. server inventing a run id without actual accepted engine launch
3. server marking launch accepted when the engine rejected it
4. product request fields being treated as hidden structural mutation
5. working-save execution being silently allowed if policy does not allow it
6. flattening product-layer and engine-layer failures into one indistinguishable error bucket

## 16. Derived Contracts Needed After This

This contract should be followed by:

1. Run Status API Contract
2. Run Result API Contract
3. Artifact Persistence / Retrieval Contract
4. Trace Query Contract
5. Run Record Persistence Contract

## 17. Final Statement

The Run Launch API in Nexa is not just a button press endpoint.

It is the formal boundary where:

- product authorization ends
- canonical execution truth begins

That boundary must remain explicit if Nexa is to scale without corrupting its engine architecture.
