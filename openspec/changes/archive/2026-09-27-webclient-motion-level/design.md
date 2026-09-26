## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C10c are archived.

- **Preferences** (`stores/elosern/preferences.js`, H5 and C7):
  - `prefs = { fontScale, text2html, reducedMotion, colorblind, textSpeed, autoAdvance }`
  - `reducedMotion` is `null | "on" | "off"`, stored as an optional boolean
  - `applyPresentationPreferences` writes `--prose-scale`, `data-reduced-motion`, and `data-colorblind` on `<html>`, then `publishView`
  - `persistPresentationPreferences` reloads the wrapper, then saves it
  - `view.js` publishes `reducedMotion`, and `AppClient.vue` binds it to `SettingsOverlay` (`:reduced-motion`, `@reduced-motion-change="store.setReducedMotion"`) and, since C7, to `AppShell` → `MessageWindow`
- **Layout store** (`web/static/webclient/js/elosern/layout_store.js`):
  - C7 sets `CURRENT_LAYOUT_VERSION = 2`, adds `PREFERENCE_ENUMS` (`textSpeed`) and the `"enum"` type, and makes the default migrations `{}`
  - `reducedMotion: "boolean"` is still in `PREFERENCE_TYPES`
  - the storage key is `elosern.layout`
- **Typing** (C7 D4): `composables/use-reduced-motion.js` resolves the override against `matchMedia` in parallel with the CSS. `MessageWindow` sets the effective speed to `instant` while it is true, and a switch into it completes the typing page.
- **`styles/tokens.css`**:
  - It defines `--motion-fast` (120ms), `--motion-base` (300ms), `--motion-slow` (400ms), `--motion-pulse` (3.2s), and `--motion-hp-pulse` (1.1s), and one easing token, `--ease-standard`.
  - Two blocks force the five tokens to 1ms and add a universal `* { animation-duration: 1ms !important; animation-iteration-count: 1 !important; transition-duration: 1ms !important }`:
    - `@media (prefers-reduced-motion: reduce) :root:not([data-reduced-motion="off"])`
    - `:root[data-reduced-motion="on"]`
  - Keyframes: `elosern-combat-pulse`, `elosern-hp-pulse`, `elosern-toast-in` (with a 6px `translateY`).
- **Hard-coded durations**:
  - `VitalsTrack.vue`: the ghost `width 0.6s ease 0.25s` and the fill `width 0.4s var(--ease-standard)`
  - `LineagePanel.vue`: `transform 120ms ease`
  - `CharacterSwitcher.vue`: `0.15s` and `0.12s` twice
  - `DockTabBar.vue`: `all 0.12s`
  - `SkillBook.vue`: `transform 0.2s`
  - `creation-overlay.css`: `concept-spin 0.9s linear infinite`
  - `GalleryPanel.vue`: `gallery-spin 1.5s linear infinite`, plus its own `@media (prefers-reduced-motion)` block
  - (`NarrativeFeed.vue` was deleted by C6c.)
- **Token consumers today**: `HudDrawer` slide (`--motion-base`), the `HudFrame` vignette and recession (`--motion-base`), the veil pulse (`--motion-pulse`), the hp pulse (`--motion-hp-pulse`), `ToastQueue` (`--motion-base`), the `ui-btn` / tab feedback in `tokens.css` (`--motion-fast`), and C6b's `▼` blink (`--motion-pulse`).
- **Narrative palette**: `tools/gen_ansi_palette.py` emits `.blink` with `blink-animation 1s steps(5, start) infinite`, neutralised only by `@media (prefers-reduced-motion: reduce)`. `web/webclient/tests/test_ansi_palette.py` compares the committed file byte for byte.
- **Built-CSS evidence**: `web/webclient/tests/test_vue_showcase_evidence.py` brace-matches every `prefers-reduced-motion` block in the built stylesheet and requires one that holds `--motion-fast:1ms`, `--motion-base:1ms`, `transition-duration:1ms!important`, and `animation-duration:1ms!important`.
- **Browser**:
  - `browser_base.BrowserBase.new_page` opens a context and adds `_WS_CAPTURE_SCRIPT` as an init script. `logged_in_page` wraps it.
  - Several test files open their own contexts with `new_context(`: `test_browser_reconnect.py`, `test_vue_foundation.py`, `test_browser_title_codex.py`, `test_browser_synth_journey.py`, `test_browser_combat_skills.py`, `test_browser_options_surface.py`, `test_browser_combat_panels.py`, `test_browser_art.py`.
  - C7 added `wait_for_page_shown` and the typing journeys in `test_browser_input_narrative.py`.

