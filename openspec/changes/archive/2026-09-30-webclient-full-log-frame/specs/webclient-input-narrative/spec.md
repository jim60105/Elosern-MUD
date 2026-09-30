## ADDED Requirements

### Requirement: The full log is framed without changing retained content
The full-log surface SHALL present itself in the shared reference workspace used by the drawers and
utility overlays: one opaque panel under the shared reference header, which draws the log's glyph, the
title `日誌` labelling the dialog, and one close control. A scrim SHALL cover the whole viewport behind
the panel, the top navigation included, and SHALL absorb pointer input without closing the log. The
header SHALL only lend markup: the surface SHALL keep its own focus trap, Escape close and focus restore
to the opening control, and SHALL NOT nest a second modal host. A pointer press on the frame's
non-focusable chrome or the scrim SHALL leave focus inside the surface, so Escape still closes it.

The lines SHALL read as one centred column with a 42em measure at the log's reading size, which the
narrative prose scale multiplies; the header, footer and their controls are chrome and SHALL NOT scale.
The column SHALL reuse the message window's prose styling — the `sys` aside, the `err` line, the
progressive CJK spacing — and every line SHALL share the column's edge. A box-drawing map line SHALL keep
its monospace grid and SHALL scroll horizontally inside its own block rather than widen the column.

Each retained input echo SHALL be styled in place as the heading of the response it begins, after the
existing divider hairline. The surface SHALL render every retained line exactly once and in its
original order through the existing safe renderer, and SHALL NOT duplicate, reorder, rewrite or remove
any line, input echoes included. Opening SHALL still show the latest line before interaction.

#### Scenario: Echo is a section heading
- **WHEN** a retained response begins with a player input echo
- **THEN** that echo appears exactly once in its original position, styled as the response's heading
  after its divider, and its response lines remain unchanged

#### Scenario: The frame keeps the log's own modal lifecycle
- **WHEN** the player opens the full log, clicks the scrim, and presses Escape
- **THEN** the click neither closes the log nor moves focus out of it, Escape closes it, and focus
  returns to the control that opened it

### Requirement: Log readers can return to latest without losing their place involuntarily
When the scroll region's visible box ends above the end of its content, the full log SHALL offer a
labelled `回到最新` control in a footer strip outside the scroll region, so the control never covers a
line or a text selection; at the end of the content the control SHALL be absent. Arriving lines SHALL
NOT force-scroll the reader. Once a line has been retained since the reader last saw the end, the
control SHALL also read `新內容`, until the end is in view again; the arrival SHALL be recognised by the
newest line's retention ordinal, so it holds when retention trimming keeps the line count constant.
Activating the control SHALL move focus to the scroll region and reveal the latest retained line —
smoothly only at the full motion level — and SHALL NOT advance or re-page the message window, dispatch
any action, or change the log's retention. When the end comes into view while the control holds focus,
focus SHALL move to the scroll region before the control leaves. The reading keys (arrows, Page Up and
Page Down, Home and End) pressed on the log's controls SHALL scroll the region as they do when it has
focus. The message window's own rule of rendering no jump-to-latest control is unchanged; this control
belongs to the full log only.

#### Scenario: New text arrives during review
- **WHEN** the player has scrolled upward and a new response arrives
- **THEN** the viewed position remains stable and the return control reveals the new end only when
  activated

#### Scenario: The control is absent at the end
- **WHEN** the full log opens at its latest line
- **THEN** no return control is rendered until the player scrolls above the end

#### Scenario: Returning leaves the message window alone
- **WHEN** the player activates the return control while the message window shows page 1 of a
  multi-page response
- **THEN** the scroll region shows its latest line with focus on it, the control is gone, the message
  window still shows the same page, and no action is sent

## MODIFIED Requirements

### Requirement: The full-log surface opens at its latest line
Whenever the full-log surface opens, it SHALL present the most recent retained narrative line in
view, with its scroll region scrolled to the end of its content, so the player sees the latest one or
two replies without scrolling. The scroll region is the log's one scrolling box inside its frame; it
SHALL take the initial focus, so the reading keys scroll it at once. The surface SHALL reach that
position after it takes focus and before the player can interact with it, and it SHALL NOT first flash its opening lines. Older lines SHALL stay reachable by
scrolling up, and the surface SHALL keep presenting the complete retained narrative through the same
markup renderer as before. While the surface is open, a newly retained line SHALL NOT change the
scroll region's offset, including once retention trimming removes the oldest line. Only opening the surface places the reader at the latest line. The surface
SHALL keep its focus trap, its Escape close, and its focus restore to the opening control unchanged.

#### Scenario: A long log opens at the latest reply
- **WHEN** the narrative retains more lines than the full-log surface can show at once and the player
  opens the full-log surface
- **THEN** the scroll region's offset is at the end of its content, the most recently retained line
  is inside the scroll region's visible box, and the first retained line is scrolled out of view above

#### Scenario: Older lines stay reachable
- **WHEN** the full-log surface has opened at its latest line and the player scrolls up
- **THEN** earlier retained lines come into view in their original order, rendered through the same
  markup renderer

#### Scenario: A line arriving while reading does not move the reader
- **WHEN** the player has scrolled the open full-log surface up to read older lines and a new
  narrative line is retained
- **THEN** the scroll region's offset is unchanged, and the new line is present at the end of the log

#### Scenario: Reopening returns to the latest line
- **WHEN** the player scrolls the full-log surface up, closes it, a new line is retained, and the
  player opens it again
- **THEN** the surface opens at its end again, with the newly retained line in view
