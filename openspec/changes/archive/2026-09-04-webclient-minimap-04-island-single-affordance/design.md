# Design — Minimap Island: One Affordance, One Readout

## Context

The minimap island is `web/webclient-app/components/LocalMap.vue`, mounted in
the stage's `[data-anchor="hud-right"]` column (230px wide, 210px content box
inside the island's 9px padding and 1px border). Change 03
(`webclient-minimap-03-canvas-scale-and-budget`) is this change's baseline: it
fixed the height-budget ratchet, made the canvas claim the card's width, made
the header a single localization-safe row with the title as its only elastic
item, and made the readout line paint no box when it has nothing to say. The
same pass reduced the header's 展開全地圖 control to a 24 × 24 icon button —
change 03 deliberately declined to specify that reduction, on the record,
"because change 04 removes the visible control outright". This is that change.

Three facts constrain what "the whole island is the button" can mean here:

1. **The island contains focusable descendants.** Today the remembered-list
   items carry `tabindex="0"`; after
   `webclient-minimap-05-edge-markers-replace-list` the named edge markers take
   over that reading path. A `role="button"` element must not contain focusable
   descendants (ARIA's `button` role has a presentational-children contract);
   doing it anyway is invalid ARIA with unpredictable screen-reader behaviour.
2. **The overlay's opener is `document.activeElement`.**
   `AppClient.onMapExpand` → `openOverlayByName("map")` captures
   `document.activeElement` at open time and the host restores focus to it on
   close (`AppClient.vue:549-567`). The opener must therefore be a real,
   focusable element that still exists after the overlay closes.
3. **The pointer path already works and must keep working.**
   `onIslandClick` opens the map from the island's body while skipping clicks
   that originate in `button, a, [tabindex], [data-node]`, so activating a
   lattice node moves rather than opening the map.

On the readout side: the line renders
`[node.label, STATE_LABELS[visibility], "→ destination"?, "座標 x,y"?]` joined
with ` · `, driven by `hoveredId`/`selectedId` from the shared renderer's
`select`/`hover`/`leave` events. Meanwhile the top-meta pill renders
`statusSlice.locationLabel`, derived at `stores/elosern.js:1838` from
`panels.status.actor.location.label` — the raw room key, literally `Wilderness`
for every wilderness cell, while the map payload's current node carries
「西部丘陵與谷地」.

## Goals / Non-Goals

**Goals:**

- The island offers exactly one full-map affordance, with no visible button
  chrome, reachable by pointer **and** by keyboard through a real `<button>`.
- The affordance is valid ARIA: no `role="button"` wrapping focusable
  descendants, no key handler standing in for a button's platform behaviour.
- The overlay's focus-restore contract is preserved without a special case.
- The island's readout states only what the island alone can state: the current
  node's coordinate figure on a coordinate-bearing layer.
- The place name is stated once, in the surface that exists to state it (the
  top-meta pill), from the best label the client already holds.
- Nothing that the detail line used to surface becomes unreachable.

**Non-Goals:**

- The meaning of `remembered` (`local-map-remembered-are-map-gateways`) and the
  removal of the remembered list
  (`webclient-minimap-05-edge-markers-replace-list`).
- The draft's dot field, fog vignette, axis cross, and pitch/font ratios
  (`webclient-minimap-06-draft-lattice-fidelity`).
- The canvas's sizing, the height budget, and the header's elastic-title rule —
  all change 03's, all unchanged here except that this change removes the item
  change 03 called "the header's trailing control".
- Any change to the payload, the presenter, the preserved UMD render model, or
  the overlay host's focus-trap implementation.

## Decisions

### D1 — The affordance is a full-bleed transparent `<button>` layered beneath the island's content

`LocalMap.vue`'s available branch renders, as its first child, a
`<button type="button" class="local-map__affordance" aria-label="展開全地圖">`
with no content, positioned `absolute; inset: 0` inside a now
`position: relative` `.local-map`, at `z-index: 0`, with the island's own
`border-radius`, transparent background and no border. Every other island child
is raised to `position: relative; z-index: 1`.

That geometry buys three things at once:

- **Keyboard.** It is a real `<button>`, so Enter and Space activate it through
  the platform, it is in the tab order without a `tabindex`, and it exposes the
  `button` role and the accessible name 展開全地圖 to assistive tech. Placing it
  first in DOM order makes the island's primary action its first tab stop,
  ahead of the remembered list's focusable items.
- **Valid ARIA.** The button element is empty. The lattice nodes, the
  remembered items, and (after change 05) the named edge markers are siblings
  of it, not descendants, so the button never contains a focusable descendant
  no matter what the island's content becomes.
- **Focus indication on the whole island.** Because the button *is* the
  island's box, `:focus-visible` on the button draws a ring around the entire
  island — the owner's 「島嶼整塊當成按鈕」 read — with no `:has()` selector and no
  second element to keep in sync.

**Pointer behaviour is unchanged, and stays single-emit.** Content sits above
the button, so a click on visible content (the readout text, the canvas
background, the header) targets that content and reaches `onIslandClick`, which
emits `open-map` exactly as today. A click on genuinely empty island area
(padding, the flex gaps between sections) lands on the button, which emits
`open-map` itself — and `onIslandClick`, which also sees that bubbling click,
skips it because `event.target.closest("button, a, [tabindex], [data-node]")`
matches the button. Keyboard activation produces the same bubbling click and is
skipped by the same guard. So every path emits exactly one `open-map`, and a
click that originates in a lattice node group (`[data-node]`) or a remembered
item (`[tabindex]`) still emits none.

*Alternatives rejected:*

- **`role="button" tabindex="0"` on `.local-map` (the literal reading of
  「島嶼整塊當成按鈕」).** Invalid ARIA for the reason in Context (1): the island
  contains focusable descendants today and will contain more after change 05.
  It also forces a hand-written `keydown` handler to reimplement Enter/Space,
  which is exactly the div-as-button anti-pattern, and it would flatten the
  island's content into a single accessible-name computation for screen
  readers. It is additionally forbidden by the shipped
  `webclient-contextual-hud` clause "the island root SHALL NOT gain a button
  role or tab-stop of its own", which this change keeps rather than relaxes.
- **A visually-hidden-until-focused button (the classic skip-link pattern).**
  It is valid and small, but it re-introduces visible chrome the moment it
  matters: the control appears out of nowhere on Tab, in a place the pointer
  user never sees, so pointer and keyboard users get two different islands. Its
  focus ring is also a small floating box rather than the island, which is the
  opposite of the owner's instruction. The full-bleed layer gives keyboard users
  the *same* affordance pointer users have, indicated on the same geometry.
- **Keeping the 24 × 24 icon button.** This is the status quo change 03
  shipped as a stopgap. It costs 24px of the 210px header row plus its 8px gap
  — with it gone the elastic title's space rises from ~124px to ~156px (+26%)
  and the meta row's own height drops from the button's 24px back to the 10px
  header line's ~15px, returning ~9px to the canvas budget — and it is a second
  control for an action the island body already performs.
- **`<a href>` or a wrapping anchor.** There is no URL; the overlay is client
  state. A link would lie about navigation semantics and pollute the browser's
  link affordances.

### D2 — The opener is stable by construction, not by a special case

`onMapExpand` captures `document.activeElement`. Pointer activation of a
`<button>` focuses it in the engines the browser suite runs, and keyboard
activation obviously does; either way the captured opener is the full-bleed
button. That button is rendered by the island's available branch and is not
keyed on the payload, so a payload commit while the overlay is open re-renders
around it rather than replacing it, and it still exists when the overlay closes.

The regression proof is the existing browser gate
(`web/tests/browser/test_browser_contextual_hud.py:640-666`): click the island's
affordance, open the map overlay, press Escape, assert
`document.activeElement`'s `data-testid` is `local-map__expand`. That assertion
is why D4 moves the identifier rather than retiring it.

*Alternative rejected:* have `LocalMap` emit the element to focus on close, or
have `AppClient` resolve the opener by selector. Both replace a working
generic contract (whatever was focused is the opener) with map-specific
plumbing, for no gain — the generic contract is already satisfied.

### D3 — The island stops tracking hover and selection entirely

With the readout reduced to the current node's coordinates, `selectedId`,
`hoveredId`, `activeNode`, `STATE_LABELS`, change 03's `currentNode` re-seed
watcher, and the `@select`/`@hover`/`@leave` bindings on the island's
`<MapLattice>` have no consumer left. They are removed from `LocalMap.vue`. The
readout becomes a pure function of the committed payload — which makes change
03's "the detail line's active node SHALL follow the committed payload"
guarantee hold *by construction* rather than by a watcher, and makes both
staleness paths that change 03's D6 patched structurally impossible.

`MapLattice.vue` is **not** edited: it keeps emitting `select`/`hover`/`leave`
as the stateless shared renderer's event surface (the overlay does not bind
them either today), so change 05/06 can consume them without re-adding an API.

