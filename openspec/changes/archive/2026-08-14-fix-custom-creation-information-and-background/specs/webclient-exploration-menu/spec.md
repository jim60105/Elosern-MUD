## RENAMED Requirements

- FROM: `### Requirement: The character panel is an exact read-only version-1 panel`
- TO: `### Requirement: The character panel is an exact read-only version-2 panel`

## MODIFIED Requirements

### Requirement: The character panel is an exact read-only version-2 panel
The production presentation registry SHALL register panel name `character` at schema version 2. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `traits`, `passives`, `equipment`, `disguise`, `guild`, `wallet`, and `persona`; `available` SHALL be true and `kind` SHALL be `character`. `traits` SHALL be a bounded list of at most 32 rows, each containing exactly `key`, `label`, `current`, and nullable `max`, derived from canonical trait values (gauges report current and maximum; static traits report the base value). `passives` SHALL be a bounded list of at most 32 passive skill keys with bounded labels from the skill registry. `equipment` SHALL be a bounded list of at most 32 rows, each with exactly `slot`, `item_key`, and bounded `display_name`, derived from canonical equipment state. `disguise` SHALL contain exactly `active` (boolean), `description` (bounded string), and a bounded list of at most 32 `displayed` rows, each with exactly `key`, `label`, and `value`, describing the outwardly displayed values when `disguise_active` is true and empty otherwise; it SHALL NEVER substitute disguised values for true traits. `guild` SHALL contain exactly `rank` (nullable rank key) and `merit` (non-negative safe integer). `wallet` SHALL be a non-negative safe integer of copper. `persona` SHALL contain exactly `background` (a nullable bounded string from the character's persona record, omitted content rendered as `null`); the section is display-only and is never used to infer any mechanical value. The presenter SHALL strictly read canonical records and registries through the no-mutation status/service read models — sharing the same canonical trait/equipment/disguise source the compact `status` panel builds from, so the two panels never diverge — SHALL emit no live object reference, SHALL NOT mutate traits, equipment, disguise, guild, wallet, persona, or world time, and SHALL use the common unavailable form outside exploration mode.

#### Scenario: Expanded state shows true values and an honest disguise
- **WHEN** an elf with active disguise opens the Character root
- **THEN** `traits` report the true values, `disguise` lists the displayed values with `active == true`, and no trait row substitutes a disguised value for a true one

#### Scenario: Undisguised actor has an empty displayed list
- **WHEN** an actor has no active disguise
- **THEN** `disguise.active` is false, `displayed` is empty, and the panel still reports true traits, passives, equipment, guild rank, wallet, and the persona background

#### Scenario: The panel reports the player's own background
- **WHEN** an active character's persona record carries a non-empty `background`
- **THEN** `persona.background` equals that text verbatim and the panel renders it as a display-only row

#### Scenario: A character without a background reports null
- **WHEN** an active character has no persona record or no background key
- **THEN** `persona.background` is `null` and no placeholder text is rendered

#### Scenario: Character panel stays read-only
- **WHEN** the character panel is built for a fully-progressed actor
- **THEN** traits, equipment, disguise, guild, wallet, persona, and world time are byte-for-byte unchanged
