# Minimap Island: One Affordance, One Readout

## Why

The minimap island currently offers the same action twice and says the same
thing twice.

1. **Two controls, one action.** Clicking the island's non-interactive body
   already opens the full map (`onIslandClick`, shipped since
   `webclient-map-01-draft-chrome` D5), and the header carries a separate
   labelled 展開全地圖 control that does exactly that and nothing else. The
   redesign draft draws no such button: its whole `.mini` card is the
   affordance, carrying only `title="展開全地圖"`
   (`docs/design/elosern-redesign/index.html`). The button exists solely
   because the island's body click is pointer-only — it is the keyboard path,
   wearing chrome. Change 03's baseline already shrank it to a 24 × 24 glyph to
   buy back header width; the honest end of that line is that the affordance
   should be the island, not a corner of it.

2. **The readout repeats what the surface already draws.** The detail line
   reads 「西部丘陵與谷地 · 目前所在 · 座標 60,107」. 「目前所在」 is a tautology —
   a minimap shows the current position by definition, and the canvas already
   draws that node as the large seal-stroked marker. 「西部丘陵與谷地」 is the
   place name, which belongs in the top-meta pill: the pill currently renders
   `panels.status.actor.location.label` (`stores/elosern.js:1838`), the raw room
   key, which is literally `Wilderness` for every wilderness cell — so the
   client knows the meaningful region name and shows it in the wrong place
   while showing a placeholder in the right one. Only the coordinate figure is
   something the island alone can say.

Both defects are chrome the island spends height and attention on while the map
itself is the thing the island exists for.

## What Changes

- **BREAKING** (spec text; pre-release, zero users): the island's visible
  full-map control is removed. Change 03 specified the header as
  "the title is the row's only elastic item … while the orientation marks and
  the header's **trailing control** SHALL be fixed-size items", and its baseline
  reduced that control to a 24 × 24 icon button. This change deletes that item
  outright. The header rule survives structurally — exactly one elastic item,
  every other header item fixed-size — with the trailing control no longer named
  as one of them.
- The island presents **exactly one** full-map affordance, with no visible
  button chrome: a full-bleed transparent `<button>` element spanning the
  island, carrying the accessible name 展開全地圖, layered beneath the island's
  visual content so the button element itself contains no focusable descendant.
  It is a real `<button>` (Enter/Space via the platform, never a key handler on
  a div), and its focus-visible treatment reads on the whole island rather than
  on a 24px corner.
- **BREAKING**: the island root does **not** gain `role="button"`. The
  `webclient-contextual-hud` requirement's clause "the island root SHALL NOT
  gain a button role or tab-stop of its own, so the labelled control below
  remains the only keyboard path" is amended: the root still gains no role and
  no tab-stop, but the keyboard path is now the full-bleed button rather than a
  labelled sibling. `role="button"` on `.local-map` is rejected outright — the
  island contains focusable descendants (the remembered-list items today, the
  named edge markers after change 05), and a `role="button"` element must not
  contain focusable descendants.
- The existing pointer path is unchanged: `onIslandClick` still skips clicks
  originating in `button, a, [tabindex], [data-node]`, so a click on an
  actionable lattice node still moves and never opens the map, and exactly one
  `open-map` is emitted per click on either path.
- The overlay's focus-restore contract is preserved by construction:
  `AppClient.onMapExpand` captures `document.activeElement` as the overlay's
  opener, so the opener must be a focusable element that still exists when the
  overlay closes — the full-bleed button is exactly that, and it is not
  re-created by a payload commit.
- **BREAKING**: the island's readout keeps only the coordinate figure. 「目前所在」
  is deleted; the place name moves to the top-meta pill; the hovered/selected
  node's label-and-state readout is removed. The island's readout is
  `座標 <x>,<y>` and nothing else, on coordinate-bearing layers only.
- Consequently the island keeps **no hover/selection state at all**: the
  readout is derived directly from the committed payload's current node, so it
  follows the payload by construction rather than by change 03's re-seed
  watcher. A node's name stays available on the canvas — `MapLattice` already
  draws each node's truncated label as visible text with its full label as the
  SVG `<title>` accessible name — and a remembered node's name stays the
  visible text of its own list item, so nothing that the detail line used to
  surface becomes unreachable.
- **BREAKING**: the top-meta location states the `local_map` panel's current
  node label when the panel carries one, falling back to the status panel's room
  label, and to the existing 「位置：--」 placeholder when neither is available.
  The `webclient-desktop-shell` scenario "the top-meta surface shows the current
  location label from the synced status panel" is amended accordingly. Nothing
  is fabricated: the client picks between two server-authored labels and never
  composes a third.
