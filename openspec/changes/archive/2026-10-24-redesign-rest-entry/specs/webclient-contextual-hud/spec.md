## MODIFIED Requirements

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's top-right corner directly below the top band and directly above the minimap island, while the committed mode is exploration, and SHALL NOT render it in combat, creation or settled dialogue mode. The card SHALL state the current location as its heading and the world date/time beneath it, and SHALL be the only surface on the stage or in the top band that states either value.

#### Scenario: Dialogue entry leaves only inert exit paint
- **WHEN** the mode live-enters dialogue
- **THEN** the card MAY retain only the inert exit paint permitted by "Surface visibility is gated by the committed game mode", outside the accessibility tree and tab order from commit, and becomes `display:none` when the anchor's fade ends

#### Scenario: The card carries the room actions at the exploration root
- **WHEN** the committed mode is exploration while the exploration panel is available and the exploration dock is at its root frame
- **THEN** the card also carries the room actions `webclient-room-actions` defines — a 查看房間 icon button beside the heading and a 休息 button beside the time — and in every other mode and state it carries no control

#### Scenario: The location resolves in a fixed order
- **WHEN** the card resolves its location
- **THEN** it uses the best server-authored place name the client already holds: the committed `local_map` panel's `current_node` label when that panel is available, names a current node, that node is present in the panel's nodes, and its label is a non-empty string; otherwise the committed status panel's actor location label; otherwise the card's own unavailable placeholder `位置：--`

#### Scenario: The world time is committed or placeholdered
- **WHEN** the card renders its world date/time
- **THEN** it is the committed world-time label, and the card's own unavailable placeholder `時間：--` when none is committed

#### Scenario: The card composes and guesses nothing
- **WHEN** location candidates exist or identifiers are available
- **THEN** the card composes no third string from the two location candidates, derives no name from any node or room identifier, renders no raw room key while a committed panel carries the authored place name for the same room, and renders no raw mode label in place of the location

#### Scenario: The card wears island chrome at a fixed size
- **WHEN** the card renders
- **THEN** it wears the HUD island chrome (the translucent panel fill, the backdrop blur, the hairline border, the shared radius and shadow, all from the shared design tokens), spans the same content-column width as the minimap island beneath it, keeps a fixed height whatever the label lengths, and truncates a label that exceeds its width with an overflow indicator while keeping the full label as its accessible text

#### Scenario: The card is display-only
- **WHEN** the card renders outside exploration, or while the exploration panel is unavailable
- **THEN** it carries no control, no tab stop, and no dispatch; in exploration with the panel available its only controls are the 查看房間 and 休息 buttons, which never truncate the heading's accessible name, and the card itself dispatches nothing

#### Scenario: The two values read on two levels
- **WHEN** the card renders heading and time
- **THEN** it sets them on two levels: the location heading in the serif face at the `--text-lg` step, then a quiet decorative gold rule, hidden from assistive technology, then the world-time line; the heading, the rule, and the time line fit the card's fixed height

#### Scenario: The time line keeps every server value intact
- **WHEN** the world-time line renders
- **THEN** it carries no leading separator glyph or rule before its first value, uses the numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 16px chrome floor), and renders the committed world-time label (or its placeholder) verbatim, with every date and time value intact: all time values remain server-authored, and the card reformats, abbreviates, or derives none of them

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 ‧ 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 ‧ 12:00`, and no other stage or top-band element states either string

#### Scenario: The card heads the map column
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel
- **THEN** the place card is the first island of the `map` anchor, its rendered width equals the minimap island's rendered width, and the stage renders no place card in its left column

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation, and later dialogue
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode and in settled dialogue mode the place card is not rendered and holds no tab stop; during live dialogue entry only its inert exit paint may remain until the map anchor's fade ends

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the heading is set one
  step below the display size the stage's island chrome uses at `--text-lg`, the time line's numerals
  are tabular lining figures in the numeral face, and the card keeps its fixed height

#### Scenario: The place card carries its amendment
- **WHEN** the `place-card-relocation` amendment applies to this requirement
- **THEN** the visible-mode set narrows to exploration and combat with this change, matching the visibility matrix's dialogue `hidden` cells

#### Scenario: The card is absent in combat
- **WHEN** the committed mode changes from exploration to combat, and later back
- **THEN** in combat the place card is not rendered (`display:none`, outside the accessibility tree) while it keeps its committed location and time, and on the return it renders again as the first island of the `map` anchor
