## Why

The `webclient-contextual-hud` capability already requires that "the narrative caption and the
right-hand HUD stack SHALL be positioned relative to [the dock] so they never overlap it" and that "at
both 1440x900 and 1280x720 no stage anchor SHALL overlap another anchor's content." Live verification
against the running client (`podman compose` image `elosern-mud:edge`, 1440×900, art generation
offline so the scene backdrop is in its placeholder state) shows this invariant broken by the scene
backdrop's own floating captions: `SceneBackdrop.vue`'s five absolutely-positioned caption elements
(`.scene-backdrop__placeholder`, `__generating`, `__scene-label`, `__scene-alt`, `__fullview-control`,
lines 335–424) each position their `bottom` offset as `calc(var(--dock-h) + Npx)` for small `N`
(12/44/56px). This assumes the action dock's top edge sits exactly `--dock-h` above the viewport
bottom, but `HudFrame.vue:173-187` places the dock anchor at `bottom: 46px; height: var(--dock-h)` —
*above* the 46px-tall persistent command line — so the dock's actual top edge sits `--dock-h + 46px`
above the viewport bottom, not `--dock-h`. Every scene-backdrop caption is therefore under-offset by
exactly the missing 46px and renders roughly 34–46px lower than intended, landing inside the action
dock's own tab-bar row instead of floating above it. Screenshotted and DOM-measured: at 1440×900 the
`.scene-backdrop__placeholder-label` ("無法提供") sits at y≈676–695 while the dock's own top edge is at
y=670 — a 25px intrusion directly over the dock's rightmost tabs — exactly the visual clutter flagged
in this review ("garbled overlapping chip floating over the dock").

The same root-cause pattern (a `--dock-h`-only offset that omits the command line's height) also
under-shoots `HudFrame.vue:167`'s narrative-caption anchor offset (`bottom: calc(var(--dock-h) + 60px)`
where 60px happens to be large enough to avoid a visible collision today, but leaves far less headroom
than the design intends and would collide if the caption grows or the buffer shrinks). Both call sites
should be fixed together since they share one root cause and one fix.

## What Changes

- Add a single shared stage-content-bottom token to `styles/tokens.css` (e.g. `--stage-content-bottom:
  calc(var(--dock-h) + 46px)`, where 46px is the persistent command line's own height, already a magic
  number duplicated at `HudFrame.vue:176` and `:186`) so every anchored-above-the-dock surface computes
  its offset from one place instead of re-deriving the command-line height by hand.
- Update `SceneBackdrop.vue`'s five `bottom: calc(var(--dock-h) + Npx)` rules and `HudFrame.vue`'s feed
  anchor rule (`bottom: calc(var(--dock-h) + 60px)`) to add their existing buffer on top of
  `--stage-content-bottom` instead of `--dock-h` alone.
- No change to `.elosern-stage [data-anchor="dock"]`'s or `[data-anchor="command-line"]`'s own
  positioning (`HudFrame.vue:172-188`) — those two are already correct (the dock is already offset by
  the literal 46px); only the *consumers* that derive a position relative to the dock without also
  accounting for the command line are wrong.
- **BREAKING**: none. Pure CSS positioning correction; no DOM structure, testid, prop, or protocol
  change. Visually, the affected captions move up by ~46px (into the gap between the dock and the
  scene) and no longer intrude into the dock's tab-bar row.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the "scene backdrop renders the art payload truthfully behind the stage"
  requirement gains an explicit scenario that the backdrop's own floating caption elements (placeholder,
  generating notice, scene label/alt, full-view control) never overlap the action dock or command-line
  anchors, extending the existing sibling requirement's general "no stage anchor SHALL overlap another
  anchor's content" invariant to this specific, previously-unstated case (these captions are children of
  the scene-backdrop layer, not one of the five named stage anchors, so the general requirement did not
  literally cover them before this change).

## Impact

- **Code**: `web/webclient-app/styles/tokens.css` (new `--stage-content-bottom` token),
  `web/webclient-app/components/SceneBackdrop.vue` (five `bottom` rules), `web/webclient-app/components/
  HudFrame.vue` (the `[data-anchor="feed"]` rule only — `[data-anchor="dock"]` and
  `[data-anchor="command-line"]` are unchanged).
- **Tests**: extend `web/tests/browser/test_browser_art.py` (which already exercises the placeholder,
  missing, and unavailable scene states via `[data-testid="scene-backdrop-placeholder"]` and covers the
  `webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage`
  requirement) with a bounding-box non-overlap assertion between each scene-backdrop caption and the
  action dock, at both 1440×900 and 1280×720 — mirroring the existing anchor non-overlap pattern already
  used by `test_browser_contextual_hud.py::test_command_line_never_overlaps_dock_caption_or_hud` and the
  `_anchors_overlap` helper in `test_browser_layout.py`.
- **No protocol, read-model, or component-inventory changes.**