- The readout adopts the draft's `.compass` treatment as a **token-driven**
  rule (the shipped requirement forbids hardcoding draft values): the island's
  smallest type step, monospace, centred, de-emphasised, with no border,
  background, or padded box — never a copy of the draft's literal
  `font-size:10px; color:var(--paper-500); margin-top:5px` declaration block.
  On a coordinate-free layer (`interior`/`instance`) there is no coordinate
  figure, so the readout renders nothing; the "no empty box" rule change 03
  already specified governs that case unchanged and is not re-specified here.
- The `data-testid="local-map__expand"` hook **moves onto the new full-bleed
  button** rather than retiring. It names the role ("the island's full-map
  affordance"), not the chrome; four Vitest sites and the browser focus-restore
  gate select on it. See `design.md` D4.

Out of scope — each is owned by another change in this series:

- Redefining `remembered` as a map gateway rather than "any previously entered
  node outside the field of view" → `local-map-remembered-are-map-gateways`.
- Deleting the remembered list and naming the edge markers →
  `webclient-minimap-05-edge-markers-replace-list`.
- The draft's far-field dot field, fog vignette, axis cross, and the
  pitch/font-ratio question → `webclient-minimap-06-draft-lattice-fidelity`.

Not in scope at all: the `local_map` v1 payload, the server presenter, the
preserved UMD render model (`web/static/webclient/js/elosern/local_map.js`) and
its dependency-free Node gate, tap-to-move, and the overlay host's focus-trap
implementation. The project is pre-release with zero users, so there is no
backward-compatibility surface and no migration path to design.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`: "The browser minimap renders states without relying on
  color alone" — the island's detail-line clause becomes a current-node-only
  coordinate readout in the draft readout treatment (the hovered/selected-node
  label-and-state readout is removed, and the island keeps no hover/selection
  state), the header clause stops naming a trailing control, and the island
  gains its single full-bleed full-map affordance with its keyboard, focus, and
  opener-stability rules. The ban on any bearing/angle/distance/coordinate
  figure beyond the permitted current-node figure survives intact.
- `webclient-contextual-hud`: "The minimap island states only its own drawing
  convention" — the full-map affordance clause is amended (one affordance, no
  visible button chrome, a real `<button>` spanning the island, the root still
  without a role or tab-stop of its own, `role="button"` on the root forbidden),
  and the coordinate-figure clause is re-anchored on the current node itself
  rather than on "while the detail line shows the current node".
- `webclient-desktop-shell`: "Required desktop surfaces remain visible and
  usable" — the top-meta surface's location states the committed `local_map`
  current node's label when the panel carries one, falling back to the status
  panel's location label, so the pill stops showing the raw room key
  `Wilderness` while the minimap knows 「西部丘陵與谷地」.

## Impact

- Affected code: `web/webclient-app/components/LocalMap.vue` (the meta-row
  button and its icon removed; the full-bleed `<button>` added with the island
  root positioned and its content layered above it; `selectedId`, `hoveredId`,
  `activeNode`, `STATE_LABELS`, the `currentNode` re-seed watcher and the
  `@select`/`@hover`/`@leave` bindings removed; `detailParts` reduced to a
  current-node coordinate readout; the readout's and the affordance's CSS),
  `web/webclient-app/stores/elosern.js` (`statusSlice.locationLabel`'s
  fallback chain). `web/webclient-app/components/TopBar.vue` and
  `components/AppShell.vue` are untouched — they render the slice they are
  given. `web/webclient-app/components/MapLattice.vue` is untouched: the shared
  renderer keeps emitting `select`/`hover`/`leave`; the island simply stops
  listening.
- Affected tests: `web/webclient-app/tests/world/local_map.test.js` (the
  affordance's shape/name/keyboard assertions replace the icon-button
  assertions; the readout assertions drop the label/state parts and the hover
  and re-seed cases; new assertions that a node click never opens the map and
  that a body click still does),
  `web/webclient-app/tests/store/store_slices.test.js` (the location fallback
  order), `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`
  and `tests/overlays/map_overlay.test.js` (the `local-map__expand` selector
  stays valid, on the new element), `web/webclient-app/tests/top_bar.test.js`
  (unchanged — the component's contract does not move),
  `web/tests/browser/test_browser_contextual_hud.py` (the click-and-Escape
  focus-restore gate, still keyed on `local-map__expand`), and
  `web/tests/browser/test_browser_shell.py` (the top-meta location assertion,
  extended to prove a wilderness cell shows the region name rather than
  `Wilderness`).
- No server, protocol, or payload change; the Python/JS validator parity
  contract and the dependency-free Node gate are untouched.
- All three requirement titles are MODIFIED in place (no rename), so every
  existing `@covers_requirement` anchor on
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`,
  `webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`,
  and `webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable`
  stays valid.
- No player-facing command changes; `docs/game/commands.md` untouched.
