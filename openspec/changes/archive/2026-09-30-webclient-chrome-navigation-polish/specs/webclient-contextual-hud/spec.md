## MODIFIED Requirements

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card in its `place` anchor, at the stage box's top-left corner below the
top band, while the committed mode is exploration, dialogue, or combat, and SHALL NOT render it in
creation mode. The card SHALL state the current location as its heading and the world date/time
beneath it, and SHALL be the only surface on the stage or in the top band that states either value.
The location SHALL be the best server-authored place name the client already holds, resolved in a
fixed order: the committed `local_map` panel's `current_node` label when that panel is available,
names a current node, that node is present in the panel's nodes, and its label is a non-empty string;
otherwise the committed status panel's actor location label; otherwise the card's own unavailable
placeholder `位置：--`. The world date/time SHALL be the committed world-time label, and the card's own
unavailable placeholder `時間：--` when none is committed. The card SHALL NOT compose a third string
from the two location candidates, SHALL NOT derive a name from any node or room identifier, SHALL NOT
render a raw room key while a committed panel carries the authored place name for the same room, and
SHALL render no raw mode label in place of the location.

The card SHALL wear the HUD island chrome (the translucent panel fill, the backdrop blur, the
hairline border, the shared radius and shadow, all from the shared design tokens), SHALL keep a fixed
height whatever the label lengths, and SHALL truncate a label that exceeds its width with an overflow
indicator while keeping the full label as its accessible text. It SHALL be display-only: no control,
no tab stop, and no dispatch.

The card SHALL set its two values on two levels: the location heading in the serif face, then a
quiet decorative gold rule, hidden from assistive technology, then the world-time line. The
world-time line SHALL carry no leading separator glyph or rule before its first value, SHALL use the
numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 12px chrome
floor), and SHALL render the committed world-time label (or its placeholder) verbatim, with every
date and time value intact: all time values SHALL remain server-authored, and the card SHALL NOT
reformat, abbreviate, or derive them. The heading, the rule, and the time line SHALL fit the card's
fixed height.

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 · 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 · 12:00`, and no other stage or top-band element states either string

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode the place card is not rendered and holds no tab stop

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the time line's numerals are tabular lining figures in the numeral face, and the card keeps its fixed height
