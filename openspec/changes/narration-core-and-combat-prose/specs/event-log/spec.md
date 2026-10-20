# Spec Delta

## ADDED Requirements

### Requirement: Entry text is authored narration while the payload keeps exact numbers

An `EventEntry`'s `text_template` SHALL carry the authored narration line selected when the
entry was built, and rendering it SHALL remain a pure format of that entry's own
`actor`/`target`/`data` fields. The entry's `kind`, `actor`, `target` and every `data` value
SHALL be unchanged by narration, so serialization, replay and structured consumers observe
exactly the numbers the resolver recorded.

#### Scenario: The line hides the amount and the data keeps it

- **WHEN** a `damage` entry records `{"amount": 450698}` and is rendered
- **THEN** the rendered line contains no digit and `entry.data["amount"]` is still 450698

#### Scenario: Rendering stays a pure, repeatable format

- **WHEN** the same entry is rendered twice through the entry-text renderer
- **THEN** both calls return byte-identical strings and neither mutates the entry or the log

#### Scenario: A payload-free consumer still sees the exact record

- **WHEN** a settled log is serialized and re-read
- **THEN** every entry's `kind`, participants and `data` values are identical to the values
  present before rendering

### Requirement: Internal-only entry kinds keep rendering nothing

Entry kinds that exist only to carry a structured fact and intentionally render an empty line
SHALL continue to render an empty line under narration, so their presence in a log does not
introduce a blank prose line where the text channel previously printed none.

#### Scenario: A kill-experience entry adds no blank line

- **WHEN** a log contains a `combat_kill_xp` entry and the log is rendered as plain text
- **THEN** that entry contributes no non-empty line and the surrounding lines keep their order
