## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C10c and C11a (`webclient-motion-level`) are archived.

- **Motion (C11a):**
  - `<html data-motion>` carries the effective level.
  - The stage-transition tokens `--motion-scene` (500ms), `--motion-portrait` (400ms), `--motion-reveal` (250ms), and `--motion-clear` (150ms) resolve to 150ms under `reduced` and 0ms under `off`.
  - `--motion-base` and `--motion-fast` are 0ms under `reduced` and `off`.
  - `--motion-travel` is 1 or 0. `--motion-shift-sm` is 12px and `--motion-shift-lg` is 32px. `--ease-enter` and `--ease-exit` exist.
  - Under `off`, a `0s !important` rule covers every element.
  - The ADDED requirement "Presentation timing never gates committed state or input" is the contract.
- **`SceneBackdrop.vue`**:
  - One `<img class="scene-backdrop__image">` renders `activeImage`: the current done URL, or the remembered `priorImage` dimmed (`--dimmed`, opacity 0.45) while the scene is `pending`.
  - `onImageLoad` records `priorImage`, and `onImageError` records the URL in `failedUrls` and shows the placeholder.
  - Swapping the URL swaps `src` on the same element, so the old bitmap disappears before the new one loads. Nothing crossfades.
  - `setPriorImage` is exposed for stories and tests.
- **`PlaceCard.vue`** (C4b): props `locationLabel` and `timeLabel`. It renders `section.place-card` holding `h1.place-card__location` and `p.place-card__time` in the fixed-height `place` anchor, with no tab stop. `AppShell` mounts it.
- **Minimap** (C1, C4c):
  - `LocalMap.vue` renders `MapLattice` in the `map` anchor, and `MapOverlay` renders the same `MapLattice` for the full map (C2 adds fit, zoom, and pan there).
  - `composables/use-map-lattice-geometry.js` gives node positions (`nodePos`) and the `viewBox` (`viewBoxX`, `viewBoxY`, `viewBoxWidth`, `viewBoxHeight`) for both layout variants. The lattice variant places in-view nodes relative to the minimum in-view coordinate, and the graph variant puts `current` at the centre, so a move recomputes the whole placement. There is no stable world frame to scroll across.
  - The minimap square is 208px.
- **`MessageWindow.vue`** (C6b, C7, C10c):
  - The focusable page surface `message-page` holds the rendered fragments of `pages[pageIndex]`.
  - The reader state `responseKey` changes when a new response starts.
  - The typewriter `start(0)`s page 1 of a new response.
  - The live region announces each page once.
- **`StageActor.vue`** (C10b): the root `.stage-actor[data-side][data-speaking]` holds one `ReferenceArtwork` with `shown`, which is `portrait`, else a name placeholder, else `null`. The dim is `filter: brightness(var(--actor-dim))` with no transition. The component has no focusable element.
- **`StatusPanel.vue`** (C3, C4c):
  - Its root carries `v-show="visible"`, so the trailing-bar memory survives while hidden.
  - `AppShell`'s `vitalsVisible` watcher (pre-flush) calls `restoreFocusHome()` (C10b's rename) when focus is inside `status-panel` on a true-to-false edge.
- **Vitest** stubs `<Transition>` by default (`@vue/test-utils` `global.stubs.transition`), so hook-based behaviour needs `global: { stubs: { transition: false } }`.

## Goals / Non-Goals

**Goals:**
- The location, appearance, and vitals rows of design §9.3, at all three levels, from tokens only.
- No blank frame on a scene change, and no misrepresented scene.
- No transition delays committed state or input. Leaving copies are unreachable.

**Non-Goals:**
- Mode transitions, the NPC entrance, the combat flash and veil, and the choices stagger (C11c).
- Pan and zoom of the full-map overlay (C2 owns its view; it does not animate).
- Any script-timed animation. Every transition here is CSS-timed through tokens (C11a D6).

## Decisions

### D1. One inert rule for every leaving copy
`lib/transition_hooks.js` exports:

```
export const inertWhileLeaving = {
  onBeforeEnter: (el) => { el.inert = false; },
  onBeforeLeave: (el) => { el.inert = true; },
  onAfterLeave: (el) => { el.inert = false; },
  onLeaveCancelled: (el) => { el.inert = false; },
};
```

Every `<Transition>` in this change binds it with `v-bind="inertWhileLeaving"`.
- `inert` removes the subtree from the accessibility tree, the tab order, and hit-testing in one attribute.
- Vue calls `onBeforeLeave` synchronously in the patch that commits the removal, so the rule holds from the commit's frame.
- `onLeaveCancelled` covers a `v-show` element that re-enters mid-leave: the vitals island shown again.
- `inert` does not move focus: an inert focused element is blurred to the body. The rule therefore also relies on the pre-flush rescues. The vitals one exists (C3 D3), and the other leaving copies hold no focusable element (images, headings, the clear layer, D4).

