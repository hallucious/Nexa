[DESIGN]
[UI_I18N_PERSISTENCE_BOUNDARY_SPEC v0.1]

1. PURPOSE

This document defines where multilingual UI preferences may be persisted in Nexa and where they must not cross.

Its purpose is to connect localization design with the existing UI-owned persistence boundary, `.nex.ui` section rules, and commit-boundary stripping rules.

2. CORE DECISION

Multilingual UI preferences are UI-owned persistence state.
They are not structural truth, approval truth, execution truth, or commit truth.

3. MAY BE PERSISTED

The following may be persisted as UI-owned continuity state:
- app_language
- ai_response_language
- format_locale
- language follow flags
- locale-sensitive display preferences

4. PREFERRED PERSISTENCE ZONES

Preferred persistence zones:
- UI-owned local settings
- UI continuity storage
- Working Save-side `.nex.ui` section when editor continuity matters

5. MUST NOT CROSS INTO CANONICAL COMMIT TRUTH

These settings must not cross the commit boundary as approved structural truth.
Commit snapshot artifacts must not treat editor language preferences as canonical engine meaning.

6. EXECUTION RECORD RULE

Execution records may reflect what happened during a run.
They must not become generic containers for UI language restore truth.
At most, any display-side language preference remains external or explicitly auxiliary.

7. FALLBACK RECOVERY RULE

If persisted multilingual UI state is stale or unsupported:
- restore must degrade safely
- language fallback may be applied
- engine truth must remain untouched

8. SHELL REPLACEABILITY RULE

Because UI shells/modules are replaceable, persisted i18n state must degrade safely if a future shell does not use exactly the same language-preference surface.

9. FINAL DECISION

Nexa multilingual preferences belong to the UI-owned continuity layer and must stop at the commit boundary.