**What still surfaces a node's name**, so nothing is lost:

- On the canvas, `MapLattice` already draws every in-view node's label as
  visible text truncated to `labelMax` glyphs, with the full label in an SVG
  `<title>` — which is the node's accessible name and its pointer tooltip
  (`MapLattice.vue:513-518`). The shipped clause "each node's full label SHALL
  remain available as its accessible name" is satisfied there, not by the
  detail line.
- A remembered node's name is the visible text of its own list item
  (`.local-map__node-label`), so the shipped rule "SHALL allow focusing a
  remembered remote node to view its name/landmark without any travel action"
  keeps holding after the detail line stops echoing the focused item.
- The current node's *place name* moves to the top-meta pill (D5), where it is
  visible without any interaction at all.

*Alternatives rejected:*

- **Keep hover/selection and drive a tooltip or an aria-live announcement.**
  It re-adds the readout under another name, and a live region announcing every
  hovered node on a 3×3 wilderness lattice is noise, not information.
- **Keep the state machine but render nothing from it.** Dead state that the
  next reader has to prove is dead; the events remain available on the renderer
  if a later change needs them.

### D4 — `data-testid="local-map__expand"` moves onto the new element

The identifier names a **role** — "the island's full-map affordance" — not the
chrome that role happened to wear. Its four consumers all still mean exactly
what they meant:

