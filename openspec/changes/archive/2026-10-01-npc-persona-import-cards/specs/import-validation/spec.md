## ADDED Requirements

### Requirement: NPC-target imports validate a complete compact card
When the class a character record is validated and instantiated against is an NPC class (the NPC default when no class is given), import validation SHALL apply the compact NPC card contract to the record's `persona` and SHALL reject any contract violation as a named issue on `persona` or `persona.<leaf>` carrying the contract's stable reason, within the existing all-or-nothing batch. The discriminator SHALL be the resolved class passed to validation and instantiation, never a field claimed inside the record. A valid NPC-target record SHALL carry the normalized card as its validated persona. A non-NPC target SHALL keep the opaque object rule and SHALL NOT be inspected.

#### Scenario: An NPC import with a partial persona is rejected by leaf
- **WHEN** a record without `speech_style` is validated with the NPC default target
- **THEN** the report rejects it with an issue on `persona.speech_style` and the batch loads nothing

#### Scenario: An NPC import with a background key is rejected
- **WHEN** an NPC-target record's persona carries a `background` key
- **THEN** the report rejects it with an `unknown_field` issue on `persona.background`

#### Scenario: A player-target import keeps an opaque persona
- **WHEN** a record whose persona has arbitrary nested structure and a `background` key is validated against `PlayerCharacter`
- **THEN** no persona issue is reported

#### Scenario: The validated record carries the normalized card
- **WHEN** an NPC-target record's persona leaves carry outer whitespace and CRLF line endings
- **THEN** the validated record's persona holds the normalized leaves
