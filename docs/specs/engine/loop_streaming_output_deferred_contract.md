# Loop Streaming Output Deferred Contract v0.1

## Recommended save path
`docs/specs/engine/loop_streaming_output_deferred_contract.md`

## 1. Status

Deferred.

This document preserves the future streaming-output policy for loop execution.
It does not authorize LoopNode implementation.

## 2. Purpose

This document defines how future loop execution must project incremental output if LoopNode support is later introduced.

It exists because execution streaming is already a first-class contract in Nexa, but loop streaming has additional ambiguity:

- an iteration may stream
- the loop may have accumulated partial output
- the loop may stop or continue
- final output exists only after termination

## 3. Core Decision

Future loop streaming must distinguish four layers:

1. resource stream inside an iteration
2. iteration-level partial output
3. loop-level accumulated partial output
4. final loop output

UI must not collapse these layers into a fake final answer.

## 4. Event Families

Future loop streaming should define events such as:

- loop_stream_opened
- loop_iteration_stream_opened
- loop_iteration_stream_chunk
- loop_iteration_partial_output_updated
- loop_accumulated_partial_output_updated
- loop_stop_condition_evaluated
- loop_iteration_stream_completed
- loop_stream_completed
- loop_stream_failed
- loop_stream_cancelled

All events must preserve run identity, node identity, loop identity, and iteration identity.

## 5. Partial vs Final Rules

Rules:

1. A chunk is not an iteration output.
2. An iteration output is not a loop output.
3. A loop partial output is not final output.
4. Final loop output may be emitted only after termination policy resolves.
5. Cancellation must say whether it cancelled a stream, an iteration, or the whole loop.
6. Failure must say whether it failed a stream, an iteration, or the whole loop.

## 6. Trace Requirements

Trace must preserve:

- loop stream sequence
- iteration stream sequence
- partial output revision sequence
- stop-condition evaluation timing
- finalization timing
- cancellation/failure boundaries

## 7. Artifact Requirements

If loop streaming produces artifacts:

- streaming previews must be marked non-final
- per-iteration artifacts must be iteration-scoped
- accumulated partial artifacts must be explicitly partial
- final artifacts must be produced only after loop termination
- no partial artifact may overwrite a final artifact

## 8. UI Requirements

UI must label loop streaming surfaces clearly:

- Iteration 2 streaming
- Partial loop result
- Waiting for stop condition
- Final loop result
- Cancelled iteration
- Cancelled loop

Beginner UI may compress labels, but may not state that a loop is complete before engine finalization.

## 9. Final Statement

Loop streaming is not ordinary provider streaming repeated several times.
It requires explicit iteration identity, partial/final boundaries, and stop-condition visibility.