*Alternative:* `aria-hidden` plus `pointer-events: none` plus `tabindex=-1` on descendants. Rejected: three mechanisms that each miss something, where `inert` is exactly the contract.

### D2. Backdrop crossfade after decode
`SceneBackdrop` separates the *target* from the *shown* image:
- `targetImage` is today's `activeImage` computed: the URL plus `dimmed`.
- `shownImage` is a ref.
- A watcher on `targetImage.url` handles three cases:
  - An unchanged URL only updates `dimmed`.
  - A new URL starts `decodeImage(url)`: `new Image()`, set `src`, then `img.decode()` when the method exists, otherwise resolve at once, as in jsdom. On settle (resolve or reject), if the target is still that URL, `shownImage` becomes the target. A reject still swaps: the rendered `<img>`'s existing `@error` then records the failure and shows the placeholder, so failure handling keeps one path.
  - While the decode is pending, the previous `shownImage` stays, with `dimmed` forced to true. That is the backdrop's existing "prior image, never presented as current" treatment, and the scene label, alt text, and `pending` notice have already switched at commit.
- The template renders `<Transition name="scene-xfade" v-bind="inertWhileLeaving"><img v-if="shownImage" :key="shownImage.url" …></Transition>` with no `mode`, so the entering and leaving images coexist.
- CSS:
  - `.scene-xfade-enter-active, .scene-xfade-leave-active { transition: opacity var(--motion-scene) var(--ease-standard) }`
  - `.scene-xfade-enter-from, .scene-xfade-leave-to { opacity: 0 }`
  - The leaving image gets `z-index: 0` and the entering `z-index: 1`, both inside `inset: 0`.
  - The dimmed modifier keeps `opacity: 0.45` on the settled element. An enter goes 0 → its resting opacity: the `enter-to` state is the element's own class opacity, because Vue removes `enter-from` and the element settles at its class value.
- `onImageLoad` and `onImageError` bind to the rendered image as today. `setPriorImage` still seeds `priorImage`.
- A placeholder-only state (no image) renders no image layer. The image fades out over the gradient stage, and the placeholder label appears at commit.

*Why decode first:* swapping `src` shows an empty box for the load time, and a crossfade from a loaded image to an empty one reads as a flash. `decode()` is the standard way to wait for paint-ready pixels.

*Why dim while waiting:* the art-panel contract forbids presenting an old scene as the current one. The label has already changed, so the previous bitmap must look stale, exactly as for a `pending` scene.

### D3. Place-card heading and minimap pan
**Place card.**
- `PlaceCard` wraps its `h1` in `<Transition name="place-card" v-bind="inertWhileLeaving">`, keyed by `locationLabel ?? "位置：--"`.
- Enter: `opacity 0` and `translateX(calc(-1 * var(--motion-shift-lg) * var(--motion-travel)))`, going to rest over `--motion-reveal` with `--ease-enter`.
- Leave: `opacity → 0` over `--motion-reveal` with `--ease-exit`, `position: absolute` at the same box.
- The time `p` is outside the transition, so a clock tick never animates.
- The card is `overflow: hidden`, so the slide never paints outside its island.

**Minimap pan.**
- `MapLattice` gains `panOnMove` (Boolean, default false), and `LocalMap` passes `true`. `MapOverlay` does not, so the full map is unaffected.
- The drawing's node, marker, and edge layers are wrapped in one `<g class="map-lattice__pan" :style="panStyle">`.
- A watcher on the current node id, with `flush: "pre"`, records `prev = { id, pos: nodePos(prevCurrent), viewBox, size }` from the geometry before the patch. A second watcher, with `flush: "post"`, computes `panOffset(prev, next)`, where `next` uses the new geometry and the same node id.
- `lib/map_pan.js` `panOffset` works in two steps:
  - It converts `prev.pos` to screen pixels, `(pos - viewBoxOrigin) × size / viewBoxSize`.
  - It converts that point back into the new drawing's user units and subtracts the node's new position.

  The result is `{dx, dy}`, or `null` when the node is missing from the new placement (a teleport or a new area).
- The component sets `--pan-x` and `--pan-y` (user units, written as px, which CSS maps to SVG user units) with `transition: none`. On the next animation frame it sets them to 0 with `transition: transform var(--motion-base) var(--ease-standard)`.
- The group's style is `transform: translate(calc(var(--pan-x) * var(--motion-travel)), calc(var(--pan-y) * var(--motion-travel)))`. Under `reduced` and `off`, travel is 0 and the base duration is 0, so the group never moves.