| site | what it asserts | still valid? |
| --- | --- | --- |
| `web/tests/browser/test_browser_contextual_hud.py:646,665` | clicking it opens the map overlay; Escape restores focus to it | yes — and it is the only browser-level proof of the opener contract this change touches |
| `tests/overlays/deferred_surfaces_absent.test.js:400` | the island has a live mount path to the map overlay | yes |
| `tests/overlays/map_overlay.test.js:38,61` | the overlay does **not** render an island affordance | yes |
| `tests/world/local_map.test.js:317` | clicking it emits `open-map` exactly once | yes |

Retiring the id would delete the browser focus-restore gate at the exact moment
this change makes it riskier, and renaming it would churn five files to say the
same thing. The two assertions that describe the *old chrome* —
`local_map.test.js:434-438` (`aria-label` + `title` + empty text +
`svg.local-map__expand-icon`) — are rewritten by this change, which is correct:
they established the treatment being removed.

*Alternative rejected:* retire `local-map__expand` and introduce
`local-map__affordance`. Cleaner-sounding, strictly worse: it forces a rename
across a Python browser suite and three Vitest files for zero behavioural
difference, and it briefly leaves the focus-restore assertion selecting on
nothing.

### D5 — The place name moves to the top-meta pill, with a two-step fallback

`statusSlice.locationLabel` (`stores/elosern.js:1838`) becomes:

1. the committed `local_map` panel's current node's `label`, when the panel is
   available, carries a `current_node`, that id resolves to a node in the
   panel's `nodes`, and that node's `label` is a non-empty string;
2. otherwise `panels.status.actor.location.label`;
3. otherwise null — and `TopBar.vue` renders its existing 「位置：--」
   placeholder, unchanged.

The client never composes a third string from the two, never derives a label
from an id, and never renders a node id as a name. `TopBar.vue` and
`AppShell.vue` are untouched: they render the slice they are handed, so the
derivation stays in the one place that already owns "what the pill says".

