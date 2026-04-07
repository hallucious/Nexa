[DESIGN]
[UI_LANGUAGE_SETTINGS_CONTRACT v0.1]

1. PURPOSE

This document defines the official language settings contract for Nexa UI.

Its purpose is to make language-related settings:

- explicit
- role-separated
- UI-owned
- persistence-safe
- compatible with the existing UI/state/storage boundary

2. CORE DECISION

Nexa must not collapse all language behavior into one setting.

The minimum correct model is:

- app_language
- ai_response_language
- format_locale

These may share defaults.
They must not share identity.

3. SETTING DEFINITIONS

3.1 app_language
The preferred language for the Nexa product interface.

Controls:
- menus
- buttons
- labels
- product copy
- panel headings
- standard UI-wrapped system messages

Preferred values:
- ko-KR
- en-US

3.2 ai_response_language
The preferred language for AI-generated user-facing explanations.

Controls:
- Designer explanations
- analysis summaries
- repair suggestions
- AI-authored guidance text

Preferred values for v0.1:
- ko
- en

3.3 format_locale
The preferred locale for culturally variable formatting.

Controls:
- dates
- times
- numbers
- sorting/collation
- pluralization rules when supported

Preferred values:
- ko-KR
- en-US

4. REQUIRED SEPARATION

4.1 app_language and ai_response_language must not be architecturally merged
Users may want English UI with Korean AI output, or the reverse.

4.2 app_language and format_locale must not be architecturally merged
They may follow each other by default, but must remain separately representable.

4.3 language settings are not engine truth
They are UI/policy preferences.

5. RECOMMENDED SCHEMA

language_settings:
  app_language: string
  ai_response_language: string
  format_locale: string
  inheritance:
    ai_response_language_follows_app_language: boolean
    format_locale_follows_app_language: boolean

6. INHERITANCE RULES

6.1 Initial default
- ai_response_language may default to app_language
- format_locale may default to app_language

6.2 Follow flags must be explicit
Silent hidden coupling is discouraged.

6.3 Detached overrides
If the user explicitly sets ai_response_language or format_locale, the corresponding follow flag must become false.

7. OWNERSHIP AND PERSISTENCE

Language settings are UI-owned.
They may be persisted in UI continuity state.
They must not become structural savefile truth, approval truth, or execution truth.

8. UI EXPOSURE RULES

The settings UI should expose at least:
- App Language
- AI Response Language
- Format Locale

Beginner mode may visually simplify this.
Advanced mode should expose all three explicitly.

9. FAILURE / FALLBACK RULES

Unsupported values must not crash the UI.
The system must fall back safely and preserve recoverability.

10. FINAL DECISION

Nexa language settings are a structured UI-owned contract.
A single merged language field is invalid by design.
