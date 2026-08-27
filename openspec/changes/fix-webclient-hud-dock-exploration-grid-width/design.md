## Context

`DockMenu.vue`'s `paneGridStyle` computed (`webclient-hud-03-action-dock`, H3):

```js
const paneGridStyle = computed(
  () =>
    props.gridCols
      ? { 'grid-template-columns': "repeat(" + String(props.gridCols) + ", 1fr)" }
      : {},
);
```

is bound via `:style="paneGridStyle"` on nine different pane-kind containers (`outlet`, `nav`,
`affordance`, `cards`, `skills`, `targets`, `scales`, `confirm`, `plain`). It exists so the row region's
*rendered* geometry always matches whatever `gridCols` the router is using for arrow-key math (task 2.7's
comment: "the root is a single-row tab bar: the column count equals the item count... so arrow-key
geometry matches the rendered order" — the same principle `exploration_menu.js` applies to `move`/`look`/
`interact`/`wait` with a fixed `gridCols: 2`).

Verified live (`agent-browser`, 1440x900, a 4-exit room): `.dock-menu__outlet`'s own class rule
(`grid-template-columns: repeat(auto-fill, minmax(150px, 1fr))`) is correct and, in isolation, produces 5
narrow columns for the same container width. The inline style from `paneGridStyle`
(`repeat(2, 1fr)`) wins (inline beats class specificity) and is the actual applied rule
(`getComputedStyle` confirms `"450px 450px"`). Forcing the *identical* declared value via
`el.style.setProperty(..., 'important')` reproduces the correct 5-column layout — proving the class rule
was never the problem; only the *track-sizing function* (`1fr`, which stretches) in the inline override
is.

**Correction from this change's own rubber-duck review, verified before finalizing:** the first draft of
this change assumed `wait` (the fourth exploration sub-menu with `gridCols: 2`) suffered the same defect
by pane-kind analogy. That assumption was wrong. `wait`'s items classify to `plain`
(`dock-panes.js:classifyPane()`), rendered through `.dock-menu__plain` — a class with **zero CSS rules
defining `display: grid`** anywhere in `DockMenu.vue` (confirmed by `grep`). `getComputedStyle` against
the live element confirms `display: "block"` even though the inline `grid-template-columns:
repeat(2, 1fr)` is still present in the `style` attribute — the property is simply inert on a non-grid
box. Live screenshot confirms the 等待/休息 frame already renders six correctly-sized, compact buttons
per row today. `wait` is therefore removed from this change's scope entirely: there is nothing to fix
there, and touching it would be a no-op at best.

This correction also surfaces a second, related fact worth recording precisely (see Decision 2): several
other menus outside exploration — `service_menu.js`'s `guild`/`board`/`quests`/`shop`/`stock`/`sell`/
`inventory` and `creation_menu.js`'s `presets` — also set `gridCols: 2` and also classify to `plain`.
Because `plain` is not a grid container, `paneGridStyle`'s output is equally inert for all of them today.
This change does not touch `plain` at all, so none of those menus is affected by it — but it means the
original "no other menu resolves to these pane kinds with a non-null gridCols" framing was imprecise; the
corrected, narrower, and verified claim is in Decision 2.

## Goals / Non-Goals

**Goals:**
- The exploration move/look/interact frames render content-sized tiles/rows, not tiles stretched to half
  (or a third, etc.) of the dock's width.
- Zero change to keyboard navigation: the same column count, the same item-to-cell mapping, every
  existing `ArrowRight`/`ArrowDown` test assertion for these menus keeps passing unmodified.
- No tile or row can grow unboundedly from `max-content` sizing on a long server-authored string — a
  fixed `max-width` safety net catches that case.

**Non-Goals:**
- No change to `exploration_menu.js`'s `gridCols: 2` values, `keyboard_router.js`'s row/col math, or the
  store's router wiring — the keyboard geometry is intentional, tested behavior, not a defect.
- No change to the `wait` sub-menu or the `plain` pane kind — verified live to already be correctly laid
  out; `.dock-menu__plain` has no `display: grid` rule, so `paneGridStyle`'s output has no visual effect
  on it. This also means the several other `plain`-classified, `gridCols: 2` menus outside exploration
  (`service_menu.js`'s `guild`/`board`/`quests`/`shop`/`stock`/`sell`/`inventory`, `creation_menu.js`'s
  `presets`) are unaffected by construction, not merely by omission.