Why the map label wins where both exist: the status panel's label is the room
key (`Wilderness` for every wilderness cell — the same string for a continent),
while the map payload's current-node label is the presenter's authored place
name (the region display name on the wilderness layer,
`_grid_room_label(...)`/the canonical room name elsewhere). On layers where the
two agree the choice is invisible; on the wilderness layer it is the whole
defect. The rule is stated as a preference order rather than "use the map label
on wilderness", so it degrades correctly for any layer and needs no layer
table.

Why the fallback must stay: the `local_map` panel can be unavailable (the
registry-owned unavailable form), can be rejected by its validator (the minimap
disables only itself), or can simply not have arrived yet, and the top-meta
pill is a required shell surface that must keep stating something truthful in
all three cases.

*Alternatives rejected:*

- **Fix the server presenter to author a better `status.actor.location.label`
  for wilderness rooms.** Arguably the deeper fix, but it is a payload/presenter
  change in a change whose whole scope is the island's chrome, it would change
  a shared status field several surfaces read, and the client already holds the
  better label. Left on the table for a status-presentation change.
- **Render both (`Wilderness · 西部丘陵與谷地`).** Restores the duplication this
  change exists to remove.
- **Derive the pill's label in `TopBar.vue` from a new `localMap` prop.** Pushes
  cross-panel logic into a presentational component and gives the pill two
  sources to reconcile at render time.

### D6 — 「目前所在」 goes, and the surviving figure is exactly the current node's two payload integers

The readout becomes `座標 <x>,<y>`, and nothing else.

- 「目前所在」 was `STATE_LABELS.current` — a state label for a node the canvas
  already marks with the large seal-stroked "you are here" marker, in a widget
  whose entire subject is where you are. It carries no information at any
  viewport.
- The place name is now the pill's (D5).
- The `→ destination` part disappeared with the hovered/selected node (D3): the
  current node never carries an `action`, so that part could only ever render
  for another node.

The shipped ban is preserved verbatim in the requirement text: no surface
renders a compass angle, a bearing angle, a distance, or any coordinate figure
beyond the permitted current-node figure, and the permitted figure is exactly
the `current` node's own payload `x` and `y` as committed, on the closed
coordinate-bearing set (`grid`, `wilderness`) only — no unit, no delta, no
derived quantity, never for another node, never on a coordinate-free layer,
never on the overlay. Removing the hovered-node readout strictly *shrinks* the
surface that ban has to police.

On `interior`/`instance` the readout resolves to nothing. What the island shows
then is already specified by change 03 — the line states nothing, paints no
box, and reserves no height in the canvas budget — and is referenced rather than
re-specified here.

### D7 — The readout treatment is specified as tokens and roles, not as the draft's declaration block

The draft's `.mini .compass` is
`font-size:10px; color:var(--paper-500); margin-top:5px; text-align:center;
font-family:var(--f-mono)`. The shipped requirement forbids a component
hardcoding a draft value, so the spec states the *treatment*: the island's
smallest type step, monospace from the shared font token, centred, at a
de-emphasised paper tier whose contrast against the island's panel is at least
4.5:1, separated from the canvas by a step from the shared spacing scale, with
no border, background, or padded box — one line, never a framed widget.

Concretely that resolves to `--f-mono`, `--paper-500` and `--sp-1`, and the
10px step the island's own header row already uses. Moving from the shipped
`--paper-300` (9.58:1) to `--paper-500` (4.98:1 on `--panel`) is deliberate and
is what change 03's own comment predicted would become correct: change 03 kept
the brighter tier *because* the line then stated the live node, its state and
its coordinates; now it states one secondary figure beside a canvas that is the
primary content, matching the meta row that already ships at the same size and
tier. 4.98:1 clears WCAG AA for body text.

*Alternatives rejected:* copy the draft's declarations literally (banned, and
`5px`/`10px` are draft-canvas numbers, not this island's ramp); keep
`--paper-300` (the figure would out-shout the map it annotates, and the island
would carry two competing 11px text tiers).

