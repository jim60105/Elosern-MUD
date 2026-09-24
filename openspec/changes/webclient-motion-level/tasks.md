## 1. Preconditions

- [ ] 1.1 Confirm C7 through C10c are archived. Stop and report if any check fails:
  - `ls web/webclient-app/composables/use-reduced-motion.js web/webclient-app/components/DialogueChoices.vue` succeeds
  - `grep -n "CURRENT_LAYOUT_VERSION = 2" web/static/webclient/js/elosern/layout_store.js` matches
  - `grep -n "A page types in at the reader's text speed" openspec/specs/webclient-input-narrative/spec.md` matches
- [ ] 1.2 Record the current consumers: `grep -rn "reducedMotion\|reduced-motion\|data-reduced-motion\|useReducedMotion" web/webclient-app web/static/webclient/js web/tests web/webclient/tests --include='*.js' --include='*.vue' --include='*.css' --include='*.py'` (excluding `dist/` and `node_modules/`). Every hit is handled in sections 2–7.

## 2. Motion-level lib and store

- [ ] 2.1 Create `web/webclient-app/lib/motion_level.js` per design D1/D6: `MOTION_LEVELS` and `resolveMotionLevel`, with no Vue import. Its header cites design §9.1/§9.2 and this change. Create `web/webclient-app/tests/motion_level.test.js` (design D10). `pnpm exec vitest run web/webclient-app/tests/motion_level.test.js` is green.
- [ ] 2.2 `web/webclient-app/stores/elosern/preferences.js` per design D1/D2:
  - replace `reducedMotion` / `setReducedMotion` with `motionLevel` / `setMotionLevel`
  - add the `matchMedia` query and its `change` listener, and `ctx.effectiveMotionLevel()`
  - `applyPresentationPreferences` writes `data-motion` and no longer touches `data-reduced-motion`
  - load and persist follow D2
  - update the header comment
- [ ] 2.3 `stores/elosern/view.js`: publish `motionLevel: ctx.effectiveMotionLevel()` and drop `reducedMotion`. `stores/elosern.js`: export `setMotionLevel` and drop `setReducedMotion`; fix the comment. Create `web/webclient-app/tests/store/motion_preferences.test.js` (design D10), and extend `tests/store/reading_preferences.test.js` with the version-2 reset. `pnpm exec vitest run web/webclient-app/tests/store` is green.

## 3. Layout store

- [ ] 3.1 `web/static/webclient/js/elosern/layout_store.js` per design D2:
  - `CURRENT_LAYOUT_VERSION = 3`
  - `PREFERENCE_ENUMS.motionLevel`
  - `PREFERENCE_TYPES` drops `reducedMotion` and adds `motionLevel: "enum"`
  - update the comments that describe the reduced-motion key or version 2

  `web/webclient-app/main.js`: fix any comment naming version 2.
- [ ] 3.2 `web/static/webclient/js/tests/layout_store.test.js`:
  - replace the H5 `reducedMotion` boolean case with `motionLevel` enum acceptance and rejection
  - add the version-2 reset
  - assert parity of `LayoutStore.PREFERENCE_ENUMS.motionLevel` with `MOTION_LEVELS` imported from `web/webclient-app/lib/motion_level.js`

  `node --test web/static/webclient/js/tests/layout_store.test.js` is green.

## 4. Settings, window, and shell wiring

- [ ] 4.1 `web/webclient-app/components/SettingsOverlay.vue` per design D4:
  - replace the three-state reduced-motion row with the `動態效果` segment (testids `settings-overlay-motion-{full,reduced,off}`, prop `motionLevel`, emit `motion-level-change`)
  - update the text-speed description
  - delete `selectReducedMotion` and the `reducedMotion` prop and emit
  - update the header comment

  Rewrite the reduced-motion cases of `web/webclient-app/tests/overlays/settings_overlay.test.js` for the three buttons.
- [ ] 4.2 `web/webclient-app/stories/Overlays/SettingsOverlay.stories.js`: replace `ReducedMotionOn` with `MotionReduced` (`args: { motionLevel: "reduced" }`), and give `Default` `motionLevel: "full"`. `stories/Overlays/OverlayHost.stories.js`: replace `reducedMotion: null` with `motionLevel: "full"`. In `web/webclient/tests/test_vue_showcase_overlays_evidence.py`, replace `overlays-settingsoverlay--reduced-motion-on` with `overlays-settingsoverlay--motion-reduced`.
- [ ] 4.3 `web/webclient-app/components/MessageWindow.vue` per design D5:
  - replace the `reducedMotion` prop and the `useReducedMotion` import with the `motionLevel` prop
  - the effective speed is `instant` when the level is not `full`
  - a change away from `full` completes the typing page

  Delete `web/webclient-app/composables/use-reduced-motion.js`. `components/AppShell.vue`: rename the pass-through prop. `AppClient.vue`: bind `:motion-level="store.view.motionLevel"` on `AppShell` and on `SettingsOverlay`, with `@motion-level-change="store.setMotionLevel"`. `stories/Core/MessageWindow.stories.js`: rename the arg. Update `tests/message_window_typing.test.js` per design D10. `pnpm exec vitest run web/webclient-app/tests/message_window_typing.test.js web/webclient-app/tests/overlays/settings_overlay.test.js` is green, and `grep -rn "reducedMotion\|useReducedMotion\|reduced-motion-change" web/webclient-app --include='*.js' --include='*.vue'` (excluding `dist/`) returns nothing.

