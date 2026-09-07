# creation-persona-persistence delta

## MODIFIED Requirements

### Requirement: Activation persists the persona block in the import-card shape
`activate_player_character()` SHALL persist a persona record for both creation modes through one shared record builder in `world/rules/character_creation.py`, written inside the same all-or-nothing activation transaction; a persona write failure SHALL roll back activation in either mode. In custom mode, when the draft carries a non-null persona block, the written `entity.db.persona` SHALL be a dict with the import-card keys (identity/personality/life_story/habit/appearance/social_connection), the block filling the three prose fields and the remaining keys stored as empty containers, and a custom draft with a null persona SHALL write nothing beyond the background rule below. The persona block SHALL be read from the custom draft — no concept-stage state exists to consult. When the draft carries a player-authored bounded background field, the same activation transaction SHALL additionally store that text under the persona record's `background` key (kept separate from the three prose fields), so a custom character's background survives activation; a draft without a background SHALL omit the key. In preset mode, the record SHALL come from the selected preset's declared persona and SHALL carry the same six import-card keys, so no downstream consumer needs a mode-dependent branch. `world/rules/character_creation.py` SHALL be the sole writer of creation-generated persona; `world/imports/loader.py` remains the import-time writer and is unchanged.

#### Scenario: A custom draft persists its persona at activation
- **WHEN** a pending character activates with a custom draft carrying a non-null persona block
- **THEN** `entity.db.persona` contains the six-key import-card dict with the block's three prose fields and empty containers for the rest, activation commits, and the character is an active persona owner

#### Scenario: A custom background is persisted inside the persona record
- **WHEN** a pending character activates with a custom draft carrying a non-empty bounded `background`
- **THEN** `entity.db.persona` contains the six import-card keys plus a `background` key holding the exact accepted text, activation commits, and the character is an active persona owner

#### Scenario: A persona write failure rolls back activation
- **WHEN** a write failure is injected into the persona-persistence step of the activation transaction
- **THEN** activation rolls back entirely, the character remains pending, and no canonical identity, trait, or persona state is written

#### Scenario: A custom draft without persona or background writes nothing
- **WHEN** a pending character activates with a custom draft whose persona is null and that has no background
- **THEN** `entity.db.persona` remains absent and activation behaves exactly as before

#### Scenario: A preset draft persists the registry persona
- **WHEN** a pending character activates with a preset draft
- **THEN** `entity.db.persona` is written from the preset's declared persona with the same six import-card keys, inside the same all-or-nothing transaction
