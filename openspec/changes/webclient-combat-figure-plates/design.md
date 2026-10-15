# Design: Figure plates — conditions on demand, low-HP alarm, keyboard group

## Context

- The glance plate (`webclient-combat-formation` D4, `components/FigurePlate.vue`) shows the name, the HP stroke and
  the readout in a `full` (112×52px·S, three lines) or `compact` (72×36px·S, two lines) slot that the formation
  engine (`components/combat-formation.js`) returns. The engine keeps every head uncovered, keeps plates apart and
  never lets anything cover a plate; front-rank plates of a two-rank side stand on the floor line.
- The vitals dock's `ConditionChips.vue` already renders glyph-only severity icons with a tooltip, a `+N` overflow
  and the shared `conditionLabel`. `vitals.js` holds `LOW_HP_THRESHOLD = 0.25`, and `VitalsTrack.vue` shows the 危險
  marker.
- `webclient-combat-panel-v6` gives each participant `conditions` (`code`, `label`, `severity`, ≤ 8). These rows carry
  no `provenance`, `remaining_seconds` or `modifiers`.
- Text never renders below `--text-xs` (16px·S). With the name and the readout at line-height 1, a full plate's third
  line is 16px·S tall (52 − 2 − 17 − 17) and a compact plate's second line 17px·S.

## Decisions

### D1. Permanent vs on demand (decision-first)

The decision in a combat turn is "which action, on whom". The facts that change it are each figure's HP, whether it
is in danger, and whether it carries a condition worth acting on (cleanse, finish, protect).

| | Permanent (glance) | On demand (tooltip / group focus) | Why |
|---|---|---|---|
| Ally plate | name (full form), HP stroke, `current / max`, ≤ 3 condition glyphs + `+N`, 危險 at ≤ 25% | condition name | HP and danger pick heal/protect targets every turn; condition kinds read by shape; their names are reference-only |
| Foe plate | name (full form), HP stroke, `current / max`, condition glyphs, 危險 | condition name | the same reasons pick finish/focus targets |
| Controlled figure | — (the vitals dock is its plate) | — | one place for the player's own vitals |
| Session token (a1/e1) | only while two drawn names repeat | accessible name | unchanged from the formation |

### D2. Glyph row

