# UI Inspiration Map v1

## Recommended save path
`docs/specs/ui/workspace_shell/01_ui_inspiration_map.md`

## 1. Purpose

This document fixes the concrete mapping between external UI inspiration sources and Nexa UI modules.

It is not a moodboard.
It is not an aesthetic style guide.
It is a **translation map** from proven interaction patterns into Nexa's own graph-centered execution-engine UI.

The point is not to copy the look of games.
The point is to borrow the structural logic that makes complex systems legible.

## 2. Core framing

Nexa is not a generic dashboard.
It is an AI workflow / execution-engine product with the following recurring UX problem:

- users must see a graph of interconnected units
- invisible runtime state must become visible
- execution problems must be diagnosable without leaving context
- novice and expert users must coexist
- reusable workflow fragments must become first-class objects

That means the most relevant external inspiration is not ordinary CRUD SaaS.
It is complex simulation and systems-management UI.

## 3. The main UI axes Nexa must support

The inspiration map is organized around these UI axes:

1. Graph Workspace
2. Inspector
3. Validation / Alerts
4. Execution / Observability
5. Template / Reuse
6. Progressive Disclosure / Explainability
7. Policy Zone / Group Editing
8. Pre-flight / Dry Run

Every external pattern should map into one or more of those axes rather than being copied visually.

## 4. Highest-priority sources

### 4.1 Factorio
Factorio is the strongest reference for:
- inspector logic
- blueprint / template library
- production / throughput statistics
- categorized alerts
- always-available structural clarity

Best translations into Nexa:
- click a node → right-side Inspector opens with full current state
- reusable subgraph templates / blueprint library
- global execution statistics and bottleneck view
- alert rail grouped by category, not raw spam
- a live-state overlay mode comparable to an "Alt-mode" view

What must not be copied:
- industrial pixel-art style
- iconography
- dark utilitarian art direction
- concrete bar-chart aesthetics

### 4.2 Oxygen Not Included
ONI is the strongest reference for:
- overlays
- diagnostic lenses
- invisible-system visualization

Best translations into Nexa:
- dependency lens
- timing / latency lens
- error / risk lens
- artifact / lineage lens
- provider / model lens
- security / boundary lens

Key rule:
Nexa must not treat critical information as color-only data.
Lenses are interpretive overlays, not decorative recolors.

### 4.3 Crusader Kings III / Victoria 3 / Paradox lineage
These are the strongest references for:
- nested tooltip chains
- layered inspector depth
- progressive disclosure
- causal explanation UX

Best translations into Nexa:
- node output → artifact → trace → provider call → rendered prompt drill-down
- inspector sections that deepen without replacing the parent context
- aggregated causal alerts rather than flat repeated failure spam

What must not be copied:
- parchment / heraldry / grand-strategy theming
- decorative panel chrome
- over-buried critical information

### 4.4 RimWorld
RimWorld is the strongest reference for:
- contextual alert snapping
- zoning / policy groups
- simple but effective side-inspector behavior

Best translations into Nexa:
- alert click → center relevant graph object + open inspector + highlight fault
- group / zone-level policies applied to sets of nodes
- dense but calm operational control patterns

### 4.5 EVE Online
EVE is useful for:
- pre-visualization
- preflight inspection
- high-density operational diagnostics

Best translation:
A **Pre-Flight Inspector** that estimates run cost, expected time, likely bottlenecks, and risk before execution.

### 4.6 KSP
KSP contributes one especially valuable pattern:
- engineering report / pre-execution validation checklist

Best translation:
Nexa validation should behave like a launch-readiness report.
It should explain:
- what is blocked
- what is risky
- what is merely warned
- what is safe to proceed with

### 4.7 Satisfactory
Satisfactory is primarily useful for:
- categorized blueprint library
- reusable module discovery
- blueprint version awareness

Best translation:
Template library with:
- personal templates
- shared templates
- category / subcategory hierarchy
- blueprint version mismatch warnings

### 4.8 Dwarf Fortress
Dwarf Fortress is not a UI source to copy.
It is a warning source.

The lesson is simple:
- too much information shown at once destroys usability
- complexity must be layered, not dumped

## 5. Priority mapping into Nexa modules

### Graph Workspace
Borrow most heavily from:
- Factorio
- ONI
- selected Cities-style canvas reading patterns

### Inspector
Borrow most heavily from:
- Factorio entity inspector
- Paradox nested inspector logic
- RimWorld click-to-inspect simplicity

### Validation / Alerts
Borrow most heavily from:
- KSP engineering report
- RimWorld contextual alerts
- Factorio categorized alert rail

### Execution / Observability
Borrow most heavily from:
- Factorio stats
- EVE preflight / diagnostics
- ONI lenses
- Paradox drill-down explanation chains

### Template / Reuse
Borrow most heavily from:
- Factorio blueprints
- Satisfactory blueprint taxonomy

## 6. What Nexa should borrow freely

These are abstract interaction principles and should be translated aggressively:

- mode-based work surfaces
- overlay / lens switching
- reusable blueprint/template libraries
- inspector-on-selection
- grouped alert rails
- tooltip-chain reasoning
- preflight / dry-run diagnostics
- zone / policy grouping
- progressive disclosure

## 7. What Nexa must redesign

These are useful patterns but need non-trivial adaptation:

- spatial alerts from games must become graph-topology alerts
- continuous factory metrics must become discrete-run and comparative metrics
- overlay systems must be accessible and composable
- nested tooltip chains must stop before information burial
- template systems must respect savefile / snapshot / execution-record boundaries

## 8. What Nexa must avoid entirely

- decorative game theming
- playful completion theatrics
- modal tutorial spam
- progression-gated UI access
- color-only state encoding
- battle-map or world-map assumptions
- any visual copy that risks trade-dress imitation

## 9. Final recommendation

If research time is limited, the three highest-value references are:

1. Factorio
2. Oxygen Not Included
3. Crusader Kings III / Victoria 3 tooltip-and-inspector patterns

Factorio gives the best structure.
ONI gives the best lens logic.
Paradox gives the best explanation layering.

Together, they cover the hardest parts of Nexa's UI.
