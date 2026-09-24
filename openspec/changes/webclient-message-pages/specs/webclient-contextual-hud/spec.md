## MODIFIED Requirements

### Requirement: Narrative lines carry the reference's semantic classes
Committed narrative lines SHALL render with the reference draft's semantic presentation: a line of
committed `sys` kind SHALL render in the sans face at the reference's secondary size and colour with
a leading `◈` seal-colour marker contributed by the line's own class, not by invented text;
emphasis inside prose lines SHALL render in the reference's gold accent; plain prose lines SHALL
render in the serif reading face. The classes SHALL be mounted by the existing markup pipeline at
render time from committed line kinds only — the tokenizer, the player-echo divider lines, and the
box-drawing art path SHALL be unchanged, and no markup class SHALL be mounted for a kind the store
does not carry. The markup pipeline SHALL run exactly once for each retained server, system, or error
line, when the line is retained. Every surface that renders the line SHALL render from that one token
stream, never from a second tokenization or a second markup path. A player input line SHALL never
enter the pipeline. A fragment of a line that paging has split SHALL render with the same kind class,
and the same box-drawing class where it applies, as the whole line would. Only the first fragment
of a `sys` line SHALL show the leading `◈` marker.

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

#### Scenario: Each line is tokenized once
- **WHEN** a server line is retained and is then rendered by the narrative surface and by the
  full-log surface, each more than once
- **THEN** the markup pipeline has run for that line exactly once, and both surfaces render the
  same token stream

#### Scenario: A split line's fragments keep the line's classes
- **WHEN** a `sys` line, and separately a prose line carrying emphasis, are each split into two
  fragments
- **THEN** both fragments of the `sys` line carry the sys face and colour, only the first shows the
  `◈` marker, and both fragments of the prose
  line render in the serif reading face with the emphasis still gold in whichever fragment holds it
