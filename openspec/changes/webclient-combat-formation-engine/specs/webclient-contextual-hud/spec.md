## ADDED Requirements

### Requirement: Combat formation geometry is one pure shared-scale function
The client SHALL compute every combat figure box, plate slot and target-marker slot from one pure function of the stage geometry, the party figure count (1 to 5: the controlled figure plus at most four companions) and the drawn foe count (1 to 15), with one shared figure scale for both sides. The function SHALL keep a dead-centre gap of the combat command card's width plus a gutter on each side free of every figure box and slot.

#### Scenario: Inputs and outputs are explicit
- **WHEN** the function is called with the stage width and height, the desktop chrome factor S, the band's top edge, the portrait height `actor-h`, the top band's bottom edge, the vitals dock box, the card width `264px × S`, a party count and a foe count
- **THEN** it returns the shared scale, one figure box per party figure (controlled figure first) and per foe (presenter order), each figure's rank, one plate slot per figure with its form (`full` or `compact`), and one target-marker slot per figure, all in stage pixels, and it reads no DOM

#### Scenario: Both sides share one scale
- **WHEN** the function returns any formation
- **THEN** every figure box on both sides has the height `scale × actor-h` and the width `scale × actor-h × 2/3` (±0.5px), and the scale is one of 0.90, 0.84, 0.78, 0.72, 0.66, 0.60, 0.55

#### Scenario: The dead-centre gap stays clear
- **WHEN** the function returns any formation
- **THEN** no figure box, plate slot or marker slot intersects the band from `stage centre − 132px × S − 16px × S` to `stage centre + 132px × S + 16px × S`; the party stands entirely left of it and the foes entirely right of it, each inside the stage's 16px × S side gutters

#### Scenario: The scale follows a fixed policy
- **WHEN** the function chooses the scale
- **THEN** it picks the largest ladder value at which both sides fit with every plate slot in the `full` form (112px × S by 40px × S); if none does down to 0.55, the largest at which they fit with `compact` slots (72px × S by 30px × S); a side fits in one rank, or else in two ranks (front `ceil(n/2)`, back `floor(n/2)`, the back rank standing `0.27 × actor-h` higher and offset by half a step); figures in a rank are spaced by `min(0.62 × figure width, the zone's free width ÷ (count − 1, plus 0.5 for a back rank))`; plate slots alternate between two lines when one line would overlap

#### Scenario: The full matrix fits at the floor
- **WHEN** the function runs for every party count 1–5 and every foe count 1–15 at 1451x790, 1600x900, 1920x1080 and 2560x1440 with the reference vitals dock
- **THEN** it returns a formation for every case with scale at least 0.55; no two plate slots intersect (2px × S apart); every plate slot and the marker slot above it (20px × S) stays at least 8px × S below the top band; no plate slot intersects the vitals dock; the vitals dock covers at most the lowest 40% of any party figure box; and every box and slot stays inside the stage

#### Scenario: Reference values are pinned
- **WHEN** the function runs at 1451x790 and 1600x900
- **THEN** it returns the reference table recorded in this change's design (for example scale 0.90 with full plates for one figure against one foe, 0.78 with full plates for five figures against one to six foes, 0.55 with two foe ranks for one figure against eight to fourteen foes at 1451x790), and any later change to the table is a deliberate update of the pinned values
