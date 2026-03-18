# Nexa Claude Prompt Kit v1

## 1. Purpose

This kit standardizes how Claude is used as a coding implementation agent for the Nexa project.

Primary goals:

* Reduce Claude token usage
* Prevent structural hallucination
* Standardize coding prompts
* Maintain architectural control by human architects

Claude acts strictly as **implementation agent**.
Design authority remains with **user + ChatGPT**.

---

## 2. Core Principles

1. Always provide **clear scope**
2. Always enforce **output structure**
3. Never send unnecessary code
4. Never allow Claude to redesign architecture

Claude should only implement within clearly defined constraints.

---

## 3. Model Usage Policy

Two-tier model strategy:

| Role                         | Model         |
| ---------------------------- | ------------- |
| Code Generator               | Claude Haiku  |
| Code Auditor / Complex Tasks | Claude Sonnet |

Use Haiku for:

* simple code generation
* test generation
* single file edits
* boilerplate

Use Sonnet for:

* multi-file refactor
* contract change
* runtime changes
* debugging

---

## 4. Prompt Structure

All prompts must follow this structure:

1. Session State Card
2. Task Capsule
3. Minimal code subset
4. Output format constraint

---

## 5. Prompt Assembly Flow

1. Select model
2. Fill Session State Card
3. Fill Task Capsule
4. Attach minimal relevant files
5. Send prompt to Claude
6. Validate output with checklist

---

## 6. Folder Structure

```
docs/claude_prompt_kit/

templates/
rules/
cards/
presets/
checklists/
```

Each folder contains standardized assets for prompt construction.

---

## 7. Important Rule

Never send full codebase unless absolutely necessary.

Only include:

* modified files
* directly related tests
* required contract files