## Goals / Non-Goals

**Goals:**
- One resolved motion level, written once and read by both the CSS and the script.
- A token vocabulary that expresses the three levels completely, so no later slice writes its own reduced-motion rule.
- No literal duration in any component, enforced by a test.
- A deterministic browser suite.
- A written contract for stepped presentation that C13 plugs into.

**Non-Goals:**
- Any new transition (C11b and C11c).
- A presentation-queue module (D6).
- Changing drawer or overlay presentation. They keep their transitions, which obey the level through the tokens.

## Decisions

### D1. The store is the only resolver; CSS reads `data-motion`
- `lib/motion_level.js` exports `MOTION_LEVELS = ["full", "reduced", "off"]` and `resolveMotionLevel(stored, osRequestsReduce)`. The result is `stored` when it is in `MOTION_LEVELS`, else `"reduced"` when `osRequestsReduce`, else `"full"`.
- `preferences.js` changes as follows:
  - It holds `prefs.motionLevel` (`null` or a level).
  - It creates `query = window.matchMedia?.("(prefers-reduced-motion: reduce)") ?? null` once, and adds a `change` listener that calls `applyPresentationPreferences()` while `prefs.motionLevel === null`.
  - `ctx.effectiveMotionLevel()` returns `resolveMotionLevel(prefs.motionLevel, !!query?.matches)`.
  - `applyPresentationPreferences` sets `data-motion` on `<html>` to the effective level on every call.
- The listener is never removed, because the store lives for the page. `setMotionLevel(level)` ignores anything outside `MOTION_LEVELS`, then applies and persists.
- `view.js` publishes `motionLevel: ctx.effectiveMotionLevel()`.
- `use-reduced-motion.js` is deleted. `MessageWindow` receives the effective level as a prop, so the CSS and the typewriter read one value and cannot disagree. C7 kept them in step by mirroring the media query in two languages.

*Why not a composable:* a composable per component would put one `matchMedia` listener in each component and still leave the `<html>` attribute to someone else. The store already owns the document's presentation attributes.

*The fallback block.* `@media (prefers-reduced-motion: reduce) { :root:not([data-motion]) { …reduced values… } }` covers Storybook, where no store runs, and the frames before `loadPresentationPreferences`. Once the store runs, the attribute is always present, so the fallback never competes with it.

### D2. Layout store version 3
- `CURRENT_LAYOUT_VERSION = 3`.
- `PREFERENCE_ENUMS.motionLevel = ["full", "reduced", "off"]`.
- `PREFERENCE_TYPES`: drop `reducedMotion`, add `motionLevel: "enum"`.

`defaultWrapper()` does not carry `motionLevel`. The key stays optional: absent means "follow the OS". `persistPresentationPreferences` writes `motionLevel` only when it is non-null. `loadPresentationPreferences` accepts it only when it is in `MOTION_LEVELS`. A node test asserts `PREFERENCE_ENUMS.motionLevel` equals `MOTION_LEVELS`, the same parity check C7 made for `textSpeed`.

*Why bump:* the schema drops a key and changes a value type. There are zero users, so there is no migration, and a version-2 wrapper resets.

### D3. Token vocabulary and the three level blocks
Durations resolve per level:

