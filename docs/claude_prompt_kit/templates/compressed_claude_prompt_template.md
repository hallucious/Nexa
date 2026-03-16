# Compressed Claude Prompt Template v1

```
[CLAUDE TASK — NEXA]

Claude Model: <Haiku / Sonnet>
Reason: <why this model>

Follow rule files strictly.

--------------------------------

[SESSION STATE CARD]

Mode: <DISCUSSION / DESIGN / IMPLEMENT / DEBUG>

Current Step:
<step>

Single Objective:
<objective>

Latest Stable Commit:
<hash>

In Scope:
- <module>
- <module>

Out of Scope:
- runtime architecture
- plugin namespace
- unrelated modules

Must Preserve:
- contract compatibility
- deterministic execution

--------------------------------

[TASK CAPSULE]

Goal:
- <implementation goal>

Why:
- <reason>

Modify:
- <files>

Do:
1. <instruction>
2. <instruction>

Do Not:
- <forbidden changes>

Tests:
- <tests>

Done When:
- expected behavior
- pytest passes

--------------------------------

[OUTPUT FORMAT]

Return only:

1. change summary
2. modified file list
3. full updated file contents
4. test updates
5. implementation done checklist result
```
