# Design

## Context

The `map` anchor's geometry lives in two copies that must stay in step (`web/webclient-app/AGENTS.md` "Styling pitfall"):

- `web/webclient-app/components/HudFrame.vue`, rule `.elosern-stage [data-anchor="map"]` (lines ~456-468 at HEAD 20b9f0c4): `top`, `right: calc(16px * var(--ui-scale))`, `width: calc(230px * var(--ui-scale))`, `gap: calc(9px * var(--ui-scale))`, `align-items: flex-end`, `max-height`, `overflow-y: auto`, `overflow-x: hidden`. It governs where no `.elosern-root` wraps the stage (Storybook).
- `web/webclient-app/styles/app-shell.css`, rule `.elosern-root .elosern-stage [data-anchor="map"]` (lines ~180-187): the same offsets plus `width: calc(var(--right-column) - 28px * var(--ui-scale))`, `align-items: stretch`, `gap: calc(14px * var(--ui-scale))`. Line ~191 gives both island anchors `scrollbar-color: #55524b transparent; scrollbar-width: thin;`. The `@media (max-height: 820px)` block (line ~207) narrows the `map` gap to 10px.

`--right-column` is `clamp(230px * S, 22vw, 360px * S)` in `styles/tokens.css` (line ~352) and `278px * S` under `@media (max-width: 1350px)` in `app-shell.css` (line ~433). S (`--ui-scale`) is `clamp(1, min(h / 790, w / 1451), 1.4)`. So the live column is 250px at 1280x720, 291.2px at 1451x790 and 464.8px at 2560x1440.

Two other surfaces offset from the column's left edge by re-deriving `--right-column`:

- `HudFrame.vue` `.elosern-stage [data-anchor="presence"]` (line ~594): `right: calc(var(--right-column, 258px * var(--ui-scale)) + 12px * var(--ui-scale));` (24px × S clear of the column's left edge, which is `--right-column - 12px` from the stage's right).
- `app-shell.css` `.elosern-root .scene-backdrop .scene-backdrop__placeholder` (line ~130): `right: calc(var(--right-column) + 12px * var(--ui-scale));`.

`.elosern-root .topbar-right` (`max-width: calc(var(--right-column) + 50px * var(--ui-scale))`) sizes the top band, not the stage, and `--actor-right-inset` in `tokens.css` uses its own 312px face-clearance constant; neither is a neighbour of the column box.

The approved prototype's column (`docs/design/map-column-instrument-panels/MapColumnPrototype.vue`, `.mcp-slot--proposal`) carries the width, the hidden scrollbar and the edge fade this change ports.

## Goals / Non-Goals

**Goals:**

- One token for the column width, read by both geometry copies and by every neighbour offset.
- A 10px × S gap in both copies at every viewport.
- A scrollbar-free over-tall column whose clipped edge fades only while content lies beyond it.

**Non-Goals:**

- Restyling `PlaceCard.vue`, `LocalMap.vue`, `ObjectiveTracker.vue`, `RiteEntry.vue` or `TitleBallotMenu.vue`; the shared instrument chrome arrives with `place-card-instrument-panel`.
- Changing `align-items` in either copy (HudFrame keeps `flex-end`, app-shell keeps `stretch`), the anchor's `top`, `right`, `max-height`, `z-index`, inert/aria-hidden bindings, the person-focus fade or the mode gates.
- Changing `--right-column`, `--actor-right-inset`, `.topbar-right` or the vitals anchor (it keeps its thin scrollbar).
- A reveal transition for the column (the prototype's `MapColumnStack` reveal is not ported; the anchor's existing opacity transitions stay).
- Deleting or editing the prototype under `docs/design/map-column-instrument-panels/`.

## Decisions

### D1. `--map-column-w` token in `tokens.css`

Add next to `--right-column` in `web/webclient-app/styles/tokens.css`, verbatim:

```css
    /* The right-hand `map` column's width (map-column-instrument-geometry):
       the right column less its 28px gutter, never narrower than the
       minimap instrument panel needs (a 240px canvas, 22px of spine
       clearance and a 20px feather). HudFrame.vue's and app-shell.css's
       `map` anchor rules and every offset taken from the column's left
       edge read this one token. */
    --map-column-w: max(calc(var(--right-column) - 28px * var(--ui-scale)), calc(282px * var(--ui-scale)));
```