### D8 — Three capabilities, because three of them genuinely own a clause

- `webclient-local-map` owns the renderer's behaviour: the detail-line clause,
  the coordinate rule, the header rule, and the island's affordance/keyboard
  rules. Modified.
- `webclient-contextual-hud` owns the island's HUD chrome contract, and its
  "The minimap island states only its own drawing convention" requirement
  literally says "the island root SHALL NOT gain a button role or tab-stop of
  its own, so **the labelled control below remains the only keyboard path**",
  with a scenario asserting "the labelled expand control remains the keyboard
  path". This change removes that labelled control, so the clause and the
  scenario must be amended here rather than silently contradicted. Modified.
- `webclient-desktop-shell` owns the top-meta surface: "The shell … SHALL show
  the current location", with the scenario "the top-meta surface shows the
  current location label **from the synced status panel**". The pill's source is
  changing, so this is the requirement that must say so. Modified.

`webclient-status-presentation` is **not** modified: the status payload, the
server's read-only location derivation, and the `status` panel's own contract
are untouched — the client only chooses between two already-committed labels.

All three requirements are MODIFIED in place with no rename, so every existing
`@covers_requirement` anchor stays valid and
`tools.spec_traceability check` must be green in the same commit.

## Risks / Trade-offs

- **A transparent full-bleed button is invisible to a pointer user, so the
  island's clickability is only signalled by chrome** → It already is, and
  unchanged: `.local-map { cursor: pointer }` plus the `:hover` border shift
  ship today, and the draft's own affordance is exactly this (a `.mini` card
  with `cursor:pointer` and a `title`). The button adds a keyboard and AT path
  to an affordance the pointer user already had.
- **Content stacking is now load-bearing: a future island child that forgets
  `z-index: 1` would sit under the button and lose its own clicks** → The rule
  is written as "every other island child is raised", i.e. a `:not()` rule on
  the island's direct children rather than a per-child opt-in, so a new child
  is raised by construction; and the Vitest suite asserts that a lattice-node
  click still moves rather than opening the map, which is the failure that
  regression would produce.
- **Two emit paths for one action (the button's own `@click` and
  `onIslandClick`)** → The guard that makes them exclusive is the one already
  shipped and already tested (`closest("button, a, [tabindex], [data-node]")`);
  the new element is a `button`, the first token in that list. The suite pins
  "exactly one `open-map`" for a body click, a button click, a keyboard
  activation, and asserts zero for a node click.
- **The pill's label now changes when the map panel changes, not only when the
  status panel does** → That is the intent (the label follows the room you are
  in either way), and both panels are committed from the same snapshot at the
  same revision, so they cannot disagree about *which* room is current. Where
  the map panel is missing or unavailable the pill falls back to exactly
  today's value.
- **A player who used hover to read a truncated node label loses that readout**
  → The full label is still the node's SVG `<title>` (pointer tooltip and
  accessible name) and the full map overlay draws the same lattice at
  `labelMax: 10`; the island's own truncation is unchanged by this change.
- **`--paper-500` at the island's smallest step is the dimmest text in the
  HUD** → It is the tier and size the island's header row already ships at,
  and it clears AA (4.98:1). If the figure proves illegible in review, the tier
  is one token change, and the requirement states a contrast floor rather than
  a token name.

## Migration Plan

None needed. The project is pre-release with **zero users**: no
backward-compatibility surface, no persisted client state (no preference, no
storage write), and no payload or protocol change. `LocalMap.vue`, the store's
location derivation, the Vitest suites, the browser assertions and the three
spec deltas land in one commit; rollback is reverting that commit.

## Open Questions

- Whether `webclient-minimap-05-edge-markers-replace-list`'s named edge markers
  are focusable. Either answer is safe here — the full-bleed button contains no
  descendants at all — but it is the reason D1 rejects `role="button"` on the
  root outright rather than "for now".
- Whether the server should eventually author a better
  `status.actor.location.label` for wilderness rooms (D5's first rejected
  alternative). If it does, the pill's preference order still resolves
  correctly and needs no change.
