# Proposal: Figure plates — conditions on demand, low-HP alarm, keyboard group

## Why

`webclient-combat-formation` replaces the participant roster with a glance plate on each figure (name, HP stroke,
readout). The roster also listed participant states, and the user asked the plates to carry conditions as glyph-only
icons with details on demand, a text-plus-colour low-HP alarm, and full keyboard reach. All of this follows
`tmp/core-panel-design-notes.md` and the game-ui-design decision-first rule. The data comes from
`webclient-combat-panel-v6` (participant `conditions`).

## What Changes

- **Condition glyphs on each plate:**
  - Glyphs reuse the vitals dock's severity shapes (`ConditionChips` gains `cap`, `tabbable`, a `plate` variant, a
    `fold` and a close signal).
  - `full` plates show up to 3 glyphs plus `+N`; `compact` plates show the most severe glyph plus `+N` (folded into the
    glyph when the 危險 tag needs the room).
  - The accessible names use the shared condition label.
- **Tooltip on demand**, with the notes' mechanics, kept inside the viewport (shift left, flip below). It closes on
  leave, blur, Escape, resize/scroll, the data disappearing, playback starting and leaving combat, so none shows at
  rest and the formation's head and plate rules hold.
- **Low-HP alarm:** at 25% HP or below (the vitals `LOW_HP_THRESHOLD`), the current value turns the critical hue and a
  `危險` tag joins the plate (after the name on a full plate, on the glyph line of a compact one).
- **One keyboard group:** the plates layer is a single tab stop after the action dock (戰場; the anchor moves after the
  band in DOM order). Left/Right move between plates, Up/Down between a plate and its glyphs, Escape/Tab leave, and
  the handled keys are consumed before the router.
- Storybook stories for every plate state (full HP, damaged, low-HP alarm, conditions, overflow, long names,
  compact) and the matrix corners with conditions, plus focused tests and one browser method.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: adds "Figure plates show conditions at a glance and their details on demand" and
  modifies "Combat figures carry glance plates" (the glyph line is filled; the layer's one keyboard entry is the
  group).

## Impact

- Code (`web/webclient-app/`): `components/FigurePlate.vue` and `figure-plate.js` (glyph row, alarm, accessible
  name), `components/ConditionChips.vue` (props, tooltip placement), `lib/condition_label.js` (no provenance → no
  source), new `components/plate-group.js` (roving focus and key handling), `AppClient.vue` (passes conditions;
  tooltip closure hooks), `components/HudFrame.vue` (the plates anchor is the group, after the band in DOM order).
- Tests: Vitest for plates/ConditionChips/plate-group/HudFrame, one new browser method registered in
  `.github/browser-shards.json`, and the existing plates-layer focus assertions updated.
- Stories: `Core/FigurePlate` states, `Core/AppShell` corners with conditions; the manifest is unchanged (the
  `Core/FigurePlate` entry was added by `webclient-combat-formation`).

## Batch: webclient combat stage

- depends-on: webclient-combat-panel-v6
- depends-on: webclient-combat-formation
- Code conflicts: `FigurePlate.vue` and `AppClient.vue` with `webclient-combat-defeated-foes` (down/defeated plate
  text) and `webclient-combat-stage-target-picking` (markers on plates); apply in batch order.
