## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §9.1) replaces the boolean reduced-motion override with three motion levels: `full`, `reduced`, and `off`. Today the client has two resolvers for one question:
- the `data-reduced-motion` CSS blocks in `styles/tokens.css`
- C7's `composables/use-reduced-motion.js`

The `reduced` rule cannot be expressed with either. Both reduced-motion blocks force every `transition-duration` and `animation-duration` to 1ms with `!important`, so no fade can survive. Eight component files also hard-code durations that no token reaches. This change (C11a, the first of three C11 slices) makes the motion level a single resolved value that CSS and script both read. It defines the token vocabulary that C11b (`webclient-scene-transitions`), C11c (`webclient-mode-transitions`), and C13 (`webclient-combat-beat-playback`) consume, and it writes down the presentation-timing contract they must keep. It adds no new transition.

**Implementation profile:** logic. The work is a preference swap, token blocks, a mechanical duration sweep, and tests. Every outcome is asserted by Vitest, node, and browser checks, so no visual judgement is needed.

## What Changes

- New pure module `web/webclient-app/lib/motion_level.js` (no Vue, no DOM):
  - `MOTION_LEVELS` (`full`, `reduced`, `off`)
  - `resolveMotionLevel(stored, osRequestsReduce)`: the stored level when it is valid, else `reduced` when the OS requests it, else `full`
- **BREAKING (internal)**: delete `web/webclient-app/composables/use-reduced-motion.js` (C7). The store becomes the only resolver.
- `web/webclient-app/stores/elosern/preferences.js`:
  - `prefs.reducedMotion` and `setReducedMotion` are deleted.
  - New `prefs.motionLevel`: `null` means nothing is stored, and the OS is followed live.
  - New `setMotionLevel(level)`, which accepts only `MOTION_LEVELS`.
  - A `matchMedia("(prefers-reduced-motion: reduce)")` `change` listener re-applies the presentation. It persists nothing.
  - `applyPresentationPreferences` always writes the **effective** level to `<html data-motion="full|reduced|off">`, and `data-reduced-motion` is gone.
- `web/webclient-app/stores/elosern/view.js` publishes `motionLevel` (the effective level) and drops `reducedMotion`. `stores/elosern.js` exports `setMotionLevel` and drops `setReducedMotion`.
- `web/static/webclient/js/elosern/layout_store.js` (wrapped by `lib/layout_store.js`):
  - `CURRENT_LAYOUT_VERSION` becomes `3`.
  - `PREFERENCE_TYPES` drops `reducedMotion` and gains the optional enum `motionLevel`, and `PREFERENCE_ENUMS.motionLevel` is added.
  - A version-2 wrapper resets to the version-3 default. There is no migration.
- `web/webclient-app/components/SettingsOverlay.vue`:
  - The three-state 減少動態效果 control (預設 / 開 / 關) is replaced by a 動態效果 segment: `完整` / `減少` / `關閉`, with testids `settings-overlay-motion-{full,reduced,off}` and the emit `motion-level-change`.
  - The pressed button shows the effective level.
  - The text-speed description names the motion level.
- `web/webclient-app/components/MessageWindow.vue`: the `reducedMotion` prop becomes `motionLevel` (the effective level, default `"full"`). Typing is instant whenever the level is not `full`. `components/AppShell.vue` and `AppClient.vue` bind `store.view.motionLevel` to the window and to `SettingsOverlay`.
- `web/webclient-app/styles/tokens.css`:
  - The `data-reduced-motion` blocks are replaced by `:root[data-motion="reduced"]`, `:root[data-motion="off"]` (with a 0s `!important` rule for off only), and an OS fallback `@media (prefers-reduced-motion: reduce) { :root:not([data-motion]) … }` for Storybook and the moment before the store loads.
  - New tokens (design D3):
    - stage-transition durations `--motion-scene`, `--motion-portrait`, `--motion-actor`, `--motion-panel`, `--motion-reveal`, `--motion-clear`, `--motion-flash`, and `--motion-stagger`
    - `--motion-trail` / `--motion-trail-delay` and `--motion-spin`
    - the travel multiplier `--motion-travel`, the distances `--motion-shift-sm` / `--motion-shift-lg`, and `--motion-flash-peak`
    - the easing tokens `--ease-enter` / `--ease-exit`
- Duration sweep. The hard-coded `transition` and `animation` durations move onto tokens in:
  - `components/VitalsTrack.vue`
  - `components/LineagePanel.vue`
  - `components/CharacterSwitcher.vue`
  - `components/DockTabBar.vue`
  - `components/SkillBook.vue`
  - `components/GalleryPanel.vue`, where the private reduced-motion block is also deleted
  - `components/creation-overlay.css`

  A new Vitest guard `tests/motion_tokens.test.js` fails on any literal duration in a component `transition` or `animation`.
