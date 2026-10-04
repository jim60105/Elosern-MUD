# Tasks — retarget-desktop-viewport-contract

TDD: where a task changes behavior the suite pins, amend/extend the pinning test in the same
task and run it before and after. Every browser-facing acceptance claim in these requirements is
verified by the browser suites in the companion change `retarget-browser-acceptance-viewports`;
unit-level pins below are the Vitest suite (`npm --prefix web/webclient-app test`).

## 1. Reference constants

- [x] 1.1 `web/webclient-app/lib/ui_scale.js`: `UI_SCALE_REFERENCE_HEIGHT = 790`,
      `UI_SCALE_REFERENCE_WIDTH = 1451`, `UI_SCALE_MAX = 1.4` unchanged; rewrite the header
      comment to the new reference (it must stop saying "16:9" — the width term guards a window
      "narrower than the reference's own aspect ratio") and drop the stale "2560x1440 renders
      the 1920x1080 reference at four thirds" sentence (2560x1440 now sits at the 1.4 cap).
- [x] 1.2 Amend `web/webclient-app/tests/ui_scale.test.js`: reference cases (1451x790 → 1),
      cap case (2560x1440 → 1.4, both raw ratios 1.823/1.764 exceed the cap), uncapped case
      (1741x948 → 1.2), below-reference floor (1280x720 → 1), tall-narrow width guard
      (e.g. 900x1600 → width ratio 0.62 → clamps to 1), and non-positive/detached cases
      unchanged in behavior. Verify the suite fails on the old constants, passes on the new.

## 2. Type ramp and prose tokens

- [x] 2.1 `web/webclient-app/styles/tokens.css` type ramp reference steps: `--text-xs` 12→16,
      `--text-sm` 13→17, `--text-md` 14→18, `--text-base` 16→20, `--text-lg` 18→22,
      `--text-xl` 20→24, `--text-2xl` 24→28, `--text-3xl` 28→32, `--text-4xl` 32→36,
      `--text-initial` 44→48; every token keeps its `calc(Npx * var(--ui-scale))` shape.
      Sweep the remaining `calc(npx * var(--ui-scale))` literals in `tokens.css` and the
      component stylesheets: literals that are chrome dimensions stay (they are re-anchored by
      the constants, not by hand); only literals whose spec text changed (band bounds, island
      square, message/log sizes, insets quoted in requirement text) are edited, per tasks 3–5.
- [x] 2.2 Prose tokens: `--message-text: calc(16px * var(--ui-scale))` and
      `--log-text: calc(16px * var(--ui-scale))` (both `vh` clamps deleted — the reference-scale
      size is the 16px floor, scaled once by the chrome factor). Update their comment blocks to
      cite the retarget (`webclient-vue-application` floor + prose-scale steps in
      `webclient-contextual-hud`). Keep `--message-page-font`, `--message-measure` (both the
      plain and dialogue-mode rules in `MessageWindow.vue`) and the full log's `42em`/1.75
      leading formulas untouched — the base under them changes, the measure does not.
- [x] 2.3 Faces: `MessageWindow.vue` page text (`font-family: var(--f-serif)` →
      `var(--f-mono)`) and `FullLogOverlay.vue` log lines (same swap). Keep
      `--f-serif`/`--f-display` for headings and non-prose surfaces; the semantic-class
      requirement's sys lines stay `--f-sans`.
- [x] 2.4 Sub-em prose treatments that would breach the floor at a 16px base:
      `MessageWindow.vue` `.sys` `0.75em` → `var(--text-sm)`, box-drawing art path `0.6em` →
      `var(--text-xs)`; `FullLogOverlay.vue` `.sys` `0.75em` → `var(--text-sm)`, art path
      `0.8em` → `var(--text-xs)`. `ReadingSample.vue`'s `0.5em` is `visibility: hidden` spacing
      furniture — leave it and note the exemption in the comment.
- [x] 2.5 Prose steps: `SettingsOverlay.vue` `SCALE_STEPS` → `A−` 1.0, `A` 1.125, `A+` 1.25;
      `preferences.js` keeps `fontScale` numeric and clamps to the legacy 0.5–2 band on load,
      then normalizes any stored value not exactly one of the three steps to the default step
      `A` = 1.125 —
      no layout-version bump (`LAYOUT_VERSION` stays 3). Update the comment block naming the
      steps.

## 3. Band, top band, stage box

- [x] 3.1 `tokens.css`: `--band-h: clamp(190px * var(--ui-scale), 27.85vh, 400px * var(--ui-scale))`
      (was `260px/27.8vh/400px`); comment records 27.85% × 790 = 220.0px at the reference and
      401px at 2560x1440 (vh term inside the bounds). `--header-h` stays `calc(48px * var(--ui-scale))`;
      `--actor-h` keeps `min(62vh, 680px * var(--ui-scale), calc(100vh - var(--header-h) - var(--band-h)))`.
      Verify the stage-box arithmetic comment (`--stage-content-bottom` consumers) reads
      790 − 48 − 220 = 522px ≥ 65% (513.5px).

