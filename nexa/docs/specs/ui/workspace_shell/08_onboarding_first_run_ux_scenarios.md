# Onboarding / First-Run UX Scenarios v1

## Recommended save path
`docs/specs/ui/workspace_shell/08_onboarding_first_run_ux_scenarios.md`

## 1. Purpose

This document defines the first-use experience.

The first-run goal is not to explain the whole product.
It is to make the product's operating model intelligible without fear.

## 2. Four things first-run must teach

1. Nexa is graph-based
2. AI can propose a draft
3. proposals are reviewed before they become accepted structure
4. runs are observable, not black boxes

## 3. Main first-run confusions to prevent

### Save vs Commit
Users will assume they are the same if the UI does not teach otherwise.

### Designer vs direct mutation
Users will assume AI edits structure immediately if preview and approval are not explicit.

### Run = "just get an answer"
Users must understand that run state, trace, and artifacts matter.

### blocked vs failed
Validation-blocked and execution-failed must not blur.

## 4. First-run shell default

- Build mode
- Working Save visible
- Beginner density
- graph empty state visible
- Designer input easy to find
- minimal validation shown
- no dense trace/diff by default

## 5. Recommended first-run flow

1. open empty workspace
2. ask for a simple circuit
3. show preview, not immediate mutation
4. approve into Working Save
5. show graph and a small set of editable details
6. run
7. show result and one clear path into trace/artifact if needed

## 6. Wrong first-run patterns

- full dense expert shell immediately
- forcing users to hand-wire from an empty graph
- hiding storage role
- hiding preview/precheck
- using modal tutorial spam instead of contextual help