| Token | `full` | `reduced` | `off` | Consumer |
|---|---|---|---|---|
| `--motion-fast` | 120ms | 0ms | 0ms | control feedback, speaking-dim filter (C11b) |
| `--motion-base` | 300ms | 0ms | 0ms | drawer slide, vignette, recession, toast, minimap pan (C11b) |
| `--motion-slow` | 400ms | 0ms | 0ms | vitals fill |
| `--motion-pulse`, `--motion-hp-pulse`, `--motion-spin` (1.2s) | as today | 0ms | 0ms | loops: veil pulse, hp pulse, `▼` blink, spinners |
| `--motion-trail` (600ms), `--motion-trail-delay` (250ms) | as stated | 0ms | 0ms | vitals ghost bar |
| `--motion-scene` | 500ms | 150ms | 0ms | backdrop crossfade (C11b) |
| `--motion-portrait` | 400ms | 150ms | 0ms | portrait crossfade (C11b) |
| `--motion-actor` | 350ms | 150ms | 0ms | NPC enter and leave (C11c) |
| `--motion-panel` | 250ms | 150ms | 0ms | command-panel slide and flip (C11c) |
| `--motion-reveal` | 250ms | 150ms | 0ms | vitals, place card, name plate, veil fades (C11b, C11c) |
| `--motion-clear` | 150ms | 150ms | 0ms | message clear (C11b) |
| `--motion-flash` | 120ms | 0ms | 0ms | combat flash (C11c) |
| `--motion-stagger` | 40ms | 0ms | 0ms | choice rows (C11c) |

Distances, factors, and easing:

| Token | `full` | `reduced` | `off` |
|---|---|---|---|
| `--motion-travel` | 1 | 0 | 0 |
| `--motion-flash-peak` | 0.85 | 0 | 0 |
| `--motion-shift-sm` / `--motion-shift-lg` | 12px / 32px | (unchanged, multiplied by travel) | (unchanged) |
| `--ease-enter`, `--ease-exit` | `cubic-bezier(0, 0, 0.2, 1)`, `cubic-bezier(0.4, 0, 1, 1)` | same | same |

Rules every consumer follows:
- **Travel.** Every translation is written `calc(<distance> * var(--motion-travel))`, so `reduced` keeps the fade and drops the move.
- **Stage-transition tokens.** They are the only tokens that stay non-zero under `reduced`, and each is ≤ 150ms there. This is design §9.1's "fades only (≤ 150ms)".
- **General tokens.** `fast`, `base`, and `slow` go to 0 under `reduced`. Drawers and control feedback therefore become instant, which keeps the existing requirements that say reduced motion "drops the transition" or makes it "effectively instant" literally true. This is how drawers "keep their transitions but obey the level".
- **Loops.** A looping animation with a 0ms duration has an active duration of 0, so it stops at its end state. For the pulses, the blink, and the spinners, that end state is the static indicator.
- **`off`.** Every duration token is 0ms, `travel` and `flash-peak` are 0, and a single `!important` rule, for `off` only, forces `transition-duration`, `transition-delay`, `animation-duration`, and `animation-delay` to `0s` on every element and pseudo-element. There is no such rule for `reduced`, because it would kill the permitted fades. The guard test (D7) is what keeps `reduced` honest.
- **0ms, not 1ms.** Vue's `<Transition>` finishes synchronously when the computed duration is 0, so no `transitionend` wait remains in tests. This is the coordinator-approved "off means 0ms".

`--motion-beat` is not defined here. C13 adds it with the same three-level pattern.

### D4. Settings control
The 輔助顯示 section's 減少動態效果 row becomes 動態效果 (`id="opt-motion-level"`):
- Three `affbtn` buttons in a `role="group"`: `完整`, `減少`, `關閉`, with testids `settings-overlay-motion-{full,reduced,off}`.
- `aria-pressed` and the `.on` class follow the prop `motionLevel` (the effective level). Clicking emits `motion-level-change` with the level.
- The description reads `未選擇時跟隨作業系統的偏好。「減少」只保留短暫淡入淡出並立即顯示文字；「關閉」讓所有變化立即呈現。`
- The C7 text-speed description becomes `逐字顯示訊息的速度；動態效果為「減少」或「關閉」時一律立即顯示。`

There is no "follow the system" button, which is coordinator-approved. Design §9.1 names three levels, and a fourth state would be one no reader can distinguish from its resolved level. The unset state exists only until the first choice, and a presentation-store reset returns to it.

