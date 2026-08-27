## Context

`DockMenu.vue`'s outlet-pane template (`webclient-hud-03-action-dock`, H3) has not been revisited since
it landed. Reproduced live at 1440x900 against a 4-exit room ("南大道"):

```html
<button class="dock-menu__outlet-tile dock-menu__outlet-tile--focused">
  <span class="dock-menu__outlet-glyph">→</span><b>east</b><small>冒險者公會外</small>
</button>
```

with `getComputedStyle` confirming the focused tile's `::before{content:"▶"}` renders in addition to the
`→` span, and the sibling `dock-detail` aside (`flex: 0 0 220px`) rendering beside the grid showing only
`"east"` again plus `"Enter → 開啟"`.

## Goals / Non-Goals

**Goals:**
- The outlet tile's primary, bold text is the destination's display name (the information a player
  actually needs), with the direction as a single leading glyph — never the direction rendered twice.
- Exactly one glyph-shaped element per tile, focused or not.
- The outlet pane's row grid receives the pane's full width; no companion side panel that adds no
  information beyond what the tile already shows.
- A disabled exit's visible marker and accessible reason stay exactly as reachable as they are today —
  removing the side panel must not silently remove the only surface that carried either one.

**Non-Goals:**
- No change to `exploration_menu.js`, the exit item shape (`key`, `label`, `direction`, `destination`,
  `enabled`, `disabled_reason`), or the router/keyboard geometry (`gridCols`) — that is
  `fix-webclient-hud-dock-outlet-grid-geometry`'s scope, not this change's.
- No change to the `nav` or `affordance` pane kinds, or their own `--focused::before` carets — this
  change's research confirmed those panes' decorative icon (`dock-menu__nav-icon`) does not currently
  render a visible glyph at all (the template's `<span v-if="glyphPath(row.item.kind)" ...></span>` has
  no background/mask bound to it), so there is no live "double glyph" symptom to fix there yet; that gap
  is a distinct, separate defect worth its own future change; conflating it here would widen this
  change's blast radius past the outlet pane it was scoped to fix.
- No change to `destinationLabel()`'s own resolution logic (matching against `local_map.nodes[]`) — only
  which field the template treats as primary vs. fallback.
- No change to the disabled-row contract's substance (the `（無法通行）` suffix, focusable-but-non-
  submitting, the server-authored reason stays reachable) — Decision 4 changes only *where* the
  accessible reason is exposed (on the tile itself instead of a now-removed side panel), not whether it
  is exposed or what it says.

## Decisions

