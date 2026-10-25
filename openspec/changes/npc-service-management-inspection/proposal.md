# Proposal

## Why

The current GM NPC reader labels capability-derived summaries as professions. Management needs honest service discovery separated from configuration diagnostics.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Present independent GM service summaries and capability/binding diagnostics without player authority or cross-frontend imports.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gm-runtime-state`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

web/gm/readers/npcs.py::_professions derives labels from components. identity_section/detail/item_of currently display duplicate profession/title rows; S removes them. services_section currently enumerates component fields. The GM frontend is web/admin-app, separate from web/webclient-app and protected by scripts/gm-import-boundary.mjs.

This is a one-engineer-day runnable slice with 4 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-title-authoring-removal
depends-on: npc-contextual-service-projection

code-conflicts: G follows N/P (therefore S) and shares GM reader/tests/docs with S/D; no game Vue import or publication protocol work is permitted. Current active authored dialogue content may share reference docs only; serialize those documentation edits.

The complete new-new and relevant active-change matrix and amendment ownership are in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md`. The approved source remains unchanged.