- `tools/gen_ansi_palette.py` and the regenerated `web/static/webclient/css/ansi_palette.css`: the `blink` class is also neutralised under `:root[data-motion="reduced"]` and `:root[data-motion="off"]`.
- Browser determinism:
  - `web/tests/browser/browser_base.py` `new_page` gains a `motion_level` argument, default `"off"`. `browser_helpers.seed_motion_level` installs an init script that writes a version-3 wrapper with that level when none is stored, so the suite runs with every change instant. The test files that open their own browser context call the same helper.
  - Tests that assert first-load defaults or typing pass `motion_level=None`.
  - New journeys cover the OS-reduced run, the explicit override, and the version-3 persistence.
- No OOB schema, presenter, server, allowlist, or component-manifest change. No component is added or deleted.

Out of scope:
- The transitions of the §9.3 table: location change, portrait crossfade, and vitals belong to `webclient-scene-transitions` (C11b). Dialogue, combat, choices stagger, and the collapse slide belong to `webclient-mode-transitions` (C11c).
- A presentation-queue module. None is added (design D6). Combat beat sequencing is `webclient-combat-beat-playback` (C13), under the contract this change specifies.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "Narrative prose scale is a client-local preference the settings surface owns" (C7 text): the motion level replaces the reduced-motion override.
  - MODIFIED "Text speed and auto-advance are client-local reading preferences the settings surface owns" (C7 text): the control names the motion level.
  - ADDED "The motion level is a client-local preference that governs every client animation"
  - ADDED "Presentation timing never gates committed state or input"
- `webclient-input-narrative`: MODIFIED "A page types in at the reader's text speed and auto-advance is opt-in" (C10c text). Typing is instant whenever the effective level is not `full`.
- `webclient-desktop-shell`: MODIFIED "Browser persistence is versioned and presentation-only" (C7 text). The current version is 3.
- `webclient-component-showcase`: MODIFIED "The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen" (main spec). The settings overlay exposes the motion level.
- `webclient-narrative-markup`: MODIFIED "The narrative palette is generated with a contrast floor and honors reduced motion" (main spec). Blink also stops under the reduced and off levels.

## Impact

- New: `web/webclient-app/lib/motion_level.js`; Vitest `web/webclient-app/tests/motion_level.test.js`, `web/webclient-app/tests/motion_tokens.test.js`, `web/webclient-app/tests/store/motion_preferences.test.js`.
- Deleted: `web/webclient-app/composables/use-reduced-motion.js`.
- Edited source:
  - `web/webclient-app/stores/elosern/{preferences,view}.js`, `web/webclient-app/stores/elosern.js`
  - `web/static/webclient/js/elosern/layout_store.js`, `web/webclient-app/main.js` (comment only)
  - `web/webclient-app/components/{SettingsOverlay,MessageWindow,AppShell,VitalsTrack,LineagePanel,CharacterSwitcher,DockTabBar,SkillBook,GalleryPanel}.vue`, `web/webclient-app/components/creation-overlay.css`, `web/webclient-app/AppClient.vue`
  - `web/webclient-app/styles/tokens.css`
  - `tools/gen_ansi_palette.py`, `web/static/webclient/css/ansi_palette.css`
  - Stories: `stories/Overlays/SettingsOverlay.stories.js`, `stories/Overlays/OverlayHost.stories.js`, `stories/Core/MessageWindow.stories.js`, `stories/Data/VitalsTrack.stories.js` (note text)
- Tests edited:
  - Vitest: `tests/overlays/settings_overlay.test.js`, `tests/message_window_typing.test.js`, `tests/store/reading_preferences.test.js`, `tests/hud_drawer.test.js`, `tests/world/inventory_panel.test.js` (comments)
  - node: `web/static/webclient/js/tests/layout_store.test.js`
  - Python: `web/webclient/tests/test_ansi_palette.py`, `web/webclient/tests/test_vue_showcase_evidence.py`, `web/webclient/tests/test_vue_showcase_overlays_evidence.py`, `web/webclient/tests/test_node_suite_evidence.py`
  - Browser: `web/tests/browser/browser_base.py`, `browser_helpers.py`, `test_vue_transport_mount.py`, `test_browser_input_narrative.py`, `test_browser_layout.py`, `.github/browser-shards.json`
- Spec traceability: two new IDs, covered by the new evidence test and browser journeys. Every modified title is unchanged, so no annotation moves.
- Dependencies:
  - Archive order: C10c (`webclient-dialogue-choices-overlay`) → C11a (this change) → C11b (`webclient-scene-transitions`) → C11c (`webclient-mode-transitions`). C13 builds on C11c.
  - Hot-spot files shared with C7 and C10: `MessageWindow.vue`, `AppShell.vue`, `AppClient.vue`, `SettingsOverlay.vue`.
