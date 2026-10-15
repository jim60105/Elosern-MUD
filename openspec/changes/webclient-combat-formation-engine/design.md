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
matrix (party 1–5 × foes 1–15) at the supported viewports, with a guaranteed dead-centre gap and one shared scale;
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

- **Scale ladder:** 0.90, 0.84, 0.78, 0.72, 0.66, 0.60, 0.55. The floor 0.55 keeps a figure 269px tall at 1451x790
  and 307px at 1600x900.
- **Per side:** one rank if it fits, else two ranks:
  - the front rank has `ceil(n/2)` figures and the back rank `floor(n/2)`;
  - the back rank stands `0.27 × actor-h` up-stage, at the same scale, offset by half a step so its figures show
    between the front ones.
- **Spacing:** step = `min(0.62 × w, (zone − w) / (count − 1 + backShift))`. The group's outer edge sits at the
  side's home inset (6vw) when it fits, and is otherwise pushed toward the outer gutter, never into the gap.
- **Plate slots:** centred over each figure, bottom edge 4px·S above the figure box top.
  - `full` slots are 112×40px·S. If one line would make neighbours closer than the slot width, alternate figures
    use a second line raised by slot height + 4px·S.
  - `compact` slots are 72×30px·S, used only when full ones cannot fit at any ladder scale.
- **Marker slot:** 20px·S above the plate slot (the target arrow of `webclient-combat-stage-target-picking`).
- **Policy:** take the largest scale at which both sides fit with all-`full` slots, else the largest with `compact`
  slots. Party size also limits the shared scale: five figures cap it at 0.78 at 1451x790. Two ranks are a fallback
  before shrinking below the floor, never after.

### D3. Invariants (Vitest over the matrix)

The test covers party 1–5 × foes 1–15 × {1451x790, 1600x900, 1920x1080, 2560x1440} with the reference vitals dock
(25vw × 92px·S on the band). For every case:

- A formation is returned, with scale ≥ 0.55.
- Every figure box has the same height on both sides.
- The gap `[C − Wc/2 − g, C + Wc/2 + g]` is free of all boxes and slots.
- Plate slots are pairwise ≥ 2px·S apart.
- Plate and marker slots stay ≥ 8px·S below the top band.
- No plate slot touches the vitals dock, and the dock covers ≤ 40% of any party box.
- Everything stays inside the stage gutters.

The case party 5 × foes 15 exceeds the 16-participant cap but is kept as the upper bound.

### D4. Reference table (planning prototype; the Vitest pins the engine's actual table)

Each cell gives the shared scale, the plate form (F full / C compact), and the number of ranks for the party and for
the foes:

| 1451x790 | foes 1 | 2 | 3 | 4–6 | 7 | 8–14 | 15 |
|---|---|---|---|---|---|---|---|
| party 1–3 | 0.90 F 1/1 | 0.90 F 1/1 | 0.90 F 1/1 | 0.78 F 1/1 | 0.60 F 1/1 | 0.55 F 1/2 | 0.55 C 1/2 |
| party 4–5 | 0.78 F 1/1 | 0.78 F 1/1 | 0.78 F 1/1 | 0.78 F 1/1 | 0.60 F 1/1 | 0.55 F 1/2 | 0.55 C 1/2 |

| 1600x900 | foes 1–3 | 4–6 | 7 | 8–13 | 14–15 |
|---|---|---|---|---|---|
| party 1–3 | 0.90 F 1/1 | 0.78 F 1/1 | 0.60 F 1/1 | 0.55 F 1/2 | 0.60 C 1/2 |
| party 4–5 | 0.78 F 1/1 | 0.78 F 1/1 | 0.60 F 1/1 | 0.55 F 1/2 | 0.60 C 1/2 |

- The engine first tries all-`full` slots down to the floor, then `compact`. That is why 14–15 foes at 1600x900 come
  out at 0.60 with compact plates, larger than 13 foes at 0.55 with full plates.
- 1920x1080 matches 1600x900.
- At 2560x1440: 0.90 full in one rank up to 7 foes, then 0.78 / 0.66 for 8–9, then 0.60 in two ranks.
- Sample boxes at 1451x790:
  - Solo against one foe at 0.90: the player 87–381 and the foe 1070–1364, both x 129–570.
  - Five figures against three foes at 0.78: the party's front figure 323–578, the foes 874–1435.
  - One figure against fifteen foes at 0.55: the foes in two ranks from x 874; the front rank stands on the band and
    the back rank's boxes span y 169–438.

### D5. Module

- `web/webclient-app/components/combat-formation.js` exports `combatFormation(input)` and the constants
  (`SCALE_LADDER`, `SCALE_FLOOR`, `CARD_WIDTH`, slot sizes, `BACK_RANK_LIFT`, `RANK_STEP`).
- It reads only its input object (stage width and height, S, band top, `actor-h`, top-band bottom, vitals box, counts).

## Risks / Trade-offs

- [Smaller figures than today in big fights] → the floor keeps figures ≥ 269px tall at the reference viewport, and
  two ranks are used before any further shrink.
- [The prototype's numbers drift in the real module] → the invariants are normative; the pinned table is updated
  deliberately in the same commit.

## Migration Plan

Pure addition; nothing renders it yet.

## Open Questions

- The game has no cap on combat foes below the 16-participant presentation bound. Should the rules cap encounters
  (for example at 6)? This would simplify the stage; the client is designed for 15 regardless.
