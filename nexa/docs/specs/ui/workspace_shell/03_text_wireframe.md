# Text Wireframe v1

## Recommended save path
`docs/specs/ui/workspace_shell/03_text_wireframe.md`

## 1. Purpose

This document turns the abstract shell into a literal text wireframe.

It fixes what should be on the screen at the same time in the main desktop shell.

## 2. Canonical desktop wireframe

```text
TOP BAR
Nexa ▸ Workspace: strategy_review_v3     Role: Working Save     Status: 2 Blocked / 4 Warnings / Idle
[Save] [Run] [Review] [Commit] [Undo] [Redo]      Mode: [Build] [Review] [Run]      Search / Quick Jump

LEFT RAIL / LEFT PANEL        CENTER GRAPH WORKSPACE                                 RIGHT STACK
[Outline]                     Graph Title: strategy_review_v3                         [Inspector] [Designer]
- Inputs                      Lens: None                                              Inspector
- Outputs                     Zoom: 85%                                               Selected: Final Judge
- Nodes                                                                              Kind: provider
- Groups                      ○ Input.question                                        Status: warning
                              │
[Templates]                   ▼                                                       Summary
- Personal                ┌───────────────┐     ┌──────────────────┐                  - provider: claude
- Shared                  │ Draft Gen     │────▶│ Review Bundle    │──────────┐       - model: claude-review
- Recent                  │ ok            │     │ blocked          │          │
                          └───────────────┘     └──────────────────┘          │       Editable Fields
[Lenses]                                               │                      ▼       - prompt_ref
- Dependency                                           ▼                  ┌────────┐  - provider model
- Error                                          ┌──────────────┐         │ Output │
- Provider                                       │ Final Judge  │────────▶│ final  │
- Artifact                                       │ warning      │         └────────┘
- Security                                       └──────────────┘

BOTTOM DOCK
[Validation] [Execution] [Trace] [Artifacts] [Diff]
Validation: 2 blocking findings, 4 warnings
1. Missing approval gate before final output
2. Output binding unresolved in Review Bundle
```

## 3. Reading the wireframe

The wireframe encodes the following operational rules:

- the graph remains visible while diagnostics are visible
- selection drives the right side
- dense evidence lives in the bottom dock
- navigation and interpretation tools sit on the left
- storage role is always visible at the top
- mode is always visible at the top

## 4. Why this wireframe matters

Without a literal wireframe, the shell can drift into vague language.
This text freezes the practical composition enough to judge later implementations against it.

## 5. Non-goals

This wireframe does not define:
- color semantics
- exact component spacing
- mobile layout
- animation behavior

It only defines the canonical desktop shell arrangement.