**1. Bold text = destination name when known; the exit's own label is the bold text only when there is
no glyph to carry the direction, or as the fallback when the destination name is unknown.**
Concretely, replace:
```html
<b>{{ row.item.label }}</b>
<small v-if="destinationLabel(row.item)">{{ destinationLabel(row.item) }}</small>
```
with a single bold field whose content is
```html
<b>{{ (row.item.enabled && directionGlyph(row.item.direction) && destinationLabel(row.item)) || row.item.label }}</b>
```
(the leading glyph span is unchanged, but now rendered through the new
`directionGlyph()` helper — a shared client-side table that resolves only
canonical direction strings to a glyph; an unknown string (a named door or
dynamic wilderness gate) resolves to no glyph and keeps the label). For a canonical exit with a known destination, the bold text
becomes the destination's display name (e.g. `北岸大道`) instead of the raw direction word — matching
both the redesign's own tiles and the `webclient-contextual-hud` requirement's "leading glyph together
with the destination's display name" wording, which names exactly two pieces of information. For a
canonical exit whose destination is not yet in the committed local-map lattice, the bold text falls back
to the exit's own label (`row.item.label`, e.g. `"east"`) so the tile is never blank — this is the same
"glyph alone with no destination line" case the existing "An unknown destination renders no destination
line" scenario already covers, just re-expressed as a single field instead of an empty `<small>` plus a
lone `<b>`. For a non-canonical exit (`row.item.direction` is `null`, e.g. a named door), `destinationLabel()`
already returns `null` unconditionally in that branch (it only resolves against `item.destination`, which
`moveItems()` only ever sets from the server's exit row regardless of canonicality — non-canonical named
doors do carry a `destination` field too, so this is verified against `exploration_menu.js:249-286`: `destination: row.destination || null` is set for every move row, not only canonical ones). This means a
named door **with** a known destination would, under the simple `destinationLabel(row.item) || row.item.label`
expression, show the destination's name instead of the door's own name — which would silently violate the
existing "A non-canonical exit keeps its own name" requirement (a scenario this change must not break).
The template therefore keeps the two branches distinct — and, per the rubber-duck review's blocking
finding below, adds a third condition: **a disabled row never substitutes the destination name**, because
`moveItems()` (`exploration_menu.js:257`) bakes the only generic disabled marker directly into
`row.item.label` itself (`row.label + (row.enabled ? "" : "（無法通行）")`) — client-side baking, not a
server field. If a disabled canonical exit's destination happens to already be in the committed local-map
lattice (a normal case — e.g. a temporarily-blocked exit to an already-visited room), substituting the
bare destination name would silently drop the only visible "（無法通行）" marker this row has, with
nothing else on the tile indicating it cannot be used. The final expression:
```html
<b>{{ (row.item.enabled && directionGlyph(row.item.direction) && destinationLabel(row.item)) || row.item.label }}</b>
```
— the destination name is used only when the row is enabled, its direction resolves to a known glyph, and
the destination is known; every other case (disabled, non-canonical, or unknown destination) falls back to
`row.item.label`, which already carries the `（無法通行）` suffix when disabled.
The glyph table is a null-prototype object (`Object.assign(Object.create(null), {...})`): an
out-of-table direction such as `"constructor"` or `"toString"` must resolve to no glyph (and thus keep the
row's own label), never to an inherited `Object.prototype` property.
Alternative considered: keep the raw label as `<b>` and only reorder which is visually larger via CSS
(swap font sizes between `<b>` and `<small>`) without changing which field holds which role. Rejected —
that still renders the direction word twice (once as glyph, once as enlarged text) for every canonical
exit; the actual defect is the redundant field, not merely its font size.

**2. Delete `.dock-menu__outlet-tile--focused::before` entirely; do not replace it with a different
non-color indicator.**
The tile's direction glyph (`.dock-menu__outlet-glyph`) already renders unconditionally, independent of
focus state, so it cannot itself serve as "the" focus indicator — but the focused state does not rely on
color alone either: `.dock-menu__outlet-tile--focused` already changes `background`, `border-color`,
*and* `color` together (a bundled fill + border-shape change, not a single hue swap), which is the same
category of non-color-adjacent signal (a full component state swap, not "red text on a beige tile")
`DockMenuItem.vue`'s bare-text cells use their `▶` caret to produce. Given `docs/design/elosern-redesign/index.html`'s
own `.tab.on`/`.o` states rely on exactly this same background+border treatment with no extra glyph, and
this codebase's `webclient-contextual-hud` "never color alone" convention is about not relying on **hue**
in isolation (a colorblind-safe concern), a background+border fill change together with a border-width or
shape change already satisfies that without a redundant icon. No new CSS is added in its place.
Alternative considered: keep the caret but reposition it (e.g. as a small corner badge instead of
inline-before) so it does not visually collide with the direction glyph. Rejected as unnecessary
complexity — deleting the rule is a net simplification with no loss of accessible signal, since the
background/border state change already exists and is not itself in question.

**3. Suppress `dock-detail` for the outlet pane kind by extending its existing `v-if`, computed from
`DockMenu.vue`'s own internal `paneKind`, not a new prop.**
`paneKind` is already a local `computed()` in `DockMenu.vue` (`classifyPane({ items: props.items })`);
the aside's guard becomes
`v-if="paneKind !== 'outlet' && ((props.showDetail && focusedRow && !props.hideGenericDetail) || props.detailMessage)"`
(per the rubber-duck review's blocking finding: the outlet exclusion wraps the *entire* guard, so a
`detailMessage` alone can no longer render the aside on the outlet pane).
This mirrors the existing `hideGenericDetail` prop's *intent* (suppress the generic aside when a more
specific or no-aside-needed surface applies) without requiring `AppClient.vue` (the caller) to know about
pane-kind internals it has no other reason to reach into — `hideGenericDetail` stays reserved for the
external combat/`SkillDetailPane` case it already serves.
Alternative considered: pass a new `hide-generic-detail-for-outlet` (or similar) prop from
`AppClient.vue`, computed there from the same `classifyPane` logic `DockMenu.vue` already runs
internally. Rejected — it would duplicate the pane-kind classification in two places (`AppClient.vue`
would need its own `classifyPane` call to decide when to pass the prop) for no benefit, since
`DockMenu.vue` already has the answer computed locally.

