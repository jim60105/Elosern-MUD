## ADDED Requirements

### Requirement: Figure plates show conditions at a glance and their details on demand
Each combat figure plate SHALL show the participant's committed conditions (`context_actions` v6 `conditions`) as glyph-only icons whose shape and hue follow the vitals dock's severity glyphs, and SHALL show a condition's name only on demand, in a tooltip that no plate shows at rest. A plate SHALL mark low hit points with text and colour together, and the plates SHALL form one keyboard group.

#### Scenario: Conditions are glyphs with accessible names
- **WHEN** a foe is poisoned (`harmful`) and blessed (`beneficial`) and a companion carries five conditions, in `full` plates
- **THEN** the foe's plate shows the two severity glyphs (the vitals dock's distinct shapes, never colour alone) on its third line, the companion's plate shows its first three glyphs and a `+2` glyph there, each glyph standing in a 24px × S hit box that stays inside the plate slot, the name and the stroke keep their own lines at their full widths, every glyph's accessible name is the shared condition label, and no condition word is permanently visible

#### Scenario: A full plate's glyph line fits its slot
- **WHEN** a `full` plate carries eight conditions
- **THEN** its third line holds three glyphs and `+5`, four 24px × S hit boxes inside the plate's content width, bottom-aligned on the slot's lower edge, and the `+5` glyph's tooltip lists the five hidden conditions

#### Scenario: A compact plate keeps one glyph
- **WHEN** a plate takes the `compact` form with three conditions
- **THEN** it shows on its second line the most severe condition's glyph (critical, then harmful, warning, informational, beneficial) and `+2`, the first line keeping its stroke at least 30px × S long, and its accessible name lists all three conditions

#### Scenario: A compact plate in danger folds its overflow into its glyph
- **WHEN** a `compact` plate with three conditions falls to low hit points
- **THEN** its second line shows the `危險` tag and the most severe glyph, marked as carrying more, whose tooltip lists all three conditions in place of the `+2` glyph, and its accessible name still lists all three

#### Scenario: The tooltip opens on demand and closes on every exit
- **WHEN** the pointer rests on a plate's glyph, and separately keyboard focus reaches it; then the pointer leaves, focus moves on, Escape is pressed, the stage resizes, the condition disappears from the committed panel, a combat round starts playing, and the mode leaves combat
- **THEN** a `role="tooltip"` ink plate with a gold tick pointing at the glyph opens on hover and on focus, describes the condition (title with glyph, then any detail lines in tabular figures) through `aria-describedby`, and closes in each of those cases; Escape is consumed only while a tooltip is open

#### Scenario: A tooltip stays inside the viewport
- **WHEN** a glyph's tooltip opens on a plate near the stage's right edge, and on a plate too close to the top for the tooltip to stand above it
- **THEN** the tooltip shifts left to stay at least 4px inside the viewport with its tick still pointing at the glyph, and opens below the glyph instead of above it

#### Scenario: No tooltip is open at rest
- **WHEN** combat renders and no pointer rests on a glyph and no glyph holds keyboard focus
- **THEN** no condition tooltip is shown, so the plates alone keep every head and every plate uncovered

#### Scenario: Low hit points add text and colour together
- **WHEN** a companion falls to 25% of its maximum hit points or below, and later recovers above it
- **THEN** its readout's current value turns the critical hue and a small `危險` tag joins the plate (after the name on a `full` plate, which ellipsizes to make room; on the glyph line of a `compact` plate), and both clear on recovery; the threshold is the vitals dock's `LOW_HP_THRESHOLD` applied to the displayed value, and the accessible name states 危險

#### Scenario: The plates are one keyboard group
- **WHEN** keyboard focus leaves the action dock (`#action-dock`) with Tab while combat is shown
- **THEN** the plates layer is the next single tab stop (`role="group"`, accessible name 戰場) and focus lands on the last focused plate or glyph, else the leftmost plate; inside it ArrowLeft and ArrowRight move between plates in stage order (left to right), ArrowDown and ArrowUp between the focused plate and its glyphs, the focused glyph opens its tooltip, Escape (once no tooltip is open) returns focus to `#action-dock`, Tab and Shift+Tab leave the group, the keys the group handles never reach the dock's keyboard router, and the focus ring is the global gold double ring

