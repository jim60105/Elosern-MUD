## Why

This is change **B4** (showcase wave, depends on **B3**; the Wave B serial chain) of the Vue SPA
WebClient migration (see the migration roadmap at
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`). This change builds the
**world and services family** — `LocalMap`, `ArtPanel`, and the `services`-backed `ShopPanel`/`QuestBoard`/
`LoreDrawer`/`InventoryPanel` (equipped only) — as documented, offline, component-tested SFCs, extends the
required-component manifest, and fixes the truthfulness contract: the art panel degrades to a truthful
placeholder and no surface invents data.

## What Changes

- SFCs + Storybook stories + Vitest tests: `LocalMap` (`local_map` v1 lattice, states, actionable adjacent
  nodes, legend + detail line, colorblind-safe not-color-only encoding), `ArtPanel` (cover-style 16:9 +
  contextual portrait overlay, or a truthful placeholder when unavailable), `ShopPanel` (stock/buy/sell),
  `QuestBoard` (list + detail), `LoreDrawer`, and `InventoryPanel` (equipped items only) — all driven by
  mock OOB data (`local_map`, `art`, `services`).
- A full inventory bag and a dedicated party panel are NOT built (no backing read model — roadmap §7).
- The required-component manifest is extended with this family.

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-component-showcase`: adds the map/art/services requirement (local map lattice + legend; art
  truthful placeholder; shop/quest/lore from `services`; inventory equipped-only; no invented data).

## Impact

- **New:** `web/webclient-app/components/` + `stories/` + Vitest tests for the world + services family;
  manifest extended.
- **Preserved:** the `local_map`, `art`, and `services` read models (rendered via the mock slice); no store,
  transport, mount, or other-family work.
