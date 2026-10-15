## ADDED Requirements

### Requirement: Combat formation geometry is one pure shared-scale function
The client SHALL compute every combat figure box, plate slot and marker slot from one pure function of the stage geometry, the party figure count (1 to 5: the controlled figure plus at most four companions) and the drawn foe count (1 to 16 minus the party count), with one shared figure scale for both sides. The function SHALL keep a dead-centre gap of the combat command card's width plus a gutter on each side free of every figure box and slot.

#### Scenario: Inputs and outputs are explicit
- **WHEN** the function is called with the stage width and height, the desktop chrome factor S, the band's top edge, the portrait height `actor-h`, the top band's bottom edge, the vitals dock box, the card width `264px × S`, a party count and a foe count
- **THEN** it returns the shared scale, one figure box per party figure (controlled figure first) and per foe (presenter order), each figure's rank, one plate slot per figure with its form (`full` or `compact`), and one target-marker slot per figure, all in stage pixels, and it reads no DOM

#### Scenario: Both sides share one scale
- **WHEN** the function returns any formation
- **THEN** every figure box on both sides has the height `scale × actor-h` and the width `scale × actor-h × 2/3` (±0.5px), and the scale is one of 0.90, 0.84, 0.78, 0.72, 0.66, 0.60, 0.55, 0.50

#### Scenario: The dead-centre gap stays clear
- **WHEN** the function returns any formation
- **THEN** no figure box, plate slot or marker slot intersects the band from `stage centre − 132px × S − 16px × S` to `stage centre + 132px × S + 16px × S`; the party stands entirely left of it and the foes entirely right of it, each inside the stage's 16px × S side gutters

#### Scenario: A side fits by an explicit rule
- **WHEN** the function tests whether a side of n figures fits at scale s with one rank, or with two ranks (front `ceil(n/2)`, back `floor(n/2)` standing `0.27 × actor-h` higher, offset by half a step)
- **THEN** it fits exactly when all of these hold: the step `min(0.62 × w, (zone − w) ÷ (count − 1, plus 0.5 for a back rank))` is not negative and every box lies inside the side's zone (from the 16px × S stage gutter to 148px × S from the centre); each rank's plate slots take one line when the step is at least the slot width plus 4px × S, two alternating lines when twice the step is, and otherwise do not fit (or, only when compact slots are allowed, the same test with the compact slot); every plate slot's marker slot (24px × S above it) stays at least 8px × S below the top band; no two plate slots on the side are closer than 2px × S, across ranks too; no plate slot touches the vitals dock; and the vitals dock covers at most the lowest 40% of any party box

#### Scenario: The scale follows a fixed policy
- **WHEN** the function chooses the scale
- **THEN** it walks the ladder from 0.90 down to the floor 0.50, at each scale giving each side one rank if it fits and else two ranks if they fit, and returns the first scale at which both sides fit with every slot `full` (112px × S by 52px × S); if none does, it walks the ladder again allowing `compact` slots (72px × S by 36px × S); a second rank is therefore always tried at a scale before the scale shrinks further, and no scale below 0.50 is ever used

#### Scenario: Inputs outside the supported range still return a formation
- **WHEN** no ladder scale fits, for example on a stage smaller than the 1451x790 reference
- **THEN** the function returns the floor-scale, two-rank, compact formation with `fits: false`, the stage renders it, and the invariants below are asserted only for inputs where `fits` is true

#### Scenario: The full matrix fits at the floor
- **WHEN** the function runs for every party count 1–5 and every foe count from 1 to 16 minus the party count at 1451x790, 1600x900, 1920x1080 and 2560x1440 with the reference vitals dock
- **THEN** it returns `fits: true` for every case with scale at least 0.50; no two plate slots intersect (2px × S apart); every plate slot and the marker slot above it (24px × S) stays at least 8px × S below the top band; no plate slot intersects the vitals dock; the vitals dock covers at most the lowest 40% of any party figure box; and every box and slot stays inside the stage

#### Scenario: Anchor values are normative
- **WHEN** the function runs at 1451x790
- **THEN** it returns scale 0.84 with `full` slots and one rank per side for one party figure against one to three foes; 0.72 with `full` slots for five party figures against one to six foes; 0.60 with one foe rank for one to five party figures against seven foes; 0.50 with two foe ranks and `full` slots for one party figure against eight to fourteen foes; and 0.50 with two foe ranks and `compact` slots for one party figure against fifteen foes
