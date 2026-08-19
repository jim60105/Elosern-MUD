## Why

This is change **B3** (showcase wave, depends on **B2**; the Wave B serial chain) of the Vue SPA
WebClient migration (see the migration roadmap at
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`). This change builds the
**data-family** surfaces — `StatusPanel`, `CharacterPanel`, `SkillBook` — as documented, offline,
component-tested SFCs, extends the required-component manifest with that family, and fixes the invariant
that status is never color-only and disguised statistics are display-only.

## What Changes

- SFCs + Storybook stories + Vitest tests for `StatusPanel` (gauges hp/mp/sp, counters, static traits,
  wallet, conditions + derived modifiers), `CharacterPanel` (details, equipped items, disguise, guild
  rank/merit, persona), and `SkillBook` (active/passive tabs, categories, search, category>group>skill,
  cost/target/cast detail) — driven by mock `status`/`character`/`skill` data.
- Status/health never color-only (icon/symbol + numeric value); disguised stats shown distinct from true
  traits (display-only). The intimate/adult block is NOT built (no backing field).
- The required-component manifest is extended with the data family.

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-component-showcase`: adds the status/character/skill requirement (truthful, non-color-only;
  disguise display-only vs true traits; only backed fields render).

## Impact

- **New:** `web/webclient-app/components/` + `stories/` + Vitest tests for the data family; manifest
  extended.
- **Preserved:** the `status`/`character`/`skill` read models (rendered via the mock slice); no store,
  transport, mount, or other-family work.
