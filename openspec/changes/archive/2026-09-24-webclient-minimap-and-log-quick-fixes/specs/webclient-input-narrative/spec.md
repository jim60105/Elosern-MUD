## ADDED Requirements

### Requirement: The full-log surface opens at its latest line
Whenever the full-log surface opens, it SHALL present the most recent retained narrative line in
view, scrolled to the end of its scrollable content, so the player sees the latest one or two replies
without scrolling. It SHALL reach that position after it takes focus and before the player can
interact with it, and it SHALL NOT first flash its opening lines. Older lines SHALL stay reachable by
scrolling up, and the surface SHALL keep presenting the complete retained narrative through the same
markup renderer as before. While the surface is open, a newly retained line SHALL NOT change the
reader's scroll position. Only opening the surface places the reader at the latest line. The surface
SHALL keep its focus trap, its Escape close, and its focus restore to the opening control unchanged.

#### Scenario: A long log opens at the latest reply
- **WHEN** the narrative retains more lines than the full-log surface can show at once and the player
  opens the full-log surface
- **THEN** the surface's scroll offset is at the end of its content, the most recently retained line
  is inside the surface's visible box, and the first retained line is scrolled out of view above

#### Scenario: Older lines stay reachable
- **WHEN** the full-log surface has opened at its latest line and the player scrolls up
- **THEN** earlier retained lines come into view in their original order, rendered through the same
  markup renderer

#### Scenario: A line arriving while reading does not move the reader
- **WHEN** the player has scrolled the open full-log surface up to read older lines and a new
  narrative line is retained
- **THEN** the surface's scroll offset is unchanged, and the new line is present at the end of the log

#### Scenario: Reopening returns to the latest line
- **WHEN** the player scrolls the full-log surface up, closes it, a new line is retained, and the
  player opens it again
- **THEN** the surface opens at its end again, with the newly retained line in view