## 4. Minimap island and map labels

- [x] 4.1 The island's square is the `canvas-size` prop, not a `--minimap-size` token (no such
      token exists in the shipped tokens): `LocalMap.vue`: island props `:canvas-size="240"`
      (was 208), `:label-font="16"`, and pass
      `:marker-name-font="16"`; update the comment block (fixed square 240px, 16-unit label and
      marker-name steps). `MapLattice.vue`: defaults `labelFont` 11→16, `markerNameFont` 10→16,
      with the doc comments restated (a user-unit size IS the drawn CSS px size at scale 1; the
      island no longer keeps marker names below its chrome step — the 16px floor forbids it).
      `MapOverlay`/full-map call sites: label and marker-name steps 16/16 (the overlay's
      1px/2px-per-user-unit fit and zoom bounds unchanged).
- [x] 4.2 Amend the unit pins that carry the old island geometry: `tests/world/local_map.test.js`,
      `tests/map_lattice_fidelity.test.js`, `tests/map_lattice_name_fit.test.js`,
      `tests/map_pan.test.js`, `tests/scene_transitions.test.js` — 208→240 canvas/viewBox/style
      pins; the 3×3 no-gateway fixture's grown pitch 59→60 (the 240px inset box lets the growth
      reach the 1.5× cap); the wilderness fixture's scale 0.933→1 so `scale × labelFont` is
      exactly 16.00 CSS px (replace the ≥11 floor assertions with an exact-16 pin); the
      below-floor window `208 / 0.75` → `240 / 0.75`; the label-term-binding fixture (2× labelMax
      + 1 cells) — recompute the 16-unit budget `(cells/2 × CELL_EM × 16 + 8)` and keep the
      binding/non-binding conclusion the delta states (overlay label term stays non-binding).
      `CELL_EM` reads the shipped cell-advance manifest (`web/webclient-app/fonts/jimmonotc/codepoints.json`),
      unchanged.
- [x] 4.3 Add one Vitest pin for the new fitted-label floor clause: for the reported wilderness
      payload the island's drawn labels are ≥ the declared step at the reference (scale 1 case),
      and annotate the new/updated map tests with the amended `webclient-local-map` requirement
      IDs as the existing tests in these files do.

## 5. Prose-scale normalization tests

- [x] 5.1 Amend `tests/store/reading_preferences.test.js` and `tests/store/motion_preferences.test.js`:
      stored `fontScale: 1.12` (a legacy step) now loads as `A` = 1.125; a stored `1.25` loads as
      `1.25`; out-of-band values still clamp; the versioned-reset cases keep passing with
      `layout_version` still 3.
- [x] 5.2 Amend `tests/overlays/settings_overlay.test.js` (current-step marker moves to the new
      step values) and `tests/overlays/reading_sample.test.js` (props sweep uses 1.125/1.25);
      the message-window re-paging tests (`message_window.test.js`, `message_window_beats.test.js`,
      `message_window_typing.test.js`) drive `fontScale` through the `pageFit` seam, so they
      should need no numeric change — verify.

## 6. Sweep and gates

- [x] 6.1 Residual sweep: no `1920`, `1080`, `27.8vh`, `208`-island, `260px`-band, or `12px`
      *type* literal survives under `web/webclient-app/` (motion-travel `12px` values, font
      `unicode-range` blobs, and `color-208` fixture spans are not geometry). Update Storybook
      frames that hardcode the old island (218/208px mock columns) to 240px.
- [x] 6.2 `pnpm test` (Vitest, repo root) green, plus the `node --test`
      `web/static` legacy text-client suite green with no behaviour change to the legacy client.
      One deliberate exception: the shared Elosern layout store's persisted prose default moves
      1 → 1.125 (the new default step `A`) and the two reset-default assertions in its own suite
      follow, because that stored default is what a fresh or reset client reads — without it the
      client would open at the 16px floor instead of the 18px default scale both this change and
      the companion acceptance change pin. `LAYOUT_VERSION` stays 3.
- [x] 6.3 Traceability: `uv run --locked python -m tools.spec_traceability list` shows the
      amended requirements covered (literal IDs), then `check` green. If any new test *module*
      is added (prefer amending existing files), `.github/evennia-shards.json` needs a shard
      entry — none is planned.
- [x] 6.4 `openspec validate retarget-desktop-viewport-contract --strict` and
      `openspec validate --all --strict` green.
- [x] 6.5 Confirm non-touches: `docs/game/commands.md` and `command-reference.md` unchanged (no
      player-command surface moves); `web/tests/browser/**` untouched (companion change owns the
      tuples and `browser_base.DEFAULT_VIEWPORT`); `.github/evennia-shards.json` unchanged.
