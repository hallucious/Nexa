[DESIGN]
[LOCALIZATION_TEST_STRATEGY_SPEC v0.1]

1. PURPOSE

This document defines the testing strategy for multilingual UI support in Nexa.

Its purpose is to ensure that i18n behavior is not treated as cosmetic-only and that localization changes do not destabilize UI behavior or blur engine/UI boundaries.

2. TESTING GOALS

The localization test strategy must verify:
- deterministic fallback behavior
- stable key lookup behavior
- app/AI/format language separation
- no execution semantic impact from language-setting changes
- safe persistence and restore behavior
- reason-code localization integrity
- layout resilience across primary supported locales

3. REQUIRED TEST GROUPS

3.1 Resource Integrity Tests
- required key presence
- duplicate key detection
- malformed locale bundle detection
- placeholder mismatch detection

3.2 Fallback Tests
- unsupported locale fallback
- missing key fallback
- default locale fallback
- non-blank rendering guarantee

3.3 Settings Resolution Tests
- app_language resolution
- ai_response_language resolution
- format_locale resolution
- follow-flag detach behavior

3.4 Boundary Tests
- language changes do not alter engine truth
- localized text is not persisted as canonical validation/output truth
- commit-boundary stripping keeps i18n preferences out of approved structural state when appropriate

3.5 Reason-Code Localization Tests
- reason_code to localized title/body/hint mapping
- raw reason_code visibility in advanced/debug mode when applicable
- missing reason-code localization fallback behavior

3.6 Layout/UX Regression Checks
For primary supported locales:
- critical controls remain readable
- panel titles remain readable
- no destructive overflow in standard layouts
- validation/status banners remain understandable

4. V0.1 PRIMARY LOCALE SET

Primary test locales:
- ko-KR
- en-US

5. NON-GOAL

V0.1 does not require exhaustive worldwide locale coverage.
It requires a stable and extensible testing baseline.

6. FINAL DECISION

Localization in Nexa must be tested as a first-class UI contract boundary, not as a cosmetic afterthought.
