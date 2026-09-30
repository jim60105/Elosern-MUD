## 1. Implement the bounded surface

- [x] 1.1 Theme the existing native toggles and align settings cards/type without changing preference APIs; exercise keyboard checked-state changes.
- [x] 1.2 Add isolated sample/replay with existing speed logic and timer cleanup; test no live-log/dispatch mutation and close mid-type.
- [x] 1.3 Inspect scale/speed combinations and full/reduced/off in the actual settings overlay at three desktop sizes.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-settings-reading-preview --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.

## Evidence

- 1.1: `SettingsOverlay.vue` toggles keep `type="checkbox"`, gain `role="switch"`, `aria-labelledby` (visible label) and `aria-describedby` (help line); drawn as a track and knob through the motion tokens; segments are one framed strip; the grid uses `align-items: start` on equal tracks; help copy is `--text-md`. Space on the focused 色盲配色 switch flipped exactly that one preference in the live client.
- 1.2: new `ReadingSample.vue` (manifest `Overlays/ReadingSample`, story) uses `useTypewriter` with the new shared `effectiveCps(motionLevel, textSpeed)` from `lib/message_reveal.js`, which `MessageWindow.vue` now uses too. Unmounting stops its frame; no store, emit or live region.
- 1.3 / 2.2: live client (managed browser server, built bundle) at 1920x1080 full/A/標準, 1440x900 full/A+/慢, 1280x720 reduced/A+/快 and off/A−/瞬間, plus Storybook `Overlays/OverlayHost/SettingsSurface` and `Overlays/ReadingSample/*`. The sample types at full, shows at once at reduced/off/瞬間 with the caption naming why, balances onto two lines at 1080, matches the live page's computed font size, and the switch focus ring is visible. At 1280x720 and 1440x900 the settings body scrolls internally (scrollHeight 792/795 over 542/722); nothing clips.
- 2.1: `pnpm exec vitest run web/webclient-app/tests/overlays/ web/webclient-app/tests/message_reveal.test.js web/webclient-app/tests/message_window_typing.test.js` (13 files, 177 passed); full `pnpm test` 128 files / 1424 passed; `node --test web/static/webclient/js/tests/*.test.js` 471 passed; `pnpm run showcase-coverage` 60/60; the four `web.webclient.tests.test_vue_showcase_*_evidence` modules 15 OK; browser (one method each): the new `DrawerNarrativeBrowserTest.test_reading_sample_previews_preferences_without_touching_play`, `test_settings_prose_scale_is_a_client_local_preference`, `test_reading_preferences_persist`, `ContextualHudBrowserTest.test_reference_surfaces_share_one_opaque_workspace_frame`, `test_codex_drawer_replaces_the_open_drawer_or_overlay`, `test_h5_overlay_triggers_exclusion_and_focus_restoration`, `test_open_drawer_or_overlay_dims_stage` all OK.
- 2.3: MODIFIED `webclient-contextual-hud` "Narrative prose scale…" names the reading sample as a prose target; `tokens.css` comment, the AVG design doc (§5.2 table, §6.4), the frozen audit §2.3 row and `.github/browser-shards.json` updated.