### D5. MessageWindow
- The prop `reducedMotion` becomes `motionLevel` (String, default `"full"`, validator `MOTION_LEVELS.includes`).
- The effective speed is `"instant"` whenever `motionLevel !== "full"`.
- The existing watcher that completed the page on entering reduced motion now completes it on any change away from `full`.
- `AppShell` renames its pass-through prop, and `AppClient` binds `:motion-level="store.view.motionLevel"` on both `AppShell` and `SettingsOverlay`.
- Nothing else in C7's typing or C10c's reading signal changes.

### D6. No presentation-queue module; the contract C13 uses
Design §9.2 sketches one queue for page, transition, and beat steps. In this code:
- **Page steps** already exist as C6b/C7 reader state in `MessageWindow`: ordered pages, a click that completes, and the flush on a new action.
- **Transition steps** (C11b, C11c) are declarative CSS and Vue transitions driven by committed state. They run concurrently and never need sequencing.
- **Beats** (C13) are the only steps that are sequenced but absent today.

A shared queue module would have no consumer in C11 and would be dead code until C13, and its shape would be guessed before C13's beat and page coupling is designed. The minimal design is therefore a spec contract, the ADDED requirement "Presentation timing never gates committed state or input", which C13 must satisfy:
1. **State is never presentation-gated.** The store commits immediately. A beat queue reads committed data and never writes back.
2. **Order.** Steps play in commit order and never reorder, drop, or alter data.
3. **Skip.** A player click or press shows the current step's end state. For beats this is design §10.2's "click skips to the end of the round".
4. **Flush.** A new player action shows every queued non-combat step's end state before its own response starts. Combat's unlock rule is C13's own (§10.2).
5. **Timing.** Every wait comes from a `--motion-*` token, which resolves to 0 at `off`. A script-timed wait reads the token's computed value from `<html>` (C13 adds that reader, next to its `--motion-beat` token), and the queue reads `store.view.motionLevel` for level-specific behaviour (`off` means text only).
6. **Input.** A transition never delays input beyond its duration.

C11 itself needs no script-side duration reader. C11b and C11c drive every transition through CSS and the tokens, so the reader is left to C13, its first consumer, rather than shipped unused.

### D7. The duration sweep and its guard
| File | Before | After |
|---|---|---|
| `VitalsTrack.vue` ghost | `width 0.6s ease 0.25s` | `width var(--motion-trail) ease var(--motion-trail-delay)` |
| `VitalsTrack.vue` fill | `width 0.4s` | `width var(--motion-slow)` |
| `LineagePanel.vue` | `transform 120ms ease` | `var(--motion-fast)` |
| `CharacterSwitcher.vue` (×3) | `0.15s`, `0.12s` | `var(--motion-fast)` |
| `DockTabBar.vue` | `all 0.12s` | `all var(--motion-fast)` |
| `SkillBook.vue` | `transform 0.2s` | `var(--motion-fast)` |
| `creation-overlay.css`, `GalleryPanel.vue` spinners | `0.9s`, `1.5s` | `var(--motion-spin)` |

`GalleryPanel.vue`'s private media block is deleted. The 150ms → 120ms and 200ms → 120ms changes are below perception thresholds for control feedback, and one token is simpler than new micro tokens. Easing keywords (`ease`, `linear`) stay: the rule is about durations.

`tests/motion_tokens.test.js` follows the `tests/z_index_scale.test.js` pattern (`readFileSync` over the source tree):
- It scans every `.vue` and `.css` file under `web/webclient-app/components/` and `web/webclient-app/styles/`, plus `web/webclient-app/AppClient.vue`.
- It looks for `transition`, `transition-duration`, `transition-delay`, `animation`, `animation-duration`, and `animation-delay` declarations, CSS and inline template styles alike, whose value contains a time literal (`/(?<![\w-])\d*\.?\d+m?s\b/`).
- It fails with the file and line.
- `styles/tokens.css` is exempt only inside its token definitions and the `off` block (the `0s !important` rule), identified by selector.
- It also asserts that the three level blocks exist and that each defines every duration token in D3's table.