- `ConditionChips` gains:
  - `cap` (default 6, the dock's existing visible cap);
  - `tabbable` (default `true`; `false` gives every icon `tabindex="-1"`, because the plate group manages focus);
  - `variant` (`dock` default | `plate`): the plate variant sizes the icons for the plate, names its test hooks
    `figure-plate__condition…` (so the dock's hooks stay unique), and replaces the dock's in-flow `+N` disclosure
    with a `+N` icon whose tooltip lists the hidden conditions (an in-flow disclosure would grow the plate out of its
    slot);
  - `fold` (plate variant only): no `+N` icon; the last visible glyph carries the hidden conditions in its tooltip
    and accessible name and shows a small drawn `+` mark (D5);
  - `closeSignal` (a counter; every change closes the open tooltip, D3).
- The glyph line has a box budget: four boxes on a full plate, two on a compact one; when the 危險 tag opens the line
  (D5) it keeps two (full) or one (compact). The conditions show most severe first (critical > harmful > warning >
  informational > beneficial, committed order within a severity). When they outnumber the boxes, the last box is
  `+N`; with a single box the `+N` folds into the glyph instead (`fold`).
- Geometry: each icon is a 24×24px·S hit box, bottom-aligned on the slot's lower edge, so it rises over the lower
  part of the readout line (which is not interactive) and never leaves the slot. Full: 3 glyphs + `+N` = 4 × 24 +
  3 × 2 gap = 102px·S inside the 106px·S content width. The glyph draws at `--text-xs`, line-height 1.
- The name (full line 1) and the stroke (line 2; at least 40px·S full, 30px·S compact) never share a line with
  glyphs. The plate's lines tighten to line-height 1 to give the glyph line its 16px·S.
- `lib/condition_label.js`'s `conditionSource` treats a missing `provenance` as no source, so participant rows reuse
  the shared label without a crash.

### D3. Tooltip

- Reuses `ConditionChips`' tooltip: `role="tooltip"` plus `aria-describedby`, `<Teleport to="body">` and
  `position: fixed` from the glyph's rect, because the plates layer is inside the stage.
- Placement: above the glyph by default. After it renders, the tooltip measures itself: it shifts left to stay 4px
  inside the viewport (the tick still points at the glyph), and opens below the glyph when it would cross the
  viewport's top. This applies to the dock's row too (it only ever moves a tip that would have been clipped).
- A tooltip lists one or more conditions: one for a glyph, the hidden ones for `+N`, the glyph's own plus the hidden
  ones for a folded glyph.
- AppClient bumps a `plateTooltipClose` counter when a round starts playing (`dispatch.beatLocked` turns true) and
  when the committed mode changes; plates pass it to `ConditionChips` as `closeSignal`. A window resize already
  closes an open tooltip; a replaced condition list (every commit) closes it too.
- Head rule: at rest no tooltip is open, so the formation's guarantees (no head and no plate covered) hold; a tooltip
  shows only while the pointer rests on, or focus holds, its glyph.
- `webclient-combat-stage-target-picking` adds the target-step trigger.

### D4. Keyboard group

- The `plates` anchor in `HudFrame.vue` is the group: while the formation stands it carries `role="group"`,
  `aria-label="戰場"` and `tabindex="0"`. The anchor moves after the bottom band in DOM order (its paint order is set
  by its explicit `z-index: 3`, unchanged), so Tab from `#action-dock` reaches it next.
- `components/plate-group.js` binds the anchor (pure DOM helpers; no Vue):
  - focusing the anchor forwards focus to the last focused plate or glyph still in the group, else the leftmost
    plate; while focus is inside, the anchor's own `tabindex` is `-1`, so Tab and Shift+Tab leave the group
    naturally, and it returns to `0` when focus leaves;
  - plates carry `tabindex="-1"`; stage order is left to right by the plate's slot centre (`data-stage-x`), ties by
    DOM order;
  - ArrowLeft/ArrowRight move to the previous/next plate (no wrap); ArrowDown moves from a plate to its first glyph
    and from a glyph to the next; ArrowUp moves back to the previous glyph, then to the plate; Home/End go to the
    first/last plate;
  - Escape: an open tooltip consumes the first press (`ConditionChips`); with none open, focus returns to
    `#action-dock`;
  - every key the group handles (arrows, Home, End, Escape, and Enter/Space on a plate) calls `preventDefault` and
    `stopPropagation`, so `bridge.js`'s document listener never routes it. Digits and other keys keep their global
    meaning.
- Each plate's `aria-label` appends 危險 when low and its conditions (`狀態：…`, the shared labels joined by `、`).

### D5. Low-HP alarm

`isLowPlateHp(current, maximum)` uses `LOW_HP_THRESHOLD` and the displayed value. When true:

- the readout's current value takes `--crit`;
- a `危險` tag (the vitals marker's style: seal border, crit text, `--text-xs` bold, ≈ 40px·S) opens the glyph line in
  both forms. Line 2 has no room beside a 40px·S stroke and a three-digit readout, and on line 1 it would crush the
  name to one character (reviewed in Storybook), so the name keeps its line;
- the line then keeps two boxes on a full plate (tag + 2 × 24 + gaps ≈ 94px·S of 112) and one on a compact plate,
  where more than one condition folds the `+N` into the glyph (D2 `fold`), because the tag, a glyph and `+N`
  (≈ 92px·S) exceed the 72px·S slot;
- the plate gains `data-low-hp="true"` for tests.

There is no pulse, unlike the vitals hp line: many plates pulsing would compete for attention.

## Risks / Trade-offs

- [Many tab stops] → avoided: the whole layer is one tab stop.
- [Tooltip over a head or a plate] → tooltips are on demand, close on every exit and never show at rest.
- [Hit boxes over the readout line] → the readout is not interactive; the boxes stay inside the slot.
- [DOM move of the plates anchor] → paint order rests on explicit z-indexes; a HudFrame test pins the order.
- [Keyboard collision with the stage target step] → `webclient-combat-stage-target-picking` moves focus out of the
  group to `#action-dock` when a step starts, so the step's arrow claim and the group never compete.

## Migration Plan

Pre-release; rollback by revert.

## Open Questions

None.