#### Scenario: Motion follows the motion level
- **WHEN** a glyph appears or a tooltip opens at `full`, at `reduced`, and at `off`
- **THEN** feedback uses the fast motion token at `full`, fades without travel at `reduced`, and appears in one frame at `off`

## MODIFIED Requirements

### Requirement: Combat figures carry glance plates
While the formation is shown, each drawn combat figure other than the controlled figure SHALL carry one plate in its formation plate slot in the stage's `plates` layer: the name, a thin hit-point stroke, a tabular readout and a line for condition glyphs; the controlled figure's vitals stay in the vitals dock. A plate SHALL NOT overlap another plate, the card, the vitals dock, the command-line row, the top band or any head, and nothing SHALL cover it.

#### Scenario: A full plate reads name, stroke and numbers
- **WHEN** a companion at 42 of 120 hit points and a foe at 18 of 30 stand in a formation with `full` plate slots
- **THEN** each 112px × S by 52px × S plate shows on its first line the display name in the serif small text (ellipsized within the plate, the full name kept in the DOM and in its accessible name), on its second line a 4px × S tapered stroke filled to the current fraction followed by the readout `42` / `120` and `18` / `30` with the current value bright and `/ maximum` receding in tabular figures, and keeps its third line for condition glyphs

#### Scenario: A compact plate keeps the stroke and the number
- **WHEN** the formation returns `compact` plate slots
- **THEN** each 72px × S by 36px × S plate hides the name visually (the name stays its accessible name), shows on its first line the stroke (at least 30px × S long) and the current hit points, and keeps its second line for a condition glyph

#### Scenario: Plates never collide
- **WHEN** combat renders for every party count 1–5 against foe counts 1, 3, 7, 8 and 16 minus the party count at 1451x790 and 1600x900
- **THEN** every plate lies inside its slot (±1px), no two plates intersect, and no plate intersects the command card's column, the vitals dock or the top band

#### Scenario: No head is ever covered and no plate is covered
- **WHEN** combat renders for every party count 1–5 against foe counts 1, 4, 8 and 16 minus the party count at 1451x790 and 1600x900, in one rank and in two
- **THEN** no plate (and no target-marker slot) intersects any standing figure's head — the central 30% of its box's width and the top 22% of its height — in the front rank or the back rank; no front-rank figure reaches a back-rank head; the heads of one rank never overlap; a figure's lower body MAY be covered; and the plates layer paints above every figure, so no figure covers a plate

#### Scenario: A two-rank side's front plates stand on the floor line
- **WHEN** a side stands in two ranks
- **THEN** each back-rank plate stands above its figure's head, and each front-rank plate stands on the side's floor line over its own figure's lower body — 8px × S above the command-line row and, for the party, 8px × S above the vitals dock — so no front-rank plate lies across a back-rank face

#### Scenario: Plates follow playback
- **WHEN** a combat round plays damage beats on a foe and on a companion
- **THEN** each plate's stroke and readout show the displayed value the beat publishes (`displayHp`) and settle to the committed value when the round ends, so the plate never shows a later value than the beat's page

#### Scenario: The plates layer is outside the portrait anchors
- **WHEN** the formation renders
- **THEN** the plates render in the stage's `plates` layer above the portrait anchors and below the HUD islands, the band and the command card, the layer holds only the plates, its only keyboard entry is the plates group that "Figure plates show conditions at a glance and their details on demand" defines, and outside combat it renders nothing and is no tab stop

#### Scenario: Repeated names carry their session token
- **WHEN** three foes share the display name 哥布林 and a fourth is named 狼
- **THEN** each 哥布林 plate shows its session token after the name (`哥布林 e1`, `哥布林 e2`, `哥布林 e3`) and the 狼 plate shows no token; a token is shown only while two drawn participants share a name
