# Nexa Claude Model Usage Policy

## Two Tier Model Strategy

Claude must be used with two models.

| Role              | Model  |
| ----------------- | ------ |
| Code generation   | Haiku  |
| Complex reasoning | Sonnet |

---

## Haiku Tasks

* simple code generation
* test creation
* dataclass creation
* single file edits
* CLI argument addition

---

## Sonnet Tasks

* multi-file refactor
* contract modification
* runtime architecture change
* plugin system modification
* complex debugging

---

## Rule

Never use Haiku for architecture decisions.
