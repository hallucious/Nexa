[DESIGN]
[UI_I18N_SPEC_INDEX v0.1]

1. PURPOSE

This document is the official index for the multilingual UI specification bundle in Nexa.

Its purpose is to:
- define the canonical i18n document set
- explain the role of each document
- fix the reading order
- reduce ambiguity during later implementation and integration

2. WHY THIS INDEX EXISTS

Multilingual UI support is not one isolated feature.
It crosses:
- UI architecture
- UI-owned persistence
- `.nex.ui` continuity behavior
- validation message rendering
- AI response-language policy
- testing strategy

This index organizes those concerns.

3. CANONICAL I18N SPEC BUNDLE

3.1 Architecture
Path:
    docs/specs/ui/ui_multilingual_localization_architecture.md
Role:
- defines the overall multilingual direction
- fixes language-layer separation
- protects engine truth from localization leakage

3.2 Settings Contract
Path:
    docs/specs/ui/ui_language_settings_contract.md
Role:
- defines app_language / ai_response_language / format_locale
- fixes settings separation and follow behavior

3.3 Resource Schema
Path:
    docs/specs/ui/i18n_resource_schema_spec.md
Role:
- defines translation-key/resource structure

3.4 Fallback Behavior
Path:
    docs/specs/ui/ui_i18n_fallback_behavior_spec.md
Role:
- defines deterministic locale/key fallback behavior

3.5 Localized Message Resolution
Path:
    docs/specs/ui/localized_message_resolution_spec.md
Role:
- defines canonical-to-localized message projection

3.6 Validation Reason Code Localization
Path:
    docs/specs/ui/validation_reason_code_localization_spec.md
Role:
- fixes reason-code localization boundary

3.7 AI Response Language Policy
Path:
    docs/specs/ui/ai_response_language_policy_spec.md
Role:
- separates AI output language from app UI language

3.8 Persistence Boundary
Path:
    docs/specs/ui/ui_i18n_persistence_boundary_spec.md
Role:
- defines where multilingual preferences may persist
- keeps them out of approved structural truth

3.9 Test Strategy
Path:
    docs/specs/ui/localization_test_strategy_spec.md
Role:
- defines what multilingual support must be tested for

4. RECOMMENDED READING ORDER

1. ui_multilingual_localization_architecture.md
2. ui_language_settings_contract.md
3. i18n_resource_schema_spec.md
4. ui_i18n_fallback_behavior_spec.md
5. localized_message_resolution_spec.md
6. validation_reason_code_localization_spec.md
7. ai_response_language_policy_spec.md
8. ui_i18n_persistence_boundary_spec.md
9. localization_test_strategy_spec.md

5. RELATION TO EXISTING UI SPECS

This bundle extends, and must remain compatible with, the existing UI specification stack including:
- ui_architecture_package.md
- ui_adapter_view_model_contract.md
- ui_state_ownership_and_persistence_spec.md
- ui_section_schema_spec.md
- ui_section_branch_rules_spec.md
- ui_public_api_exposure_spec.md
- ui_commit_boundary_stripping_spec.md

6. FINAL DECISION

This index is the canonical entry point for multilingual UI design in Nexa.
