## ADDED Requirements

### Requirement: Figure plates show conditions at a glance and their details on demand
Each combat figure plate SHALL show the participant's committed conditions (`context_actions` v6 `conditions`) as glyph-only icons whose shape and hue follow the vitals dock's severity glyphs, and SHALL show a condition's name and detail only on demand in a tooltip. A plate SHALL mark low hit points with text and colour together.

#### Scenario: Conditions are glyphs with accessible names
- **WHEN** a foe is poisoned (`harmful`) and blessed (`beneficial`) and a companion carries five conditions, in `full` plates
- **THEN** the foe's plate shows the two severity glyphs (the vitals dock's distinct shapes, never colour alone) on its third line, the companion's plate shows its first three glyphs and a `+2` glyph there, each glyph drawn 14px × S tall inside a 24px × S hit box that stays inside the plate slot, the name and the stroke keep their own lines at full width, every glyph's accessible name is the shared condition label, and no condition word is permanently visible

#### Scenario: A compact plate keeps one glyph
- **WHEN** a plate takes the `compact` form with three conditions
- **THEN** it shows on its second line the most severe condition's glyph and `+2` (and the `危險` tag when low), the first line keeping its stroke at least 30px × S long, and its accessible name lists all three conditions

#### Scenario: The tooltip opens on demand and closes on every exit
- **WHEN** the pointer rests on a plate's glyph, and separately keyboard focus reaches it; then the pointer leaves, focus moves on, Escape is pressed, the stage resizes, the condition disappears from the committed panel, a combat round starts playing, and the mode leaves combat
- **THEN** a `role="tooltip"` ink plate with a gold tick pointing at the glyph opens on hover and on focus, describes the condition (title with glyph, then detail lines in tabular figures) through `aria-describedby`, and closes in each of those cases; Escape is consumed only while a tooltip is open

#### Scenario: Low hit points add text and colour together
- **WHEN** a companion falls to 25% of its maximum hit points or below, and later recovers above it
- **THEN** its readout's current value turns the critical hue and a small `危險` tag joins the readout, in both plate forms, and both clear on recovery; the threshold is the vitals dock's `LOW_HP_THRESHOLD`

#### Scenario: The plates are one keyboard group
- **WHEN** keyboard focus leaves the action dock (`#action-dock`) with Tab while combat is shown
- **THEN** the plates layer is the next single tab stop (`role="group"`, accessible name 戰場); inside it ArrowLeft and ArrowRight move between plates in stage order, ArrowUp and ArrowDown between the focused plate's glyphs, the focused glyph opens its tooltip, Escape and Tab leave the group, the group's keys never reach the dock's keyboard router, and the focus ring is the global gold double ring

#### Scenario: Motion follows the motion level
- **WHEN** a glyph appears or a tooltip opens at `full`, at `reduced`, and at `off`
- **THEN** feedback uses the fast motion token at `full`, fades without travel at `reduced`, and appears in one frame at `off`