## 5. Tokens, sweep, guard, palette

- [ ] 5.1 `web/webclient-app/styles/tokens.css` per design D3:
  - add the new tokens to `:root`
  - replace both `data-reduced-motion` blocks with the `reduced` block, the `off` block with its `0s !important` rule, and the `:root:not([data-motion])` media fallback
  - rewrite the block comment
  - `elosern-toast-in` translates `calc(6px * var(--motion-travel))`
- [ ] 5.2 Sweep per design D7:
  - `components/VitalsTrack.vue`, `LineagePanel.vue`, `CharacterSwitcher.vue`, `DockTabBar.vue`, `SkillBook.vue`, `GalleryPanel.vue` (delete its media block), and `components/creation-overlay.css`
  - update the comments in `components/HudDrawer.vue`, `HudFrame.vue`, `ToastQueue.vue`, `LocalMap.vue`, and `stories/Data/VitalsTrack.stories.js` that name `prefers-reduced-motion` as the switch; they name the motion level
  - fix the stale comments in `tests/hud_drawer.test.js` and `tests/world/inventory_panel.test.js`
- [ ] 5.3 Create `web/webclient-app/tests/motion_tokens.test.js` per design D7. It fails on a planted literal (check once locally, then remove the plant), and it is green after 5.2: `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js`.
- [ ] 5.4 `tools/gen_ansi_palette.py` per design D8: append the `data-motion` blink rule and update the header. Regenerate `web/static/webclient/css/ansi_palette.css` with the generator's own entry point, and add the selector assertion to `web/webclient/tests/test_ansi_palette.py::test_reduced_motion_neutralizes_blink`. `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_ansi_palette` is green.
- [ ] 5.5 `pnpm run build`. Then update `web/webclient/tests/test_vue_showcase_evidence.py`'s reduced-motion block assertion per design D10, using the literal minified forms found in the built CSS. `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_evidence` is green.

## 6. Browser determinism and journeys

- [ ] 6.1 `web/tests/browser/browser_helpers.py`: add `seed_motion_level(target, level)` per design D9. `web/tests/browser/browser_base.py`: `new_page` and `logged_in_page` take `motion_level="off"` and seed unless it is `None`.
- [ ] 6.2 `grep -n "new_context(" web/tests/browser/*.py`. Every site other than `browser_base.py` calls `seed_motion_level(context, "off")` right after creating the context. The expected set is in design Context; report any extra site.
- [ ] 6.3 Opt out with `motion_level=None` per design D9 in:
  - `test_browser_layout.py`, where its stored-wrapper literals and `== 2` assertions become 3
  - C7's three journeys in `test_browser_input_narrative.py`
  - `test_vue_transport_mount.py::test_reduced_motion_and_status_not_color_only`, which now asserts `data-motion="reduced"`, `--motion-base` 0ms, and `--motion-scene` 150ms
- [ ] 6.4 Add the five journeys of design D9 to `web/tests/browser/test_browser_input_narrative.py`:
  - annotate `test_os_reduced_motion_resolves_to_reduced`, `test_stored_motion_level_overrides_os`, and `test_motion_off_is_instant` with `webclient-contextual-hud::the-motion-level-is-a-client-local-preference-that-governs-every-client-animation`
  - annotate `test_transitions_never_gate_commit` with `webclient-contextual-hud::presentation-timing-never-gates-committed-state-or-input`
  - annotate `test_seeded_motion_level_is_applied` with the motion-level ID

  Add the methods to the `test_browser_input_narrative` shard in `.github/browser-shards.json`.
- [ ] 6.5 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_layout web.tests.browser.test_vue_transport_mount web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_shell_narrative web.tests.browser.test_browser_contextual_hud_drawers`. All green.

## 7. Evidence, specs, traceability

- [ ] 7.1 `web/webclient/tests/test_node_suite_evidence.py`: add `test_motion_level_vitest_evidence_passes`, which runs `tests/motion_level.test.js`, `tests/motion_tokens.test.js`, and `tests/store/motion_preferences.test.js`. Annotate it with both new contextual-hud IDs. Run it green.
- [ ] 7.2 Sync this change's deltas into:
  - `openspec/specs/webclient-contextual-hud/spec.md`
  - `openspec/specs/webclient-input-narrative/spec.md`
  - `openspec/specs/webclient-desktop-shell/spec.md`
  - `openspec/specs/webclient-component-showcase/spec.md`
  - `openspec/specs/webclient-narrative-markup/spec.md`

  Confirm the two new IDs with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.

## 8. Validation

- [ ] 8.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_ansi_palette`
- [ ] 8.2 Drive the live client at 1920×1080 with `agent-browser`:
  - Check that the settings overlay shows `動態效果` with the OS-resolved button pressed.
  - Check that `關閉` sets `data-motion="off"` and pages appear at once.
  - Check that `完整` restores typing.
  - Check that a reload keeps the choice.

  Close the browser afterwards.
- [ ] 8.3 Run `openspec validate webclient-motion-level --strict` and `git diff --check`. Both clean.
