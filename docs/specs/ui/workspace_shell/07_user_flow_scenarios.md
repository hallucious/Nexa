# User Flow Scenarios v1

## Recommended save path
`docs/specs/ui/workspace_shell/07_user_flow_scenarios.md`

## 1. Purpose

This document defines how users actually traverse the shell.

The UI is not just a screen arrangement.
It is a set of repeatable loops.

## 2. Scenario 1 — create a new circuit

1. enter a new Workspace
2. land in Build mode, Working Save
3. choose either direct graph editing or Designer-assisted draft creation
4. if using Designer:
   - request
   - intent
   - patch
   - precheck
   - preview
5. approve or request revision
6. continue in Build mode with the updated draft
7. stabilize validation
8. move toward Review

## 3. Scenario 2 — modify an existing circuit

1. open an existing Working Save
2. either edit directly or ask Designer to modify
3. inspect touched scope
4. read diff and precheck
5. apply accepted change into Working Save
6. continue structure cleanup in Build

## 4. Scenario 3 — final review and commit

1. reach a review-ready draft
2. open Review mode
3. inspect outputs, risks, diff, and blockers
4. commit
5. create Commit Snapshot
6. confirm storage role transition clearly in the UI

## 5. Scenario 4 — execute

1. start a run
2. transition to Run mode
3. observe active node, progress, recent events
4. inspect failures via graph / trace / artifact routes
5. finish with completed / failed / partial readout
6. produce an Execution Record

## 6. Scenario 5 — post-run analysis

1. inspect final outputs
2. inspect trace
3. inspect artifacts
4. return to Build if structural change is needed

## 7. Scenario 6 — diff comparison

Compare:
- Working Save vs Commit Snapshot
- Commit vs Commit
- Execution Record vs Execution Record
- Preview vs current draft

The key behavior is:
comparison must always link back to graph objects.

## 8. Beginner and advanced difference

Beginners should see the shortest successful loop:
request → preview → approve → run → result

Advanced users should get a shorter expert loop:
edit → validate → review → commit → run → diagnose