### D8. Blink follows the level
`gen_ansi_palette.py` keeps its media block and appends `:root[data-motion="reduced"] .blink, :root[data-motion="off"] .blink { animation: none; -webkit-animation: none; text-decoration: underline dotted; }`, and the header text names the motion level. The committed CSS is regenerated, and `test_ansi_palette.py` gains an assertion for the new selector. The palette's `1s` blink is generated Evennia styling outside `web/webclient-app`, and the guard does not scan it. The level still stops it.

### D9. Browser determinism
- `browser_helpers.seed_motion_level(target, level)` takes a page or a context and adds an init script. On each document, if `localStorage.getItem("elosern.layout")` is null, it writes `{layout_version: 3, dimensions: {}, tabs: {}, preferences: {text2html: true, fontScale: 1, colorblind: false, textSpeed: "normal", autoAdvance: false, motionLevel: level}}`.
- `BrowserBase.new_page(viewport, motion_level="off")` and `logged_in_page(viewport, motion_level="off")` call it unless `motion_level is None`.
- Every direct `new_context(` site listed in Context calls it on the new context.

Why this approach:
- It uses the product's own persistence, with no test-only hook in the bundle.
- "When absent" keeps reload-persistence journeys valid.
- A wrapper that drifts from the store's version would reset, and the first new journey (`test_seeded_motion_level_is_applied`, asserting `data-motion="off"`) catches that.

Opt-outs (`motion_level=None`) apply where a test needs first-load defaults or real typing:
- all of `test_browser_layout.py`
- C7's `test_message_page_types_and_completes`, `test_reduced_motion_pages_are_instant`, and `test_reading_preferences_persist`
- `test_vue_transport_mount.py::test_reduced_motion_and_status_not_color_only`

New journeys in `test_browser_input_narrative.py`:
- `test_seeded_motion_level_is_applied`
- `test_os_reduced_motion_resolves_to_reduced` (`emulate_media(reduced_motion="reduce")`, nothing stored): `data-motion="reduced"`, the `減少` button pressed, `--motion-base` 0ms, `--motion-scene` 150ms, `--motion-travel` 0, and a page shown in full. After `emulate_media(reduced_motion="no-preference")`, `data-motion="full"`, with no reload.
- `test_stored_motion_level_overrides_os`: under an emulated reduce, select `完整`, reload, and check `data-motion="full"`, a wrapper with `motionLevel: "full"` and `layout_version: 3`, and no `ui_action`.
- `test_motion_off_is_instant`: select `關閉`, then every `--motion-*` duration resolves to 0 and `getComputedStyle(document.querySelector('[data-testid="message-window"]')).transitionDuration` is `0s`.
- `test_transitions_never_gate_commit`: at `full` (`motion_level=None`), open a drawer, and in the same frame the drawer has focus and the store view names it. Inject a combat-mode snapshot, and in the same frame the stage's `data-elosern-mode` is `combat`.

### D10. Tests
- **Vitest:**
  - `tests/motion_level.test.js`: `resolveMotionLevel` (all nine stored × OS cases plus an invalid stored value).
  - `tests/store/motion_preferences.test.js`, with a mocked `matchMedia` that can fire `change`:
    - the default follows the OS
    - a live OS change re-applies while nothing is stored, and does not when a level is stored
    - `setMotionLevel` applies `data-motion`, persists, and ignores invalid values
    - load discards an invalid stored value
    - a version-2 wrapper resets
  - `tests/motion_tokens.test.js`, per D7.
  - `tests/overlays/settings_overlay.test.js`: three buttons, the pressed state and `.on` class per `motionLevel`, and the `motion-level-change` emits. The reduced-motion cases are deleted.
  - `tests/message_window_typing.test.js`: the reduced-motion cases become `motionLevel` `reduced` and `off` (instant), and `full` under a mocked OS reduce types. A change away from `full` completes the page.
  - `tests/store/reading_preferences.test.js`: its version-1 reset case also covers version 2.