- No change to `affordance`/`cards`/`skills`/`targets`/`scales`/`confirm` pane kinds' `paneGridStyle`
  behavior — no defect was found or reported there; combat's fixed-size tokens/cards already have their
  own width controls (`.tok{width:38px}`, `OptionCard.vue`'s `max-width:16rem`) that this change does
  not touch.
- No change to the outlet-tile's internal content/markup (that is
  `fix-webclient-hud-dock-outlet-tile-presentation`'s scope, a separate change).

## Decisions

**1. Change only the track-sizing function (`1fr` → `max-content`) for the `outlet`/`nav` pane kinds;
leave the column-count mechanism and every other pane kind — including `plain` — untouched.**
```js
const paneGridStyle = computed(() => {
  if (!props.gridCols) {
    return {};
  }
  const sizeFn = ["outlet", "nav"].includes(paneKind.value) ? "max-content" : "1fr";
  return { "grid-template-columns": `repeat(${props.gridCols}, ${sizeFn})` };
});
```
`max-content` sizes each grid track to the largest max-content contribution of the items placed in it —
i.e. each tile/row takes only the width its own text/icon needs, exactly like `width: fit-content` would.
The grid's own auto-placement algorithm (which item lands in which row/column) is governed purely by the
*count* of tracks (`repeat(2, ...)`), never by their size function, so switching `1fr` → `max-content`
cannot change which item ends up in which cell — the exact property `keyboard_router.js`'s row/col math
depends on staying stable. `paneKind` is already a local `computed()` in this file (used by the template's
`v-if`/`v-else-if` chain), so no new state or prop is introduced. `plain` is deliberately excluded from
`sizeFn`'s allowlist — it is not a grid container (see Context's correction above), so including it would
be a harmless but misleading no-op; excluding it keeps the code honest about what it actually affects.
Alternative considered: remove the inline `grid-template-columns` override entirely for these two pane
kinds, falling back to each one's own CSS class rule (`repeat(auto-fill, minmax(150px, 1fr))` etc.).
Rejected — CSS Grid's `auto-fill` track *count* is resized live by the browser based on available width
(that is its whole purpose), so at different rendered widths (e.g. between the two supported viewports,
or if a sidebar's presence changes available width) the number of visual columns would no longer
reliably be 2, breaking the assumption `keyboard_router.js`'s fixed `gridCols: 2` depends on for its
row/col math to stay meaningful. Keeping `repeat(2, ...)` (a fixed count) but changing only the *sizing
function* preserves the fixed-count guarantee the keyboard model requires while still fixing the width.
Alternative considered: cap the track size with `minmax(150px, 260px)` (an explicit upper bound) instead
of `max-content`. Rejected as an arbitrary magic number with no basis in either affected pane's actual
content — `max-content` is self-adjusting per pane and per tile without needing a hand-picked number
that could look wrong for a longer or shorter label than whatever content happened to be measured during
design; the unbounded-growth risk this raises is instead addressed directly on the tile (Decision 3).

**2. Scope the `sizeFn` allowlist to exactly `["outlet", "nav"]` — corrected and re-verified after this
change's own rubber-duck review found the first draft's blast-radius claim false.**
`move` → `outlet` (its rows carry `direction`/`exit-` keys) and `look`/`interact` → `nav` (look rows
carry `explore.look`; interact rows carry `navigation`+`target-` surfaces) are both real `display: grid`
containers whose inline override was doing visible, wrong work — these are the only two pane kinds this
change touches. The first draft additionally listed `plain` (`wait`'s pane kind) and, based on that
inclusion, claimed "no other menu in the app currently resolves to these pane kinds with a non-null
`gridCols` except these four exploration sub-menus." A direct `grep -n "gridCols"` across
`web/static/webclient/js/elosern/*.js` disproves that: `service_menu.js` sets `gridCols: 2` for
`guild`/`board`/`quests`/`shop`/`stock`/`sell`/`inventory`, and `creation_menu.js` sets `gridCols: 2` for
`presets` — all of which also classify to `plain` by the same elimination logic as `wait`. Because this
revision drops `plain` from `sizeFn`'s allowlist entirely (Decision 1), none of those other menus is
touched by this change regardless — the corrected scope is exactly `outlet` and `nav`, and no other pane
kind in the codebase today resolves to either of those two kinds with a non-null `gridCols` except
`move`/`look`/`interact`.

**3. Add a `max-width` safety cap on the tile/row itself (`.dock-menu__outlet-tile`,
`.dock-menu__nav-row`), not on the grid track, to bound `max-content`'s otherwise-unbounded growth.**
Unlike the rejected `minmax(150px, 260px)` track-level cap (Decision 1), which would apply one arbitrary
number to *both* pane kinds' tracks regardless of their very different content shapes, a per-selector
`max-width` is scoped to each pane's own real content: outlet tiles hold a glyph plus a destination name
(`destinationLabel()`, sourced from `local_map.nodes[].label`); nav rows hold an icon, a name, and an
optional sub-line (`row.item.kind` or `affordanceLabels.join("・")`) — both server-authored strings with
no length contract today. Without a cap, an unusually long one (e.g. several joined affordance labels)
could size a `max-content` track wider than the pane's available width, overflowing past the dock's edge
or overlapping the adjacent `dock-detail` aside (still present for the `nav` pane — the sibling
`fix-webclient-hud-dock-outlet-tile-presentation` change removes it only for `outlet`). `max-width: 220px`
on `.dock-menu__outlet-tile` (matching its own class's existing `minmax(150px, ...)` floor with headroom)
and `max-width: 320px` on `.dock-menu__nav-row` (wider, since it carries an icon plus two lines of text)
each pair with `overflow-wrap: break-word` so a string that hits the cap wraps onto a second line inside
the tile rather than being clipped or pushing the layout.
Alternative considered: no cap at all, accepting `max-content`'s unbounded growth. Rejected per this
change's own rubber-duck review — untested against a long-label case, and a plausible regression
(reproducing a different, worse width defect than the one being fixed) that costs almost nothing to
guard against.

## Risks / Trade-offs

- **[Risk] A future menu could resolve to `outlet`/`nav` with a `gridCols` value where `max-content`
  sizing is undesirable (e.g. a genuinely tabular layout wanting equal-width columns).** → Low
  likelihood — no such case exists today (verified: only `move`/`look`/`interact` feed a non-null
  `gridCols` into these two pane kinds), and if one is added later its own change can extend or adjust
  this branch; this change does not need to anticipate it.
- **[Risk] Some existing test might assert a specific rendered pixel width for one of these tiles/rows.**
  → `grep -rn` confirmed no existing test asserts `getBoundingClientRect`/bounding-box width for any
  `dock-menu__outlet`/`dock-menu__nav`/`dock-menu-item` element; only text content and `data-item-key`
  presence are asserted today.
- **[Risk, rubber-duck-flagged and fixed] `max-content` has no upper bound, unlike the reference's
  `minmax(150px, 1fr)` + `auto-fill`; an unusually long destination name or affordance-label list could
  size a tile/row wider than the pane, overflowing past the dock's edge or into the still-present
  `dock-detail` aside on the `nav` pane.** → Fixed by Decision 3's per-selector `max-width` cap plus
  `overflow-wrap: break-word`; tested with a long-label fixture (task 1.3), not just the short 4-exit
  case this change was originally reproduced against.
- **[Risk, rubber-duck-flagged and fixed] The first draft incorrectly generalized the defect to `wait`
  (the `plain` pane kind) and, on that same incorrect basis, claimed no other menu in the codebase shared
  the affected pane kinds with a non-null `gridCols`.** → Both corrected: `wait` is removed from scope
  (verified live to already be correctly laid out — `.dock-menu__plain` is not a grid container), and
  Decision 2 records the direct `grep`-verified fact that several other `plain`-classified menus
  (`service_menu.js`, `creation_menu.js`) also set `gridCols: 2`, all equally unaffected by this change
  because `plain` was dropped from scope entirely rather than assumed safe by analogy.
- **[Trade-off] `max-content` leaves visible empty space to the right of the two tiles/rows on wider
  rooms with short content.** → Accepted and intended: the alternative (stretching) is the exact defect
  being fixed; empty space reading as "this row has nothing more to show" is the same trade-off the
  reference's own `auto-fill` grids make when an exit list is short.

## Migration Plan

Not applicable — no data migration, no feature flag. A computed-function edit plus two scoped CSS rules
in one file, landed and reviewed as one change.

## Open Questions

None — the column-count/track-size independence is a verified property of CSS Grid's placement
algorithm, the pane-kind scoping is verified by direct enumeration against `exploration_menu.js`,
`service_menu.js`, `creation_menu.js`, and `dock-panes.js`, and the `wait`/`plain` exclusion is verified
against the live rendered `display` computed style, not assumed by analogy.