The pan is presentation only:
- Node elements, `data-node` attributes, accessible names, and click targets carry the new placement at commit.
- The shape moves as one rigid group, and clicks during the pan still hit the node under the pointer.
- The pan never changes the placement or the fit rules C1 and C4c define.

*Why a transform offset (FLIP) and not a `viewBox` tween:* each move recomputes the placement (Context), so there is no shared world frame in which to move a camera. The transform offset keeps the previous node visually anchored, then settles. It works for both variants, needs no script-side duration, and is pure CSS under the tokens.

### D4. The message window's clear layer
- Inside the page surface, the fragment container is wrapped in `<Transition name="message-clear" v-bind="inertWhileLeaving">`, keyed by `responseKey`. The page surface `message-page` itself is not keyed, so its focus, key scope, and live region are untouched.
- With no `mode`, the new response's container mounts at once and the typewriter `start(0)`s as C7 defines. The old container leaves:
  - `.message-clear-leave-active { position: absolute; inset: 0; z-index: 1; background: <the window's panel fill>; transition: opacity var(--motion-clear) var(--ease-exit) }`
  - `.message-clear-leave-to { opacity: 0 }`
  - There are no enter classes, so the new page appears without an enter animation. It is empty at first because it types.
- The opaque fill hides the new page's first typed characters under the fading old page, so the two texts never overlap legibly. Within 150ms at most about 7 characters type underneath at `normal`.
- A page advance within the same response is not a response change, so it does not clear.
- A remount (reconnect) mounts with no leave, matching design §12 ("no transition replays").

The coordinator approved clearing on every new response, not only on a location change. The window's only "clear" moment is a response change. A location change always starts one (the move's `in` line), and the art panel commits later than that line, so tying the clear to `art.scene` would fade text the player is already reading.

### D5. Portrait crossfade and dim easing
`StageActor` wraps `ReferenceArtwork` in `<Transition name="actor-xfade" v-bind="inertWhileLeaving">`, keyed by `portraitKey`:
- `shown?.url`
- else `"ph:" + (shown?.placeholder?.label ?? "")`
- else `"none"`

The leaving copy is `position: absolute; inset: 0`. Enter and leave both run `opacity` over `--motion-portrait` with `--ease-standard`.

The root gains `transition: filter var(--motion-fast) var(--ease-standard)`, so the speaking dim eases at `full` and switches instantly at `reduced` and `off` (C11a D3: `--motion-fast` is 0ms there). A same-URL catalog refresh keeps the key, so it never fades.

### D6. Vitals reveal inside `StatusPanel`
`StatusPanel`'s template root becomes `<Transition name="vitals-reveal" v-bind="inertWhileLeaving">` around the existing root element that carries `v-show="visible"`. Keeping the `v-show` inside the component keeps C3 D1's trailing-bar memory and its tests.
- Enter from, and leave to: `opacity: 0; transform: translateY(calc(-1 * var(--motion-shift-sm) * var(--motion-travel)))`.
- Active: `transition: opacity var(--motion-reveal) var(--ease-enter), transform var(--motion-reveal) var(--ease-enter)`. The leave uses `--ease-exit`.
- The vitals anchor has a fixed position, and the island slides within it. The anchor's `max-height` bounds it, and the 12px slide stays inside the stage's top-left area.
- C3's pre-flush rescue runs before the patch that starts the leave, and the leave then sets `inert` (D1). This is the order the "Focus leaves the vitals island before it animates out" scenario needs.

### D7. Tests
- **Vitest:**
  - `tests/transition_hooks.test.js`: each hook's effect on `inert`.
  - `tests/map_pan.test.js`:
    - the same viewBox gives the position delta
    - a changed viewBox origin and size gives the screen-anchored delta
    - a missing node gives `null`
    - the graph variant's recentred placement gives an offset equal to the previous node's old screen position mapped into the new units
  - `tests/scene_transitions.test.js`, with `stubs: { transition: false }`, covers:
    - `SceneBackdrop`: a mocked `HTMLImageElement.prototype.decode` holds a promise, the previous image is shown dimmed while pending, both images are present after resolve with the leaving one `inert`, and a reject still swaps.
    - `PlaceCard`: the heading's leave is `inert`, and a time-only change adds no leaving element.
    - `MessageWindow`: a new `responseKey` leaves one inert container, the new one mounts and `data-typing` is true at once, and the page surface keeps focus.
    - `StageActor`: a URL change leaves one inert copy, and a same-URL refresh leaves none.
    - `StatusPanel`: toggling `visible` false sets `inert` during leave, and toggling back before `after-leave` clears it.
  - `tests/scene_backdrop.test.js`: adjust the cases that assert one `<img>` directly after a URL change, by awaiting the decode microtask.
  - `tests/core/stage_actor.test.js`, `tests/place_card.test.js`, `tests/message_window.test.js`, `tests/data/status_panel.test.js`: unchanged assertions pass with the default transition stub. Fix any that count children during a swap.