- **Node:** `layout_store.test.js` covers version 3, `motionLevel` enum acceptance and rejection, the absence of `reducedMotion`, parity with `MOTION_LEVELS`, and the version-2 reset.
- **Python:**
  - `test_vue_showcase_evidence.py` requires a `prefers-reduced-motion` block holding `--motion-fast:0ms`, `--motion-base:0ms`, `--motion-scene:150ms`, and `--motion-travel:0`. It also requires a `data-motion=off` rule (quotes as the minifier emits them) holding `transition-duration:0s!important` and `animation-duration:0s!important`. Confirm the literal minified forms against `pnpm run build` output before fixing the strings.
  - `test_vue_showcase_overlays_evidence.py`: the story id `overlays-settingsoverlay--reduced-motion-on` becomes `overlays-settingsoverlay--motion-reduced`.
  - `test_node_suite_evidence.py` gains `test_motion_level_vitest_evidence_passes`, which runs the three new Vitest files and is annotated with both new contextual-hud IDs.

### D11. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud "Narrative prose scale is a client-local preference the settings surface owns" | C7 `webclient-typewriter-reading-prefs` |
| contextual-hud "Text speed and auto-advance are client-local reading preferences the settings surface owns" | C7 (ADDED there) |
| input-narrative "A page types in at the reader's text speed and auto-advance is opt-in" | C10c `webclient-dialogue-choices-overlay` |
| desktop-shell "Browser persistence is versioned and presentation-only" | C7 |
| component-showcase "The full overlays are complete…" | main spec (no series change touches it) |
| narrative-markup "The narrative palette is generated…" | main spec |

- Every scenario title is kept, and each MODIFIED block adds at most one scenario. No annotation moves.
- The scenario titles "Reduced motion overrides, and defers when unset" and "An explicit off lets pages type" keep their names. Their bodies now describe the motion level: the explicit `full` level is what turns reduced motion off.
- **Requirements left untouched on purpose.** Their text says reduced motion disables or neutralises a transition, and under the new blocks the `reduced` and `off` levels make each of them instant:
  - "An open drawer or overlay dims the stage behind it"
  - the vitals trailing bar and low-HP pulse requirements
  - the drawer's reduced-motion scenario
  - the bag's "effectively instant" rule
  - `webclient-vue-application` "Reduced motion is honored"

  They remain true, and their scenarios still describe the OS-default case.
- New IDs: `webclient-contextual-hud::the-motion-level-is-a-client-local-preference-that-governs-every-client-animation` and `webclient-contextual-hud::presentation-timing-never-gates-committed-state-or-input`. They are covered by the evidence test and the new browser journeys. Confirm both slugs with `uv run --locked python -m tools.spec_traceability list` after syncing.
- `openspec validate` reports that blocks based on unarchived series changes cannot apply yet. That is expected.

**Archive order: C10c (`webclient-dialogue-choices-overlay`) → C11a (this change) → C11b (`webclient-scene-transitions`) → C11c (`webclient-mode-transitions`).** C13 archives after C11c. If a base block changes before archive, re-sync this change's block and keep only its own edits: the motion level, version 3, and the blink selector.

## Risks / Trade-offs

- [A component the guard does not scan (a JS-set inline style) animates with a literal duration] → The `off` safety rule still makes it instant. Under `reduced` it would play. The guard scans every template, and C11 adds no script-timed motion.
- [The seeded browser wrapper drifts from the store's schema] → A drifted wrapper resets to the default, which is `full` in headless Chromium, and `test_seeded_motion_level_is_applied` fails at once.
- [Tests outside `BrowserBase` miss the seed] → The Context lists every `new_context(` site, and task 6.2 greps for them. Until C11b adds transitions, a missed site only runs at `full`, which changes nothing.
- [Control feedback timing changes (150ms and 200ms become 120ms)] → Imperceptible for hover feedback. Recorded in D7.
- [Budget] → lib and store (1.5h), layout store and node (1h), settings and window (1h), tokens and sweep and guard (1.5h), palette (0.5h), browser seeding and journeys (1.5h), specs and gates (1h). About 8h.

## Migration Plan

None. A stored version-1 or version-2 wrapper resets to the version-3 default on first load. The client is unreleased.
