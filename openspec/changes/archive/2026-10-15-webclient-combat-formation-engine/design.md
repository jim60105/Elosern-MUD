# Design: Combat formation engine

## Context

- **Party cap.** `world/rules/party.py` has `PARTY_MAX_COMPANIONS = 4`; the client caps the line-up at
  `COMPANION_LINEUP_MAX = 5` (`components/companion-lineup.js`); PartyDrawer shows `N / 4`. So a combat party is 1–5
  figures: 0–4 companions plus the controlled figure.
- **Foe maximum.** No combat rule caps a session's `enemy_ids`: an AREA opener can engage every co-located hostile
  monster. The only bound is the presenter's `MAX_PARTICIPANTS = 16` (`world/rules/combat_view.py`; a larger roster
  makes the panel unavailable). So foes are at most 15 (with a solo player) and 11 with a full party. The client
  stands at most three today (`FOE_LINEUP_MAX = 3`).
- **Today's staging.** Companions stand at full size, overlapping and shifted toward the centre. Foes stand
  depth-staged at 100% / 90–78% / 80–70–61% of the player's height. The two sides differ in scale, and with three foes
  the rear foe stands 31px from the stage centre at 1451x790, so a dead-centre command card cannot avoid figures.
- **User decisions.**
  - The command card stands at true dead centre with a clear gap.
  - In combat only, the party may leave the single row. Exploration and dialogue keep today's layout.
  - Both sides always share one figure scale.
  - Plates sit with each figure and must never collide.

## Goals / Non-Goals

**Goals:** one pure, DOM-free function that returns every combat figure box, plate slot and marker slot for the full
matrix (party 1–5 × foes 1–(16 − party)) at the supported viewports, with a guaranteed dead-centre gap and one shared scale;
plus a Vitest that proves the invariants over the matrix.

**Non-Goals:** applying it to the stage (`webclient-combat-formation`); plate content (`webclient-combat-figure-plates`).

## Decisions

### D1. Coordinates

- Stage-pixel coordinates. C = stage width / 2. Card width `Wc = 264px·S` (fixed; see
  `webclient-combat-command-card-centred`). Gutter g = 16px·S.
- Zones:
  - Party: from `16px·S` to `C − Wc/2 − g` (577.5 at 1451x790).
  - Foes: from `C + Wc/2 + g` to `width − 16px·S` (873.5–1435 at 1451x790).
  - Each zone is 561.5px at 1451x790 and 618.9px at 1600x900.
- In combat the `map` anchor (the place card and the former participant frame) is not rendered
  (`webclient-combat-formation` D2), so the right zone reaches the gutter. The prototype showed that keeping the place
  card makes two-rank foe formations impossible (plates collide with it).

### D2. The formation

- **Scale ladder:** 0.90, 0.84, 0.78, 0.72, 0.66, 0.60, 0.55, 0.50. The floor 0.50 keeps a figure 245px tall at
  1451x790 and 279px at 1600x900 (the plates have fixed sizes, so they stay readable at any scale).
- **Per side:** one rank if it fits, else two ranks:
  - the front rank has `ceil(n/2)` figures and the back rank `floor(n/2)`;
  - the back rank stands `0.27 × actor-h` up-stage, at the same scale, offset by half a step so its figures show
    between the front ones.
- **Spacing:** step = `min(0.62 × w, (zone − w) / (count − 1 + backShift))`. The group's outer edge sits at the
  side's home inset (6vw) when it fits, and is otherwise pushed toward the outer gutter, never into the gap.
- **Plate slots:** centred over each figure, bottom edge 4px·S above the figure box top.
  - `full` slots are 112×52px·S. If one line would make neighbours closer than the slot width, alternate figures
    use a second line raised by slot height + 4px·S.
  - `compact` slots are 72×36px·S, used only when full ones cannot fit at any ladder scale.
- **Marker slot:** 24px·S above the plate slot (a 24px·S pointer target) (the target arrow of `webclient-combat-stage-target-picking`).
- **Policy:** at each ladder scale a side takes one rank if it fits, else two ranks if they fit (so a second rank is
  always tried before the scale shrinks further); the first scale where both sides fit with all-`full` slots wins,
  else the first with `compact` slots. Vertical headroom decides most cases: the plate stack and the marker must stay
  under the top band, which is why a back rank (lifted 0.27·actor-h) only fits at small scales. If nothing fits at
  the floor (an unsupported stage), the function returns the floor two-rank compact formation with `fits: false`.

### D3. Invariants (Vitest over the matrix)

