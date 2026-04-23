[DESIGN]
[AI_RESPONSE_LANGUAGE_POLICY_SPEC v0.1]

1. PURPOSE

This document defines the official UI-facing policy for AI response language in Nexa.

Its purpose is to keep AI-generated explanations compatible with multilingual UI design without collapsing AI output language into app-language behavior.

2. CORE DECISION

AI response language is a policy preference, not a guarantee of perfect model compliance.

3. WHAT IT CONTROLS

This policy may influence:
- Designer explanations
- analysis summaries
- repair suggestions
- AI-authored help text
- assistant-style explanatory output in the UI

It does not redefine:
- canonical engine truth
- validation reason codes
- storage semantics
- machine-facing contract literals

4. RELATION TO APP LANGUAGE

app_language and ai_response_language are separate settings.
They may share defaults.
They must not be architecturally merged.

5. PREFERRED V0.1 VALUES

Preferred values:
- ko
- en

More granular values may be added later if needed.

6. POLICY APPLICATION RULE

The UI/settings layer may provide this preference to AI-facing generation paths.
The existence of the preference does not require exposing low-level prompt internals to the user.

7. COMPLIANCE RULE

If a model partially ignores the preferred language:
- treat it as degraded response compliance
- do not treat it as settings corruption
- do not silently rewrite the user’s chosen preference

8. LOCALIZATION BOUNDARY

This policy is not a substitute for UI localization.
UI localization and AI response language remain distinct subsystems.

9. STORAGE RULE

AI response language preference is UI-owned/policy-owned state.
It must not become structural savefile truth.

10. FINAL DECISION

Nexa must preserve a distinct AI response language policy layer alongside UI localization.
