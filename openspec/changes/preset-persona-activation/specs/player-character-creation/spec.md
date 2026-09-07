# player-character-creation delta

## ADDED Requirements

### Requirement: Preset activation persists the preset's declared persona
Preset mode SHALL persist the selected preset's declared persona: activation
SHALL write `entity.db.persona` from `preset.persona.to_record()` inside the same
all-or-nothing transaction that writes identity, traits, skills, and inventory,
so a preset-created character is a persona owner from its first login exactly as
a custom-created one is. A persona write failure SHALL roll activation back
entirely, leaving the character pending with no canonical identity, trait, or
persona state written.

Both creation modes SHALL build their record through one shared helper in
`world/rules/character_creation.py`, which remains the sole writer of
creation-generated persona. The custom path's output SHALL be unchanged.

A preset-created character's persona record SHALL carry the same six
`PERSONA_IMPORT_CARD_KEYS` a custom-created character's record carries, so no
consumer — `PersonaStore`, the dialogue prompt builder, or
`world/rules/persona_edit.py` — needs a mode-dependent branch.

#### Scenario: A preset activation persists the registry persona
- **WHEN** a pending player activates a shipped preset whose registry entry declares a persona
- **THEN** `entity.db.persona` equals that preset's `to_record()` output, written atomically with the rest of the activation state

#### Scenario: Both modes produce the same record key set
- **WHEN** a preset activation and a custom activation are compared
- **THEN** both records carry exactly the six `PERSONA_IMPORT_CARD_KEYS`, with `background` present in each only when that source supplied one

#### Scenario: A preset persona write failure rolls activation back
- **WHEN** a write failure is injected into the persona step of a preset activation
- **THEN** activation rolls back entirely, the character remains pending, and no identity, trait, skill, inventory, or persona state survives

#### Scenario: A preset character reaches the dialogue persona surface
- **WHEN** an NPC builds its dialogue context for a preset-created character
- **THEN** the player persona block resolves from the written record instead of being absent

#### Scenario: Custom activation output is unchanged
- **WHEN** a custom draft carrying a persona block and a background activates
- **THEN** the persisted record is identical to the record produced before the shared builder was introduced
