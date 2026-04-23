[DESIGN]
[UI_MULTILINGUAL_LOCALIZATION_ARCHITECTURE v0.1]

1. PURPOSE

This document defines the official multilingual localization direction for Nexa UI.

Its purpose is to ensure that:

- UI language expansion is supported without distorting engine truth
- app language, AI response language, and locale formatting remain explicitly separated
- localization remains UI-owned rather than engine-owned
- multilingual growth can happen incrementally rather than through late-stage rewrites

This specification extends the current UI architecture package.
It does not replace the existing engine/UI boundary.

2. POSITION IN NEXA

Official structure remains:

Nexa Engine
→ UI Adapter / View Model Layer
→ UI Module Slots
→ Theme / Layout Layer

Multilingual support belongs to the UI side of this structure.
It must not redefine:

- structural truth
- approval truth
- execution truth
- storage lifecycle truth
- canonical machine-facing values

3. CORE DECISION

Nexa UI must be multilingual-capable from the beginning of UI implementation.

Official rule:

- i18n-ready architecture must exist now
- full language rollout does not need to happen now
- v1 language support should stay narrow
- canonical engine/storage values must remain language-neutral

Recommended v1 languages:

- Korean
- English

4. LANGUAGE LAYERS

Nexa must distinguish four language layers.

4.1 App UI Language
- menus
- buttons
- labels
- panel titles
- help text
- navigation text

4.2 User-Facing System Message Language
- warnings
- errors
- validation text
- confirmation prompts
- empty-state copy

4.3 AI Response Language
- Designer explanations
- analysis output
- suggestions
- summaries
- repair explanations

4.4 Locale Formatting Layer
- date/time formatting
- number formatting
- pluralization behavior
- sorting/collation behavior
- currency/measurement formatting if added later

These four layers are related, but not identical.

5. CORE PRINCIPLES

5.1 Localization is a view concern
Changing UI language must not change execution semantics.

5.2 Canonical internal values remain untranslated
Examples:
- working_save
- commit_snapshot
- blocked
- warning
- approved
- reason_code
- provider_id
- plugin_id

5.3 UI text must be key-based
UI strings must resolve through translation keys, not hardcoded scattered text.

5.4 Fallback behavior must be deterministic
Missing translations must fall back in a predictable order.

5.5 Layout must tolerate language expansion
The UI must assume translated strings can become longer or shorter.

5.6 Localization must remain modular
Translation resources must be updateable without changing engine contracts.

5.7 Localization must remain incremental
New languages must be addable without redesigning the whole UI stack.

6. WHAT MUST BE LOCALIZED

Must be localized:
- product chrome text
- panel labels
- action labels
- standard validation labels
- standard runtime state labels
- confirmation text
- onboarding/help copy
- standard empty states

Must remain canonical internally and only be localized at presentation time:
- status values
- reason codes
- node ids
- plugin ids
- provider ids
- savefile role values
- raw path expressions
- machine-facing contract literals

7. STORAGE / CONTRACT BOUNDARY

Localization must not contaminate:
- `.nex` structural truth
- commit snapshot truth
- execution record truth
- validation reason codes
- runtime status semantics

Translated labels belong in UI/view-model rendering.
They do not belong in the engine source of truth.

8. AI OUTPUT LANGUAGE RULE

AI response language must remain separately configurable in principle.

App language and AI response language must not be treated as the same field by architecture.

9. V1 IMPLEMENTATION DIRECTION

V1 should include:
- translation key system
- language settings model
- locale-aware formatting
- Korean and English resources
- deterministic fallback
- no hardcoded scattered product text

V1 does not need:
- broad language-pack marketplace
- automatic machine-translation pipeline
- RTL-first support
- region-by-region compliance localization

10. FINAL DECISION

Nexa UI must be designed as multilingual-capable from the start.

The correct strategy is:
- keep engine truth language-neutral
- localize through UI-owned resources
- separate app language from AI response language
- begin with Korean and English
- expand later through evidence-driven growth
