## 1. Preconditions

- [ ] 1.1 Confirm C11a (`webclient-motion-level`) and C10c are archived. Stop and report if any check fails:
  - `grep -n 'data-motion="reduced"' web/webclient-app/styles/tokens.css` matches
  - `grep -n -- "--motion-scene\|--motion-portrait\|--motion-reveal\|--motion-clear\|--motion-travel\|--motion-shift-lg" web/webclient-app/styles/tokens.css` shows every token
  - `ls web/webclient-app/components/StageActor.vue web/webclient-app/components/DialogueChoices.vue` succeeds
  - `grep -n "Presentation timing never gates committed state or input" openspec/specs/webclient-contextual-hud/spec.md` matches
- [ ] 1.2 Record the hooks this change edits:
  - `SceneBackdrop.vue`'s `activeImage`, `onImageLoad`, and `onImageError`
  - `PlaceCard.vue`'s heading element
  - `MessageWindow.vue`'s fragment container inside `message-page` and its `responseKey`
  - `StageActor.vue`'s `shown`
  - `StatusPanel.vue`'s `v-show="visible"` root (`data-testid="status-panel"`)
  - `MapLattice.vue`'s drawing `<g>` layers

## 2. Shared helpers

- [ ] 2.1 Create `web/webclient-app/lib/transition_hooks.js` (`inertWhileLeaving`, design D1) and `web/webclient-app/tests/transition_hooks.test.js`. `pnpm exec vitest run web/webclient-app/tests/transition_hooks.test.js` is green.
- [ ] 2.2 Create `web/webclient-app/lib/map_pan.js` (`panOffset`, design D3) with no Vue or DOM import, and `web/webclient-app/tests/map_pan.test.js` covering the four cases in design D7. `pnpm exec vitest run web/webclient-app/tests/map_pan.test.js` is green.

## 3. Scene and place

- [ ] 3.1 `web/webclient-app/components/SceneBackdrop.vue` per design D2:
  - `targetImage` / `shownImage` with the decode watcher
  - the dimmed previous image while a decode is pending
  - the keyed `<Transition name="scene-xfade" v-bind="inertWhileLeaving">`
  - the stacking and fade CSS on `--motion-scene`
  - the full view keeps reading the shown image
  - update the header comment

  Adjust `web/webclient-app/tests/scene_backdrop.test.js` where it asserts one image right after a URL change (await the decode microtask). Add a `SceneChange` story to `stories/Core/SceneBackdrop.stories.js`.
- [ ] 3.2 `web/webclient-app/components/PlaceCard.vue` per design D3: key the heading inside `<Transition name="place-card" v-bind="inertWhileLeaving">`, with the enter slide (`--motion-shift-lg × --motion-travel`), the fades on `--motion-reveal`, and the card's `overflow: hidden`. The time line stays outside the transition. Add a `LocationChange` story to `stories/Core/PlaceCard.stories.js`. `pnpm exec vitest run web/webclient-app/tests/place_card.test.js` stays green.
- [ ] 3.3 `web/webclient-app/components/MapLattice.vue` per design D3:
  - the `panOnMove` prop, and the `.map-lattice__pan` group around the drawing layers
  - the pre-flush and post-flush watchers, and `--pan-x` / `--pan-y` set, then released on the next animation frame
  - the travel-multiplied transform with the `--motion-base` transition

  `web/webclient-app/components/LocalMap.vue` passes `:pan-on-move="true"`. `MapOverlay.vue` passes nothing. `pnpm exec vitest run web/webclient-app/tests/world` stays green.

## 4. Window, actors, vitals

- [ ] 4.1 `web/webclient-app/components/MessageWindow.vue` per design D4: wrap the fragment container (not `message-page`) in `<Transition name="message-clear" v-bind="inertWhileLeaving">` keyed by `responseKey`, with the leave-only CSS (absolute, the window's panel fill, opacity over `--motion-clear`). `pnpm exec vitest run web/webclient-app/tests/message_window.test.js web/webclient-app/tests/message_window_typing.test.js web/webclient-app/tests/message_window_dialogue.test.js` stays green.
- [ ] 4.2 `web/webclient-app/components/StageActor.vue` per design D5: the `portraitKey`, the keyed `<Transition name="actor-xfade" v-bind="inertWhileLeaving">`, the absolute leaving copy, the opacity on `--motion-portrait`, and `transition: filter var(--motion-fast) var(--ease-standard)` on the root. Add an `AppearanceChange` story to `stories/Core/StageActor.stories.js`. `pnpm exec vitest run web/webclient-app/tests/core/stage_actor.test.js` stays green.
- [ ] 4.3 `web/webclient-app/components/StatusPanel.vue` per design D6: the template root becomes `<Transition name="vitals-reveal" v-bind="inertWhileLeaving">` around the `v-show="visible"` element, with the enter and leave CSS on `--motion-reveal` and `--motion-shift-sm × --motion-travel`. Add a `RevealToggle` story to `stories/Data/StatusPanel.stories.js`. If the showcase data evidence lists StatusPanel story ids exhaustively, add `data-statuspanel--reveal-toggle` to `web/webclient/tests/test_vue_showcase_data_evidence.py`. `pnpm exec vitest run web/webclient-app/tests/data/status_panel.test.js` stays green.
- [ ] 4.4 Create `web/webclient-app/tests/scene_transitions.test.js` with `global: { stubs: { transition: false } }`, covering design D7's component cases. `pnpm exec vitest run web/webclient-app/tests/scene_transitions.test.js` is green.
- [ ] 4.5 `grep -rnE "(transition|animation)[a-z-]*:[^;]*[0-9]m?s" web/webclient-app/components/{SceneBackdrop,PlaceCard,MapLattice,MessageWindow,StageActor,StatusPanel}.vue` returns nothing, and C11a's `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js` stays green.

## 5. Browser and evidence

- [ ] 5.1 Create `web/tests/browser/test_browser_scene_transitions.py` with the six journeys of design D7. Route `/art/scene/*.png` to a small PNG, and poll states and computed styles rather than time. Annotate each journey with the IDs design D7 lists, confirming the slugs with `uv run --locked python -m tools.spec_traceability list` after 6.1. Add the file's methods to a shard in `.github/browser-shards.json`.
- [ ] 5.2 `web/webclient/tests/test_node_suite_evidence.py`: add `test_scene_transitions_vitest_evidence_passes`, which runs `tests/transition_hooks.test.js`, `tests/map_pan.test.js`, and `tests/scene_transitions.test.js`, annotated with both new contextual-hud IDs.
- [ ] 5.3 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_scene_transitions web.tests.browser.test_browser_art web.tests.browser.test_browser_local_map_interaction web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_exploration_dialogue`. All green.

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas into `openspec/specs/webclient-contextual-hud/spec.md`. Confirm both new IDs with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.

## 7. Validation

- [ ] 7.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence web.webclient.tests.test_vue_showcase_data_evidence`
- [ ] 7.2 Drive the live client at 1920×1080 with `agent-browser` at `完整`:
  - Move between two rooms with generated scenes, and check the backdrop crossfade with no blank frame, the place-card slide, the minimap pan, and the message clear.
  - Take damage and heal, and check that the vitals island fades and slides in and out.
  - Repeat at `減少` (fades only) and `關閉` (instant).

  Close the browser afterwards.
- [ ] 7.3 Run `openspec validate webclient-scene-transitions --strict` and `git diff --check`. Both clean.
