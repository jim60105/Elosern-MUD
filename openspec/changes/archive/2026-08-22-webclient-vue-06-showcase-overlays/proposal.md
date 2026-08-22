## Why

This is change **B5**, the last of the offline showcase wave (depends on **B2, B3, B4**) of the Vue SPA
WebClient migration (see the migration roadmap at
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`). Building the full
overlays completes the component set, so B5 also asserts the deferred surfaces are absent and **freezes the
required-component manifest** to the complete set — the "showcase is complete before wiring" boundary the
wiring wave (C1–C4) depends on.

## What Changes

- SFCs + Storybook stories + Vitest tests for the full overlays: `MapOverlay`, `SettingsOverlay` (fonts,
  type scale, reduced-motion, text-to-HTML toggle, colorblind; emits `options.*`), `HelpOverlay`, and
  `CreationOverlay` (presets/custom/concept wizard, adult gate on **both** the age and apparent_age fields,
  activate transition; emits `creation.*`).
- Assert the deferred surfaces are **absent, not mocked**: a dedicated Party/companion panel, the intimate/
  adult status collapsible, a full inventory bag, and the event-log Toasts surface.
- **Freeze the required-component manifest** to the complete set; the component-coverage gate enforces it.

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-component-showcase`: adds the full-overlay requirement (settings `options.*`, creation
  `creation.*` + both-field adult gate, help) and the deferred-absent + manifest-frozen requirement.

## Impact

- **New:** `web/webclient-app/components/` + `stories/` + Vitest tests for the overlays; the manifest
  frozen.
- **Preserved:** the creation adult-gate invariant (both age fields rejected); the `services`/onboarding
  read models; no store, transport, mount, or legacy removal (C/D waves).
