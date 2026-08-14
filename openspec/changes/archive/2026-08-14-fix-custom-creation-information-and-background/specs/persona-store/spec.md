## MODIFIED Requirements

### Requirement: Flatten produces one bounded, labeled prompt block
`PersonaStore.flatten(fields=("personality", "life_story", "habit"))` SHALL return a single string
with one labeled section per present field in the declared field order (e.g. 性格：… /
人生經歷：… / 習慣：…, and 背景：… for a `background` field), each field string capped and the
combined block capped at a total bound. A missing record, a non-mapping record, or a record with
none of the requested fields present SHALL return `None` and never raise. The default field set
(and therefore NPC dialogue injection) remains the three prose fields; `background` is included
only when explicitly requested.

#### Scenario: Three present fields flatten in declared order with labels
- **WHEN** a record contains all three prose fields and `flatten()` is called with the default fields
- **THEN** the result is one string containing exactly three labeled sections in the order
  `personality`, `life_story`, `habit`, each label prefix present once

#### Scenario: An explicitly requested background flattens with its label
- **WHEN** a record contains a non-empty `background` and `flatten(("personality", "life_story",
  "habit", "background"))` is called
- **THEN** the result includes a `背景：` labeled section carrying the capped background text, in the
  requested field order

#### Scenario: Absent fields are omitted
- **WHEN** a record contains only `personality` and `habit`
- **THEN** the flattened block contains exactly two labeled sections and no placeholder or empty
  section for `life_story`

#### Scenario: Non-string fields are treated as absent
- **WHEN** a record field such as `habit` is `None`, a number, or a container rather than text
- **THEN** that field produces no section and no exception is raised; only non-empty string
  fields produce sections

#### Scenario: Missing or malformed records return None
- **WHEN** `flatten()` is called for an entity with no persona record, a non-mapping persona
  value, or a mapping with none of the requested fields
- **THEN** the result is `None` and no exception is raised

#### Scenario: Field and block caps are enforced deterministically
- **WHEN** a field string or the combined block exceeds the configured bounds
- **THEN** the result is truncated to the bound; the truncation is deterministic and never raises

## ADDED Requirements

### Requirement: The look appearance path renders a living entity's persona block
The in-game 「看」 surface (shared by the text command and the WebClient look action) SHALL append a
living entity's flattened persona block (including the `背景：` section when the record carries a
background) when the player looks at themself, at another player character, or at an NPC, using the
same code path for all three. Looking at the room or at an object SHALL NOT append any persona
block. A record without any of the rendered fields renders nothing, so entities without a persona
(e.g. monsters) are unchanged; the onboarding look beat and the displayed-stats block are
unaffected.

#### Scenario: Looking at yourself shows the persona block
- **WHEN** an active character whose persona record has content uses 「看 自己」
- **THEN** the output contains the persona block (including `背景：` when present) after the
  description and displayed-stats block

#### Scenario: Looking at another player character shows that character's persona block
- **WHEN** a player looks at another present player character whose persona record has content
- **THEN** the output contains the target's persona block (including `背景：` when present) and not
  the looker's own block

#### Scenario: Looking at an NPC shows the NPC's persona block
- **WHEN** a player looks at a present NPC whose `entity.db.persona` record has content
- **THEN** the output contains that NPC's persona block (including `背景：` when present)

#### Scenario: Looking at the room or an object omits any persona block
- **WHEN** the actor looks at the room or at an object
- **THEN** no persona block is appended to those outputs