- **Browser**, `web/tests/browser/test_browser_scene_transitions.py`, at 1920x1080:
  - Routes `/art/scene/*.png` to a small PNG fixture with `page.route`, so two same-origin scene URLs decode.
  - Asserts computed styles and DOM states, never elapsed time.
  - `test_full_motion_scene_change` (`motion_level=None`, headless Chromium has no OS preference, so the level is `full`). Inject an art update with a new URL, then poll until two `scene-backdrop-image` elements exist. The leaving one has `inert` and a computed `transition-duration` of `0.5s`. Eventually one remains.
  - `test_full_motion_place_card_and_clear`. Inject a new status location, then check that a leaving `place-card__location` is inert with `transform` present in its computed transition. Send `look`, then check that a leaving `message-clear` layer is inert with a `0.15s` duration, and `message-page` keeps focus.
  - `test_full_motion_minimap_pan`. Inject a `local_map` update moving `current` to an adjacent node, then read the `.map-lattice__pan` group's computed `transition-duration` (`0.3s`) and its non-identity transform on the first frame after commit, then identity.
  - `test_vitals_reveal_and_inert`. Inject `hp` below maximum and check that the island is visible with a `0.25s` transition. Focus a harmful chip, then inject a clear. Focus lands on the focus home, never on `body`, and the island is inert until hidden.
  - `test_reduced_motion_fades_only` (`motion_level="reduced"`). The scene leaving layer's duration is `0.15s`, the place card's computed transform is `none` throughout, and the minimap group's transform stays identity.
  - `test_off_motion_is_instant` (default `off`). After each injection, in the next frame, exactly one scene image, one heading, and one page container exist, and no element carries `inert` from a transition.
  - Annotations:
    - the full, reduced, and off journeys: `webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level`
    - the inert, clear, and vitals journeys: `webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out`
    - the vitals journey also covers the modified vitals ID, and the clear journey the modified message-window ID
  - Confirm the slugs with `tools.spec_traceability list`.
- **Evidence:** `test_node_suite_evidence.py` gains `test_scene_transitions_vitest_evidence_passes`, which runs the three new Vitest files and is annotated with both new IDs.

### D8. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud "The vitals island is shown only in combat or while a vital or a condition needs attention" | C3 `webclient-retire-redundant-hud` (ADDED there, no later series change) |
| contextual-hud "The message window presents the current response one page at a time in the band's message region" | C10c `webclient-dialogue-choices-overlay` |

- Every scenario title is kept, so no annotation moves.
- The two ADDED requirements get new IDs, covered as D7 lists.
- The stage-actor requirement (C10b) is not modified: it already says transitions between its states are owned by the motion layer.
- The place-card requirement (C4b) is not modified: the card's size, text, and truncation are unchanged, and the new heading and the new time are in the DOM at commit.
- The art-panel requirements are not modified: the prior-image dim rule is reused, not changed.

**Archive order: C10c (`webclient-dialogue-choices-overlay`) → C11a (`webclient-motion-level`) → C11b (this change) → C11c (`webclient-mode-transitions`).** C11c reuses `inertWhileLeaving` and modifies the stage and collapse requirements. If a base block changes before archive, re-sync this change's blocks and keep only its own edits: the clear layer, and the vitals exit.

## Risks / Trade-offs

- [Two stacked full-bleed images cost memory during the fade] → They coexist for 500ms at most. Both are already decoded, and the leaving element is removed after `after-leave`.
- [A decode that never settles (a hung request) keeps the previous image dimmed forever] → The image request has the browser's normal timeout. The label, alt text, and placeholder rules already describe the new scene, and a newer target replaces the wait.
- [The pan offset jumps when the fit scale changes a lot between placements] → `panOffset` works in screen pixels, so the previous node is anchored exactly, and the group then settles to the committed placement. Scale is not animated; only translation is.
- [Browser assertions on in-flight states are racy] → They poll for a state and then read computed styles. None asserts elapsed time. The `off` journeys give determinism.
- [Budget] → lib and hooks (0.5h), backdrop (1.5h), place card and vitals (1h), minimap pan (1.5h), clear and portrait (1h), Vitest (1.5h), browser (1h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