**4. Move the disabled row's server-authored explanation onto the tile itself, so removing the generic
aside (Decision 3) does not also remove the outlet pane's only carrier of `disabled_reason.message`.**
Before this change, `dock-detail`'s `else` branch (`DockMenu.vue:387-392`) is the *only* place any pane
renders `focusedRow.reason` — the specific server-authored explanation (e.g. `"出口被阻擋。"`), as
opposed to the generic `（無法通行）` suffix already baked into the label. Removing the aside for the
outlet pane (Decision 3) without replacing this would violate this capability's own unmodified "A
disabled row in any pane stays readable" scenario (`... exposes ... its server-authored explanation`).
The fix mirrors `DockMenuItem.vue`'s existing accessible-reason pattern exactly: the outlet tile gains
`:aria-describedby="!row.item.enabled && row.reason ? row.rowId + '-reason' : null"` and a
`visually-hidden` `<span :id="row.rowId + '-reason'">{{ row.reason }}</span>` rendered only when disabled
and a reason exists (`row.reason` is already computed by `DockMenu.vue`'s `rows` computed via
`disabledReasonText(item)` — no new data plumbing). This keeps the explanation reachable by assistive
technology without reintroducing a visible side panel or the width it consumed.
Alternative considered: render the reason visibly on the tile (a `<small>`-style reason line, mirroring
`.dock-menu__aff-reason`). Rejected for this change — the outlet tile's compact ~150px width has no
comfortable room for a third text line without either truncating the destination name or growing the
tile past the reference's proportions; the accessible-only note preserves the same guarantee
(`webclient-contextual-hud`'s wording is "exposes ... its accessible disabled state and its
server-authored explanation," not "renders it visibly") without reopening the width problem this change
exists to fix. A future change is free to add a visible affordance if product wants one.

## Risks / Trade-offs

- **[Risk] Some existing test may assert the outlet tile's exact rendered text (e.g. `"east"` as the
  `<b>` content) or the `::before` caret's presence.** → `grep -rn` `dock-menu__outlet` and the literal
  strings across `web/webclient-app/tests/` and `web/tests/browser/` before landing (task-tracked); this
  change's research pass found no existing outlet-tile-specific test at all (a pre-existing coverage
  gap this change also closes with a new test).
- **[Risk] A future exit whose server label already IS its destination name (a coincidence, not
  guaranteed by contract) could look odd once duplicated fields collapse to one.** → Not applicable:
  collapsing two redundant fields into one only removes duplication, it never invents or hides real
  data; a coincidental label/destination match today already renders as `"east" / "east"` in the current
  two-field layout, which is equally redundant — this change makes that case render once, not worse.
- **[Trade-off] The bold-text ternary is less readable inline than a single expression.** → Accepted: it
  is guarded by a code comment explaining the disabled-row and non-canonical-exit exceptions (Decision
  1), and is covered by a unit test per branch (canonical+known destination+enabled,
  canonical+known destination+disabled, canonical+unknown destination, non-canonical).
- **[Risk, rubber-duck-flagged] Combining the destination-name swap (Decision 1) with removing the
  generic aside (Decision 3) would, without Decision 4, silently erase both the visible `（無法通行）`
  marker (whenever a disabled canonical exit's destination is already known) and the only surface that
  rendered the server's specific `disabled_reason.message`, leaving a disabled tile with zero indication
  it cannot be used.** → Fixed by making the bold-text expression enabled-aware (Decision 1's final form)
  and by moving the accessible reason onto the tile itself (Decision 4) before removing the aside. No
  existing test exercised a disabled outlet row (`test_browser_contextual_hud.py`'s `_move_row()` helper
  already supports `enabled=False` but no call site ever passes it, and `dock_menu_panes.test.js`'s
  outlet fixture has no disabled row) — tasks 1.2 and 3.2 add that coverage.
- **[Non-blocking, rubber-duck-flagged] `test_browser_contextual_hud.py:1017` asserts
  `assertIn("南", first_text, ...)` against a tile whose destination label is `"南大道"` — a substring
  match that will keep passing under the new single-field template by coincidence (the old raw-label
  assertion and the new destination-name text both happen to contain "南"), so it stops actually
  distinguishing the two layouts.** → Task 4.1 tightens this to a whole-token check (or an explicit
  absence check for the raw exit label) so a future regression back to the two-field layout would be
  caught.

## Migration Plan

Not applicable — no data migration, no feature flag. Source-level template/style edit to one file
(`DockMenu.vue`), landed and reviewed as one change.

## Open Questions

None — every decision is settled by the existing `webclient-contextual-hud` requirement text, the
existing `hideGenericDetail`/hidden-aside precedent already in this same file, or a verified fact about
`exploration_menu.js`'s item shape.
