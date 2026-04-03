Spec ID: execution_model
Version: 1.7.0
Status: Active
Category: architecture
Depends On:

# Execution Model Spec

Scope: `src/engine/*` minimal deterministic execution semantics

## 2. Core concepts

### 2.1 Engine

An `Engine` is a directed graph defined by:

- `entry_node_id`: the starting node
- `node_ids`: all nodes in the engine
- `channels`: directed edges `src -> dst`
- `flow`: per-node flow gating rules (`FlowRule`)

### 2.2 ExecutionTrace

`Engine.execute(revision_id=...)` returns an `ExecutionTrace` that contains:

- `revision_id`, `fingerprint`
- `validation_success` and `validation` details
- `nodes[node_id] -> NodeTrace`

## 3. NodeTrace status model

Each node has:

- `node_status`: `NOT_REACHED | SUCCESS | FAILURE | SKIPPED`
- stage statuses: `pre_status`, `core_status`, `post_status` (`NOT_RUN | SUCCESS | FAILURE | SKIPPED`)

Execution stages contract (v1):

1. `pre` runs first (if present)
2. `core` runs next (if present), unless `pre` failed
3. `post` runs last (if present), even if `pre` or `core` failed
4. `post` may override the node output snapshot

## 4. FlowPolicy reachability

### 4.1 Policies

`FlowPolicy` is defined as:

- `ALL_SUCCESS`: run when **all** parents are `SUCCESS`
- `ANY_SUCCESS`: run when **any** parent is `SUCCESS`
- `FIRST_SUCCESS`: v1 deterministic semantics treat this the same as `ANY_SUCCESS`

Default policy for a node is `ALL_SUCCESS` if no `FlowRule` exists for that node.

### 4.2 Deterministic reachability rules

Given a node `N` (not the entry) with parent set `P`:

1. Parents in `NOT_REACHED` are considered **pending**.
2. A node runs when its policy is **satisfied** by current parent statuses.
3. A node becomes `SKIPPED` only when its policy becomes **impossible** to satisfy given **terminal** parent statuses.

Impossibility definition (v1):

- For `ALL_SUCCESS`:
  - if **any** parent is terminal non-success (`FAILURE` or `SKIPPED`), then `N` becomes `SKIPPED`.
- For `ANY_SUCCESS` / `FIRST_SUCCESS`:
  - if **no** parent is `SUCCESS` and **all** parents are terminal non-success (`FAILURE` or `SKIPPED`), then `N` becomes `SKIPPED`.
- Otherwise the node remains `NOT_REACHED` (defer until more parents become terminal).

## 5. Failure propagation

Failure propagation is an effect of the reachability rules:

- `ALL_SUCCESS` nodes are blocked by any upstream failure (impossible).
- `ANY_SUCCESS` nodes are **not** blocked by one upstream failure if another parent can succeed.

Reason codes (minimal, informational):

- `ENG-UPSTREAM-FAIL`: upstream failure prevents `ALL_SUCCESS`
- `ENG-UPSTREAM-NO-SUCCESS`: no upstream success can satisfy `ANY_SUCCESS`

## 6. Runtime Execution Event Surface

The engine may emit a runtime-owned execution event stream as an observability surface.
This event stream is UI-agnostic and does not replace `ExecutionTrace`.

Minimum stable event vocabulary:

- `execution_started`
- `node_started`
- `progress`
- `artifact_preview`
- `warning`
- `node_completed`
- `execution_completed`
- `execution_failed`

Rules:

1. Event ordering must follow real runtime ordering.
2. `execution_id` must be preserved across all events from the same run.
3. `node_started` / `node_completed` must use real node identity.
4. `execution_completed` is emitted only for successful run completion.
5. `execution_failed` is emitted only for failed run completion.
6. `warning` is advisory and must not redefine structural or execution truth.
7. `artifact_preview` is preview-safe observability data only and must not redefine final artifact truth.
8. The event stream is an observability surface, not the canonical replacement of `ExecutionTrace`.