It is declared on the same `:root` block as `--right-column`, so the `@media (max-width: 1350px)` override of `--right-column` on `:root` flows into it. Alternative considered: writing the `max(...)` expression inline in both copies and the neighbours. Rejected: four hand copies of one number, which the style guide forbids (§ 版面與幾何: neighbours derive from one design token, like `--vitals-dock-w`).

### D2. Both geometry copies

`HudFrame.vue` `.elosern-stage [data-anchor="map"]` becomes (only `width`, `gap` and the scrollbar line change; every other declaration stays byte-identical):

```css
.elosern-stage [data-anchor="map"] {
  top: calc(var(--header-h) + var(--stage-inset-y));
  right: calc(16px * var(--ui-scale));
  width: var(--map-column-w);
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--ui-scale));
  align-items: flex-end;
  max-height: calc(100% - var(--header-h) - var(--band-h) - 2 * var(--stage-inset-y));
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
}
```

`app-shell.css` `.elosern-root .elosern-stage [data-anchor="map"]` becomes `width: var(--map-column-w);` and `gap: calc(10px * var(--ui-scale));` (other lines unchanged). In the same file:

- Line ~191 becomes `.elosern-root [data-anchor="vitals"] { scrollbar-color: #55524b transparent; scrollbar-width: thin; }` (the `map` arm is dropped: at equal specificity it would come after HudFrame's `scrollbar-width: none` and win).
- In `@media (max-height: 820px)` delete the line `.elosern-root .elosern-stage [data-anchor="map"] { gap: calc(10px * var(--ui-scale)); }` and reword the comment above it so it no longer mentions the map column's gap (leave the `.place-card` lines and their comment sentence about the place card in place; `place-card-instrument-panel` removes them).

Update the comments above both rules to say the width is `--map-column-w`.

### D3. Neighbour offsets

- `HudFrame.vue` presence: `right: calc(var(--map-column-w) + 40px * var(--ui-scale));` (16px stage gutter + 24px clearance; identical to today's `--right-column + 12px` wherever the floor is not in force). Update the comment above it: the column's left edge is `16px + --map-column-w` from the stage's right edge.
- `app-shell.css` placeholder: `right: calc(var(--map-column-w) + 40px * var(--ui-scale));`.

### D4. Hidden scrollbar and edge fade in `HudFrame.vue`

Add after the `map` rule, verbatim:

```css
/* An over-tall `map` column (map-column-instrument-geometry): no scrollbar
   (it would cross the instrument panels' spines and take their width); the
   clipped edge fades out over 32px only while content lies beyond it. The
   mask drops the panels' backdrop blur while it applies (their ink is 90%
   opaque, so the loss is negligible). */
.elosern-stage [data-anchor="map"]::-webkit-scrollbar {
  display: none;
}
.elosern-stage [data-anchor="map"][data-more-above],
.elosern-stage [data-anchor="map"][data-more-below] {
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 var(--map-fade-top, 0px), #000 calc(100% - var(--map-fade-bottom, 0px)), transparent 100%);
  mask-image: linear-gradient(180deg, transparent 0, #000 var(--map-fade-top, 0px), #000 calc(100% - var(--map-fade-bottom, 0px)), transparent 100%);
}
.elosern-stage [data-anchor="map"][data-more-above] {
  --map-fade-top: calc(32px * var(--ui-scale));
}
.elosern-stage [data-anchor="map"][data-more-below] {
  --map-fade-bottom: calc(32px * var(--ui-scale));
}
```

Both custom properties carry stylesheet fallbacks, so the Node gate (`web/static/webclient/js/tests/ui_contract.test.js`, "every custom property consumed without a fallback is defined") stays green. Alternative considered: a pseudo-element gradient overlay. Rejected: it would paint ink over the scene instead of revealing it, and would need its own stacking above every panel.

### D5. `useScrollEdgeFade` composable

New file `web/webclient-app/composables/use-scroll-edge-fade.js`, exporting exactly:

```js
// Pure: which edges of a scroll box have content beyond them. 1px of
// tolerance absorbs sub-pixel scroll positions.
export function scrollEdges({ scrollTop, clientHeight, scrollHeight }) {
  return {
    above: scrollTop > 1,
    below: scrollTop + clientHeight < scrollHeight - 1,
  };
}

// Reactive: `{ moreAbove, moreBelow }` refs for the element in `elRef`.
export function useScrollEdgeFade(elRef) { /* ... */ }
```

`useScrollEdgeFade` behaviour:

1. `moreAbove` / `moreBelow` are `ref(false)`; `measure()` reads `elRef.value` and assigns `scrollEdges(el)`; with no element both are `false`.
2. On `onMounted`, and whenever `elRef` changes (`watch(elRef, attach, { flush: "post" })`): remove the old listeners/observers, add a passive `scroll` listener calling `measure`, create a `ResizeObserver(measure)` observing the element and each of its current `element.children`, create a `MutationObserver` with `{ childList: true }` on the element whose callback re-runs the child observation (disconnect the ResizeObserver, observe the element and every current child again) and then `measure()`, and call `measure()` once.
3. When `typeof ResizeObserver === "undefined"` (jsdom) skip the ResizeObserver; when `typeof MutationObserver === "undefined"` skip it; the scroll listener and the initial measure always run.
4. `onBeforeUnmount` removes the listener and disconnects both observers.

In `HudFrame.vue`: import it, add `const mapAnchorRef = ref(null); const { moreAbove: mapMoreAbove, moreBelow: mapMoreBelow } = useScrollEdgeFade(mapAnchorRef);`, and on the `map` anchor element add `ref="mapAnchorRef"`, `:data-more-above="mapMoreAbove || null"`, `:data-more-below="mapMoreBelow || null"` (an absent attribute, never `"false"`, so the attribute selectors in D4 stay simple).

Alternative considered: the prototype's ResizeObserver-only measurement. Rejected: the live column mounts and unmounts children (`LocalMap`, `ObjectiveTracker`, `RiteEntry`, `TitleBallotMenu`); a child mounted after setup is never observed, and the anchor's own box does not resize once it is at max-height, so the fade would go stale.

### D6. Tests

- `web/webclient-app/tests/hud_frame.test.js`, new `it("reads the map column width from one token in both geometry copies and every neighbour", ...)` using the file's existing `styleBlock` / `extractRule` helpers and `readFileSync`:
  - `tokens.css` contains the exact D1 declaration line.
  - Both `extractRule(styleBlock("components/HudFrame.vue"), '.elosern-stage [data-anchor="map"]')` and `extractRule(appShellCss, '.elosern-root .elosern-stage [data-anchor="map"]')` contain `width: var(--map-column-w);` and `gap: calc(10px * var(--ui-scale));`, and neither contains `--right-column`.
  - The HudFrame rule contains `scrollbar-width: none;`; `app-shell.css` contains no rule whose selector includes `[data-anchor="map"]` and whose body includes `scrollbar` (assert `appShellCss` does not match `/\[data-anchor="map"\][^{]*\{[^}]*scrollbar/`).
  - The HudFrame style block contains the D4 mask rule and both `--map-fade-*` assignments.
  - The presence rule contains `right: calc(var(--map-column-w) + 40px * var(--ui-scale));` and the placeholder rule in `app-shell.css` contains the same `right:` line.
  - Update the existing presence assertion (`expect(anchor).toMatch(/right: calc\(var\(--right-column/)`, line ~407) to `/right: calc\(var\(--map-column-w\)/`.
  - Mount `HudFrame` and assert the map anchor carries neither `data-more-above` nor `data-more-below` in jsdom (no layout, so every measurement is 0).
- New `web/webclient-app/tests/use_scroll_edge_fade.test.js`:
  - `scrollEdges` table: `{0, 100, 100}` → neither; `{0, 100, 300}` → below only; `{100, 100, 300}` → both; `{200, 100, 300}` → above only; `{0.5, 100, 100.5}` → neither (tolerance).
  - Composable: mount a tiny component that renders a `div` bound to the ref; stub the element's `scrollTop`/`clientHeight`/`scrollHeight` with `Object.defineProperty`, dispatch `scroll`, assert the refs; install a fake `globalThis.ResizeObserver` class recording `observe` targets and exposing its callback, append a child, flush the MutationObserver (`await Promise.resolve()` twice), assert the new child was observed and the refs re-measured; unmount and assert `disconnect` was called. Restore globals in `afterEach`.
- New file `web/tests/browser/test_browser_map_column_instruments.py` (module docstring: live-client acceptance for the map column's instrument panels; the later changes of this batch add their methods here), class `MapColumnInstrumentBrowserTest(BrowserAcceptanceTest)` (import `BrowserAcceptanceTest, ui_scale` from `.browser_base`, panel helpers from `.browser_helpers`, `covers_requirement` from `tools.spec_traceability`), with a module-level `_objectives_panel(count)` copied from `test_browser_shell_surfaces.py` and one method `test_map_column_holds_its_width_and_fades_hidden_overflow`, decorated `@covers_requirement("webclient-contextual-hud::the-map-column-holds-its-instrument-geometry-and-fades-hidden-overflow", "webclient-contextual-hud::the-hud-island-stack-renders-as-bounded-floating-islands-not-column-cards")`. Live client (`self.logged_in_page(viewport)`), snapshot with `valid_status_panel(...)`, `valid_local_map_panel()`, `valid_art_panel()` and `_objectives_panel(1)`, injected with `inject_snapshot(page, panels, mode="exploration")`, then `page.evaluate("document.fonts.ready")`:
  - For `(1280, 720) → 282`, `(1451, 790) → 291.2`, `(2560, 1440) → 464.8`: the `[data-anchor="map"]` rect width equals the expected value (delta 1.0); stage right minus anchor right equals `16 * ui_scale(viewport)` (delta 1.0); anchor `offsetWidth == clientWidth`; anchor computed `background-color` is `rgba(0, 0, 0, 0)`, `border-top-width` is `0px`, `box-shadow` is `none`; `[data-anchor="presence"]` rect right is `anchor.left - 24 * ui_scale(viewport)` (delta 1.0); the vertical distance between `[data-testid="place-card"]`'s bottom and the next anchor child's top equals `10 * ui_scale(viewport)` (delta 1.0).
  - At 1451x790 and 2560x1440: the anchor has neither `data-more-above` nor `data-more-below` and computed `mask-image` is `none`.
  - At 1280x720, whether the populated column fits is not stable across this batch (`place-card-instrument-panel` removes the 820px place-card compaction, after which the column fits by under about 2px), so no assertion there depends on whether it fits. Set the anchor's `scrollTop` to 0, read a baseline `{above: hasAttribute("data-more-above"), below: hasAttribute("data-more-below")}` (`above` must be false; `below` is recorded, not asserted). Append a probe child (`div`, `data-testid="map-overflow-probe"`, inline `height: 600px; flex: none`) to the anchor, wait until `data-more-below` is present (no scroll event dispatched), assert computed `mask-image` is not `none` and `data-more-above` is absent; set `scrollTop` to half of `scrollHeight - clientHeight`, wait for both attributes; set `scrollTop` to `scrollHeight`, wait until only `data-more-above` remains; remove the probe, set `scrollTop` to 0, and wait until the attributes equal the baseline.
  - At 1451x790 (where the column fits): append the same probe, wait until `data-more-below` is present, remove it, and wait until neither attribute remains and computed `mask-image` is `none`. This is the "a column that comes to fit loses every fade" assertion.
  - The 32px × S fade depth is established by the source assertion above on the two `--map-fade-*: calc(32px * var(--ui-scale));` lines, not by the browser test: unregistered custom properties do not compute to pixels, so the browser test only asserts that the mask is present or absent.
  - Register it with `uv run --locked python -m tools.shard_register fix`.

### D7. Visual review (human-reviewed)

The review document for this batch is `docs/design/map-column-instrument-panels/` (the approved prototype, Storybook title `Design/MapColumnInstrument`) compared against live-client screenshots. For this change the human checks only: the column's right gutter and width match the prototype's proposal column at 1280x720, 1451x790 and 2560x1440, and at 1280x720 the over-tall column fades at its clipped edge with no scrollbar. The implementer captures those screenshots with `agent-browser` into the session scratchpad and lists their paths in the apply report; no test asserts the look.

## Risks / Trade-offs

- [The mask drops the panels' backdrop blur while an edge fades] → accepted in the approved decision; the ink is 90% opaque. The mask applies only while content overflows.
- [The widened column (282px at ≤1350px wide viewports) narrows the open stage by 32px] → the presence rail and placeholder follow the token (D3); the `actor-right` face-clearance constant is unaffected at the acceptance viewports (its centre stays left of the column edge: 311px vs 298px from the right at 1280x720).
- [A hidden scrollbar hides that the column scrolls] → the edge fade is the affordance, and wheel/keyboard/touch scrolling are unchanged.
- [MutationObserver re-observation churn] → `childList` only (no subtree, no attributes); the column has at most four children.

## Migration Plan

None (pre-release, client-only CSS and one composable).
