# Proposal: lore-codex-schema-v2

## Batch: handbook-codex-titles (change 3 of 4)

- depends-on: lore-species-research
- conflict: `lore-species-research` edits `world/rules/lore_knowledge.py` too. This change adds `species_card` beside the writers that change introduces, and needs its `list_species_defeated` reader and the species-backed monster category.
- conflict: `handbook-codex-tab` depends on this change. It consumes the v2 payload and deletes `LoreCodexDrawer.vue`, which this change only adapts to v2. Both changes touch the `webclient-lore-codex-panel` spec. That change's deltas are written against this change's archived text.
- conflict: none with `handbook-titles-tab` (disjoint files).

## Why

The approved design `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` (D3, D4, D6, D7, §4.2) needs a payload that can draw an MHW-style tile wall. That means a total per category, placeholders in ordinal position, a grouping for monsters, stage-gated monster fields, and an art descriptor per discovered entry. The v1 `lore_codex` panel ships discovered entries only, with no totals and no art, and its non-disclosure rule forbids exactly the count and ordinal disclosure that D4 now allows.

## What Changes

- **BREAKING (wire, pre-release):** `lore_codex` moves to schema version 2 with this shape: `{schema_version: 2, available, discovered_total, total, categories: [{key, label, discovered, total, groups: [{key, label|null, slots}]}]}`. A slot is either `{placeholder: true}` or `{key, title, stage, art, card, locked_fields}`.
- Monster slots group by the species' default variant threat tier in `MONSTER_TIER_REGISTRY` order. Every other category has one group with a `null` label. Slots keep registry order.
- New `world/rules/lore_knowledge.py::species_card(species_key, stage)`, the canonical stage-gated monster renderer. While sighted it renders the name, appearance and tier, and `locked_fields` names the defeated-stage fields. Once defeated it adds description, ecology, habitat and ordinary variants. It never serializes `author_*` fields.
- Art: monsters get the existing `portrait:monster:<species>` descriptor (including the gallery-fallback terminal), regions and anchors get the existing scene descriptor of their declared `scene_archetype`, and every other category gets `null`. The presenter enqueues nothing.
- New shared bounds, mirrored in the JS validator and pinned by the parity contract: slots per category ≤ 128, total slots ≤ 512, card fields ≤ 8, field value ≤ 1024 code points, variant lines ≤ 8, groups per category ≤ 16. When the canonical payload exceeds the envelope, trailing placeholders are dropped first (last category first), then entry art is nulled from the last slot backwards. If it still does not fit, the presenter fails closed. An art-building failure nulls only that slot's art.
- The client validator (`web/static/webclient/js/elosern/protocol/panels/exotic.js`) mirrors v2 exactly. The existing `LoreCodexDrawer.vue` is adapted to read v2 (discovered slots as its entries) so the tree stays green until `handbook-codex-tab` replaces it.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `webclient-lore-codex-panel`: the version-1 schema, the discovered-only non-disclosure and the bounds requirements are removed and replaced by version-2 schema, count-and-ordinal non-disclosure, monster grouping, stage-gated monster cards, art descriptors and bounds with placeholder trimming. The canonical-renderer and entry-title requirements are modified.

## Impact

- Server: `web/webclient/presentation/lore_codex.py`, `world/rules/lore_knowledge.py` (adds `species_card`), and the existing `lore_codex` registration (`web/webclient/presentation/registry.py`, schema version only).
- Client protocol: `web/static/webclient/js/elosern/protocol/constants.js`, `protocol/panels/exotic.js`, and their node tests.
- Client view (adaptation only): `web/webclient-app/components/LoreCodexDrawer.vue`, its story fixtures and its vitest suite.
- Tests and fixtures: `tests/test_lore_codex_parity_contract.py`, `tests/test_panel_schema_version_parity_contract.py`, `web/webclient/presentation/tests/test_lore_codex_panel.py`, `web/tests/browser/browser_helpers.py::valid_lore_codex_panel`, `web/tests/browser/incremental_sync_fixture.py::oversized_payload`, and every other v1-shaped `lore_codex` fixture found by grep.
- Human-reviewed: the variant line format and the habitat separator listed in `design.md` § "Review document (human-reviewed)".
