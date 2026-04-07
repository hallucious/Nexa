[DESIGN]
[UI_INTERNATIONALIZATION_LOCALIZATION_SPEC v0.1]

1. PURPOSE

This document defines the official internationalization / localization boundary
for Nexa UI.

Its purpose is to make the following distinctions explicit and enforceable:

- UI chrome language
- system message language
- locale-aware formatting
- content-bearing text
- AI response language
- canonical engine/storage values

This specification exists because UI internationalization must not blur:

- engine-owned truth
- user-authored content
- AI-generated content
- editor chrome
- commit-safe storage

2. CORE DECISION

Nexa UI must be i18n-ready from the foundation layer onward,
but the i18n system must remain bounded.

Official rule:

- UI chrome and system messages are localized through translation keys
- canonical ids / enums / storage values are never translated at rest
- user-authored or AI-generated content is not automatically treated as UI chrome
- app language and AI response language are separate concerns
- locale-aware formatting is applied at presentation time, not stored as translated truth

3. TEXT OWNERSHIP MODEL

3.1 UI Chrome Text
Examples:
- buttons
- navigation labels
- panel section labels
- empty-state text
- tooltips
- confirmation dialog text

Rule:
UI chrome text must be sourced from locale resources by translation key.

3.2 System Message Text
Examples:
- validation messages
- execution status explanations
- disabled reasons
- commit boundary warnings

Rule:
System messages must be derived from stable internal reason codes or message ids,
then localized at presentation time.

3.3 Content-Bearing Text
Examples:
- circuit title
- node label authored by user
- artifact title/body
- AI-produced explanation text
- preview content snippets

Rule:
Content-bearing text is not automatically part of UI chrome localization.
It may be shown as-is, optionally with source-language metadata or optional translation features,
but must not be silently reclassified as locale-resource text.

3.4 Canonical Engine / Storage Values
Examples:
- working_save
- commit_snapshot
- execution_record
- success
- blocked
- reviewer
- plugin ids
- reason codes

Rule:
Canonical values remain language-neutral in code, storage, contracts, and tests.
Only the UI-facing presentation derived from them may be localized.

4. APP LANGUAGE VS AI RESPONSE LANGUAGE

These are separate settings.

4.1 App Language
Controls:
- UI chrome
- system messages
- locale formatting

Ownership:
- UI-owned preference

4.2 AI Response Language
Controls:
- language of generated explanations / drafts / analyses / suggestions

Ownership:
- request/runtime/provider/designer policy concern
- not implicitly the same as app language

Rule:
Changing app language must not silently rewrite AI response language.
Changing AI response language must not silently rewrite app language.

5. LOCALE FORMATTING RULES

Locale-aware formatting applies to presentation of:
- date
- time
- datetime
- duration
- number
- percent
- currency (if later applicable)

Rule:
Raw canonical values remain unlocalized in engine/storage models.
Formatting occurs at presentation time through locale-aware format hints.

6. TRANSLATION RESOURCE RULES

6.1 Translation keys must be stable.
6.2 English is the required fallback language.
6.3 Initial officially supported UI languages are Korean and English.
6.4 Missing translation keys must fail softly to fallback text.
6.5 Locale resources must not become a hidden source of semantic truth.

7. ADAPTER / VIEW-MODEL RULES

The UI adapter must distinguish at least three text forms:

7.1 DisplayTextRef
For UI chrome and system message text.

Recommended shape:
- text_key: string
- fallback_text: optional string
- params: optional dict[str, primitive]

7.2 ContentTextView
For user-authored or AI-authored content-bearing text.

Recommended shape:
- raw_text: string
- source_kind: enum("user", "ai", "engine", "imported", "unknown")
- source_language: optional string
- translation_state: optional enum("none", "available", "requested", "translated", "unknown")

7.3 LocaleFormatHint
For values that are formatted per locale.

Recommended shape:
- format_kind: enum("date", "time", "datetime", "duration", "number", "percent", "currency", "unknown")
- raw_value: primitive
- locale_override: optional string

8. PERSISTENCE RULES

8.1 UI-owned locale preferences may be persisted only as UI-owned state.
8.2 Resolved translated strings must not be persisted as canonical `.nex` truth.
8.3 `.nex.ui` may store app language and locale preference in Working Save.
8.4 Commit Snapshot must not carry canonical UI locale state across the commit boundary.
8.5 AI response language policy must not be stored inside `.nex.ui` unless a future explicit contract allows it.

9. LAYOUT / ACCESSIBILITY RULES

UI layout must be i18n-resilient.

Required considerations:
- longer translated strings
- truncation strategy
- responsive expansion
- icon-plus-text fallbacks
- high-contrast accessibility support

Deferred for later dedicated support:
- full RTL layout adaptation
- large-scale multi-script typography tuning

10. FORBIDDEN PATTERNS

The UI layer must not do the following:

10.1 Hardcode new user-facing chrome strings directly in implementation modules.
10.2 Store translated labels as canonical engine/storage values.
10.3 Assume app language equals AI response language.
10.4 Treat user-authored content as locale-resource text.
10.5 Translate canonical enums / ids inside saved artifacts.
10.6 Reconstruct localized messages by guessing from raw content without stable ids.

11. IMPLEMENTATION PRIORITY

The rational priority order is:

1. i18n-ready structure
2. translation-key discipline
3. locale preference persistence
4. Korean / English locale resources
5. broader language expansion later

This means Nexa should become structurally i18n-ready now,
not fully multilingual in breadth right now.
