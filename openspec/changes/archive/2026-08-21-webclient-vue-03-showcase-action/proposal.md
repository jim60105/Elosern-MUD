## Why

This is change **B2** (showcase wave, depends on **B1**; the Wave B serial chain) of the Vue SPA
WebClient migration (see the migration roadmap at
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`). B1 built the core
narrative family and seeded the component-coverage manifest. This change builds the **action-dock
family** — the finite, keyboard-and-pointer-actionable menu surface — as documented, offline,
component-tested SFCs, and extends the required-component manifest with that family.

## What Changes

- SFCs + Storybook stories + Vitest tests for the action-dock family: `ActionDock`, `DockMenu`/
  `DockMenuItem`, `OptionCard`/`ChoiceCardRow`, `ChoicePointBlock` — driven by mock `context_actions` v5
  data, exposing the preserved `action-`/`target-` item keys and a stable `data-testid` on every
  interactive cell, rendering option/choice cards in the exact server-authored shape, and ready/generating
  choice-point states.
- The required-component manifest is **extended** with the action-dock family (the Wave B serial
  coordination point).
- A new per-family requirement on `webclient-component-showcase` documenting the action-dock contract.

## Capabilities

### New Capabilities
(none — `webclient-component-showcase` was introduced in B1.)

### Modified Capabilities
- `webclient-component-showcase`: adds the action-dock family requirement (finite, keyboard-and-pointer
  actionable; exact card shape; no invented action/target).

## Impact

- **New:** `web/webclient-app/components/` + `stories/` + Vitest tests for the action-dock family; the
  manifest extended with those keys.
- **Preserved:** the `context_actions` contract (rendered via the mock slice); no store, transport, mount,
  or other-family work.
