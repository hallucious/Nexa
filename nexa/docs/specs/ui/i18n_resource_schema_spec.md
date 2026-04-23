[DESIGN]
[I18N_RESOURCE_SCHEMA_SPEC v0.1]

1. PURPOSE

This document defines the official translation-resource schema for Nexa UI.

Its purpose is to ensure that localization resources are:
- predictable
- stable
- modular
- shell-replaceable
- compatible with the existing adapter/view-model boundary

2. CORE DECISION

Nexa UI text must resolve through translation keys and locale resources.
Hardcoded scattered product strings are invalid as the long-term direction.

3. RESOURCE MODEL

Preferred v0.1 resource layout:

locales/
  en-US/
    ui.json
  ko-KR/
    ui.json

Optional later split:
- validation.json
- designer.json
- execution.json
- artifacts.json

V0.1 should favor simplicity over over-sharding.

4. KEY STRUCTURE

Preferred key shape:

<domain>.<section>.<item>

Examples:
- ui.nav.home
- ui.settings.language
- ui.settings.ai_response_language
- ui.panel.validation.title
- ui.status.running
- ui.error.network_timeout
- ui.confirm.destructive_change

5. KEY RULES

5.1 Keys must be stable
5.2 Keys must be semantic, not positional
5.3 Keys must not embed literal translated text
5.4 Keys must not encode layout assumptions
5.5 Identical meaning may reuse one key
5.6 Different meaning must not share one key only because English text happens to match

6. RESOURCE ENTRY SHAPE

Minimum entry shape:

key: localized string

Optional later shape:

key:
  text: localized string
  description: translator note
  placeholders:
    - name
    - count

V0.1 should keep the canonical runtime shape simple.

7. PLACEHOLDER RULES

When placeholders exist:
- placeholder names must be stable
- placeholder names must be locale-independent
- placeholder order must not be assumed
- formatting logic must not depend on English word order

Example concept:
- ui.execution.progress = "{processed} / {total} processed"

8. RESOURCE OWNERSHIP

Translation resources are UI-owned assets.
They do not alter engine truth.
They must be consumed through the UI adapter/view-model boundary or a localization layer above it.

9. FALLBACK EXPECTATION

Every key lookup must support deterministic fallback:
- requested locale resource
- default locale resource
- stable developer-visible fallback

10. VALIDATION EXPECTATION

Resource validation should detect:
- missing required keys
- duplicate keys
- malformed placeholders
- placeholder mismatches across locales
- invalid locale bundle shape

11. FINAL DECISION

Nexa translation resources must be key-based, locale-scoped, semantically named, and UI-owned.
