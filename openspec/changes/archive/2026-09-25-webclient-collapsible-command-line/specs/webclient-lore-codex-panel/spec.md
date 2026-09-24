## ADDED Requirements

### Requirement: The codex opens from the top navigation bar, not from the quest drawer

The codex drawer SHALL be opened by the labelled 圖鑑 control in the top navigation bar's tool group,
and by no control inside the quest drawer or the command line. The control SHALL open the codex
reference drawer through the store's single open-drawer entry point, so at most one focus-trapped
surface is open at a time and the existing drawer teardown rules apply unchanged, and closing the
drawer SHALL return focus to the control. Its glyph SHALL be visually distinct from the adjacent
title-codex (稱號冊) control, which opens a different system.

#### Scenario: The top navigation bar opens the codex
- **WHEN** the player activates the 圖鑑 control in the top navigation bar's tool group while the command line is collapsed
- **THEN** the codex reference drawer opens and any previously open drawer or overlay closes

#### Scenario: The quest drawer offers no codex control
- **WHEN** the quest drawer renders
- **THEN** it contains no control that opens the codex

#### Scenario: The two codex controls are distinguishable
- **WHEN** the top navigation bar's tool group renders
- **THEN** the world-codex control and the title-codex control carry distinct labels and distinct
  glyphs

## REMOVED Requirements

### Requirement: The codex opens from the command-line utility strip, not from the quest drawer
**Reason**: The command line is collapsed by default (AVG stage design §5.5), so its utility strip no longer holds overlay or drawer openers; they move to the top navigation bar's tool group. The requirement's subject (where the codex opens from) changes, so it is replaced.
**Migration**: "The codex opens from the top navigation bar, not from the quest drawer" states the same single-opener, distinct-glyph contract for the tool-group control. Tests annotated with the old ID re-anchor to the new one.
