# Design: Figure plates — conditions on demand, low-HP alarm, keyboard group

## Context

- The glance plate (`webclient-combat-formation` D4) shows the name, the HP stroke and the readout in a `full`
  (112×40px·S) or `compact` (72×30px·S) slot.
- The vitals dock's `ConditionChips.vue` already renders glyph-only severity icons with a tooltip, a `+N` overflow
  and the shared `conditionLabel`. `vitals.js` holds `LOW_HP_THRESHOLD = 0.25`, and `VitalsTrack.vue` shows the 危險
  marker.
- `webclient-combat-panel-v6` gives each participant `conditions` (`code`, `label`, `severity`, ≤ 8).

## Decisions

### D1. Permanent vs on demand (decision-first)

The decision in a combat turn is "which action, on whom". The facts that change it are each figure's HP, whether it
is in danger, and whether it carries a condition worth acting on (cleanse, finish, protect).

| | Permanent (glance) | On demand (tooltip / group focus) | Why |
|---|---|---|---|
| Ally plate | name (full form), HP stroke, `current / max`, ≤ 3 condition glyphs + `+N`, 危險 at ≤ 25% | condition name, remaining time, modifiers | HP and danger pick heal/protect targets every turn; condition kinds read by shape; their prose is reference-only |
| Foe plate | name (full form), HP stroke, `current / max`, condition glyphs, 危險 | condition detail | the same reasons pick finish/focus targets; numbers were in the roster before, so nothing is lost |
| Controlled figure | — (the vitals dock is its plate) | — | one place for the player's own vitals; no duplicate |
| Session token (a1/e1) | — | accessible name | the digit shortcuts address frame rows, not tokens, so tokens add clutter only |

### D2. Glyph row

- `ConditionChips` gains `cap` (default: its existing visible cap) and `tabbable` (default `true`; `false` inside
  plates, where the group manages focus).
- The plate renders it with `cap = 3` (full) or `cap = 1` (compact), ordering conditions by severity
  (critical > harmful > warning > beneficial) for the compact form.
- The glyph row sits on the plate's name line, right-aligned. In the compact form it sits after the readout.
- Plate sizes are unchanged: a 22px·S glyph hit box fits the 40px·S full plate's top line and the 30px·S compact line.

### D3. Tooltip

- Reuses `ConditionChips`' tooltip: `role="tooltip"` plus `aria-describedby`, and `<Teleport to="body">` with
  `position: fixed` from the glyph's rect, because the plates layer is inside the transformed stage.
- AppClient bumps a `plateTooltipClose` counter on playback start, mode change and resize. Plates watch it and close.
- `webclient-combat-stage-target-picking` adds the target-step trigger.

### D4. Keyboard group

- `components/plate-group.js` implements a roving tabindex. The group element (`role="group"`, `aria-label="戰場"`,
  `tabindex="0"`) forwards focus to the last focused glyph, or to the first plate.
- Keys:
  - ArrowLeft/ArrowRight move between plates in stage order, the same order the formation returns;
  - ArrowUp/ArrowDown move between glyphs;
  - Escape returns focus to `#action-dock`;
  - Tab leaves naturally.
- Keydown handlers stop propagation for the keys they handle, so `bridge.js` never routes them to the dock.
- Each plate's `aria-label` (formation D4) appends its conditions.

### D5. Low-HP alarm

`isLowPlateHp(current, maximum)` uses `LOW_HP_THRESHOLD` and the displayed value. When true, the readout's current
value takes `--crit` and a `danger` tag (`危險`, the vitals marker's style) is added; the plate also gains
`data-low-hp="true"` for tests. There is no pulse, unlike the vitals hp line: many plates pulsing would compete for
attention.

## Risks / Trade-offs

- [Many tab stops] → avoided: the whole layer is one tab stop.
- [Tooltip over the card] → tooltips are on demand and close on Escape. They render above the card only while asked
  for.

## Migration Plan

Pre-release; rollback by revert.

## Open Questions

None.
