# Proposal: Combat formation engine (pure geometry)

## Why

The user ruled that the combat command card stands at true dead centre with a clear gap. Both sides must be shown at
one shared figure scale, and every figure carries a plate that never collides with another. In combat only, the party
may leave its single row. Today's staging cannot meet this: the sides differ in scale, at most three foes stand, and
the rear foe stands within 31px of the centre at 1451x790. The real bounds are a party of 1–5 figures and up to 15
foes (the 16-participant presentation bound). This change builds the geometry that satisfies all of it as one pure,
testable function, before any component uses it.

## What Changes

- New `web/webclient-app/components/combat-formation.js`: `combatFormation(input)` returns the shared scale and every
  figure box, plate slot (full 112×40px·S or compact 72×30px·S, one or two staggered lines) and target-marker slot.
  It covers party 1–5 × foes 1–15, using one or two ranks per side.
- The geometry rules:
  - a fixed dead-centre gap of the card width (264px·S) plus a 16px·S gutter on each side;
  - one scale ladder from 0.90 down to a floor of 0.55;
  - all-full plates preferred before compact ones.
- A Vitest proves the invariants over the full matrix at 1451x790, 1600x900, 1920x1080 and 2560x1440, and pins the
  reference table.
- Nothing renders it yet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: adds "Combat formation geometry is one pure shared-scale function".

## Impact

- Code: one new pure module and one new Vitest file (`web/webclient-app/tests/core/combat_formation.test.js`).
- No component, server or protocol change.

## Batch: webclient combat stage

Final apply/archive order:

1. `webclient-combat-panel-v6`
2. `webclient-combat-formation-engine`
3. `webclient-combat-formation`
4. `webclient-combat-figure-plates`
5. `webclient-combat-defeated-foes`
6. `webclient-combat-command-card-centred`
7. `webclient-combat-stage-target-picking`
8. `webclient-combat-cross-side-confirm`

- depends-on: none
- Code conflicts: none with other changes (new files only); `webclient-combat-formation` consumes it.