The test covers party 1–5 × foes 1–(16 − party) × {1451x790, 1600x900, 1920x1080, 2560x1440} with the reference vitals dock
(25vw × 92px·S on the band). For every case:

- `fits` is true, with scale ≥ 0.50.
- Every figure box has the same height on both sides.
- The gap `[C − Wc/2 − g, C + Wc/2 + g]` is free of all boxes and slots.
- Plate slots are pairwise ≥ 2px·S apart.
- Plate and 24px·S marker slots stay ≥ 8px·S below the top band.
- No plate slot touches the vitals dock, and the dock covers ≤ 40% of any party box.
- Everything stays inside the stage gutters.

Cells beyond the 16-participant bound are not part of the matrix.

### D4. Reference table (planning prototype; the spec's anchors are normative, the rest is pinned by the Vitest)

Each cell gives the shared scale, the plate form (F full / C compact) and the foe rank count (the party always fits
in one rank). Foes run to 16 minus the party size.

| 1451x790 | foes 1–3 | 4–6 | 7 | 8–14 | 15 |
|---|---|---|---|---|---|
| party 1–3 figures | 0.84 F 1 | 0.72 F 1 | 0.60 F 1 | 0.50 F 2 | 0.55 C 2 (party 1 only) |
| party 4–5 figures | 0.72 F 1 | 0.72 F 1 | 0.60 F 1 | 0.50 F 2 | — |

| 1600x900 and 1920x1080 | foes 1–3 | 4–6 | 7 | 8–14 | 15 |
|---|---|---|---|---|---|
| party 1–3 figures | 0.84 F 1 | 0.78 F 1 | 0.60 F 1 | 0.50 F 2 | 0.55 C 2 (party 1 only) |
| party 4–5 figures | 0.78 F 1 | 0.78 F 1 | 0.60 F 1 | 0.50 F 2 | — |

At 2560x1440: 0.90 for up to 4 foes, 0.84 for 5–7, 0.78 for 8, 0.66 for 9, then 0.55 with two ranks (a five-figure
party caps at 0.84).

The 1451x790 fifteen-foe cell was 0.50 C 2 in the planning prototype. The explicit fit rule and policy of D2 give
0.55 C 2 there: with compact slots the two staggered back-rank lines and the marker clear the top band by 8.4px at
0.55 (front rank 8, step 50.9px, so twice the step clears the 76px compact width). No reading of the rule reproduces
the prototype's 0.50 there while keeping its 0.55 at 1600x900 and its 0.50 full cells for 8–14 foes, so the rule
decides and the cell and the spec anchor follow it.

The jump from one rank at 0.60 to two ranks at 0.50 is forced by headroom: a back rank lifted 0.27·actor-h with
52px·S plates and a 24px·S marker only fits under the top band at 0.50 at 1451x790.

### D5. Module

- `web/webclient-app/components/combat-formation.js` exports `combatFormation(input)` and the constants
  (`SCALE_LADDER`, `SCALE_FLOOR`, `CARD_WIDTH`, slot sizes, `BACK_RANK_LIFT`, `RANK_STEP`).
- It reads only its input object (stage width and height, S, band top, `actor-h`, top-band bottom, vitals box, counts).

## Risks / Trade-offs

- [Smaller figures than today in big fights] → the floor keeps figures ≥ 245px tall at the reference viewport, and
  two ranks are used before any further shrink.
- [A marker slot overlaps a neighbour's raised plate] → with two staggered lines, a lower-line figure's 24px·S marker
  slot sits beside the raised plates of its neighbours and overlaps them horizontally whenever the step is less than
  half the slot width plus 12px·S (every 8–14 foe case at 1451x790). The invariants do not forbid it, since forbidding it
  would leave no full-slot formation for eight or more foes; `webclient-combat-stage-target-picking` must draw the
  marker above the plates or within this slot so it stays visible.
- [Front-rank plates over back-rank faces] → in a two-rank formation the front rank's plate lines lie across the
  back rank's upper bodies (at 1451x790 and 0.50 the front plates span y≈213–321 while the back figures start at
  y≈193). The invariants allow it; `webclient-combat-formation` should give the plates' ground enough feathering that
  the back-rank faces still read.
- [The prototype's numbers drift in the real module] → the invariants are normative; the pinned table is updated
  deliberately in the same commit.

## Migration Plan

Pure addition; nothing renders it yet.

## Open Questions

- The game has no cap on combat foes below the 16-participant presentation bound. Should the rules cap encounters
  (for example at 6)? This would simplify the stage; the client is designed for 15 regardless.
