# Delta spec: webclient-contextual-hud (webclient-align-03-narrative-feed)

## MODIFIED Requirements

### Requirement: The narrative is a bounded caption whose complete log is reachable in one action
The narrative SHALL render as a bounded caption card at the visual centre of the stage, constrained in
both measure and height so it never grows to fill the stage, drawn with the reference's caption panel
treatment: panel fill with backdrop blur, hairline border, shared radius and shadow, and the
reference's vertical hairline rule offset outside the card's left edge. The card SHALL carry a head
row styled as the reference's caption head (small uppercase letter-spaced label): on the left, a mode
label — `敘述` while the committed mode is exploration and `戰鬥日誌` while it is combat — and on the
right, a single labelled capsule control that opens a full-log surface presenting the complete
retained narrative through the same markup renderer as the caption — never a second markup path. The
full-log surface SHALL be scrollable, SHALL trap focus while open, SHALL close on Escape, and SHALL
restore focus to the control that opened it. The unread indicator, its polite live region, and its
jump-to-latest behaviour SHALL remain on the caption card beside the head label and SHALL otherwise
be unchanged.

#### Scenario: The caption card is bounded
- **WHEN** the narrative holds more lines than the caption card can show
- **THEN** the card scrolls internally within its bounded height and does not expand to fill the
  stage

#### Scenario: The head row names the mode and owns the log control
- **WHEN** the caption renders in exploration mode and then in combat mode
- **THEN** the head label reads `敘述`, then `戰鬥日誌`, and the `完整日誌` capsule is the card's only
  full-log control

#### Scenario: The complete log opens in one action
- **WHEN** the player activates the caption card's full-log control
- **THEN** the full-log surface opens showing the complete retained narrative, rendered through the
  same markup renderer as the caption

#### Scenario: The full-log surface returns focus on Escape
- **WHEN** the full-log surface is open and the player presses Escape
- **THEN** it closes and focus returns to the control that opened it

#### Scenario: The unread indicator is unchanged
- **WHEN** new narrative lines arrive while the caption card is scrolled away from the latest line
- **THEN** the unread indicator states its count and jump action and is announced through its polite
  live region exactly as before

### Requirement: Condition chips carry a severity glyph, a payload duration, and a bounded overflow
Each entry in `status.conditions` SHALL render as one chip pairing a per-severity shape glyph with an
accessible name carrying the condition's label, its remaining duration when the payload supplies one,
and every derived modifier the payload provides. The five severities SHALL each map to a distinct
glyph shape, so two severities are never separated by colour alone, and the beneficial and harmful
directions SHALL be readable from the glyph itself. Because the chip is icon-only, the island SHALL
also present that label, duration, and modifier text visibly when a chip is focused or hovered, so the
information the chip moves into its accessible name stays reachable by pointer and by keyboard.

The duration badge SHALL render only when the payload carries `remaining_seconds` for that condition;
a condition without one SHALL render no badge and no substitute value. The badge SHALL show the
payload's integer verbatim and SHALL NOT be decremented, animated down, or otherwise advanced by the
client between committed revisions.

Visible chips SHALL be bounded, and the remainder SHALL be reachable in one action through an overflow
chip stating how many are hidden. The overflow surface SHALL be bounded and scrollable and SHALL close
on Escape, so no committed condition becomes unreachable at any condition count the payload permits.
An empty condition list SHALL render no condition island at all — no placeholder island, no
`無條件` text — consistent with the contextual-hiding rule that an absent surface is not a dimmed or
emptied surface.

#### Scenario: A chip carries its label, duration, and modifiers
- **WHEN** a condition with a label, a remaining duration, and a derived modifier is committed
- **THEN** its chip renders the severity glyph and a duration badge, and its accessible name states
  the label, the remaining duration, and the modifier and its value

#### Scenario: Two severities are distinguishable without colour
- **WHEN** a warning condition and a harmful condition are committed together
- **THEN** their chips carry different glyph shapes and remain distinguishable with colour removed

#### Scenario: A condition without a duration renders no badge
- **WHEN** a committed condition carries no `remaining_seconds`
- **THEN** its chip renders no duration badge and no substitute value in its place

#### Scenario: The duration does not tick between revisions
- **WHEN** a chip with a duration badge is displayed and no new revision commits
- **THEN** the badge continues to show the payload's value unchanged, and the client runs no countdown

#### Scenario: Overflowing conditions stay reachable
- **WHEN** more conditions are committed than the island shows as chips
- **THEN** an overflow chip states the hidden count and reveals every remaining condition in one
  action, within a bounded scrollable surface that closes on Escape

#### Scenario: No conditions renders no island
- **WHEN** the committed condition list is empty
- **THEN** no condition island is rendered anywhere in the HUD

## ADDED Requirements

### Requirement: Narrative lines carry the reference's semantic classes
Committed narrative lines SHALL render with the reference draft's semantic presentation: a line of
committed `sys` kind SHALL render in the sans face at the reference's secondary size and colour with
a leading `◈` seal-colour marker contributed by the line's own class, not by invented text;
emphasis inside prose lines SHALL render in the reference's gold accent; plain prose lines SHALL
render in the serif reading face. The classes SHALL be mounted by the existing markup pipeline at
render time from committed line kinds only — the tokenizer, the player-echo divider lines, and the
box-drawing art path SHALL be unchanged, and no markup class SHALL be mounted for a kind the store
does not carry.

#### Scenario: A sys line renders with the seal marker
- **WHEN** a committed narrative line of kind `sys` renders
- **THEN** the line carries the reference's sys treatment including the leading `◈` marker, and the
  marker is decorative (absent from the accessible name of any surrounding live region update that
  already names the line's text)

#### Scenario: Emphasis renders gold inside prose
- **WHEN** a committed prose line carries emphasis through the markup pipeline
- **THEN** the emphasis renders in the reference's gold accent without changing the surrounding
  prose face

#### Scenario: Unknown kinds do not gain semantic classes
- **WHEN** a committed line carries no semantic kind beyond plain output
- **THEN** it renders as plain serif prose without the sys marker
