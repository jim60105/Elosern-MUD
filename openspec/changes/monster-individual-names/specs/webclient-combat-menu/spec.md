## ADDED Requirements

### Requirement: The combat target prompt shows the focused monster's variant
The target prompt SHALL show a focused monster's name with a variant tag derived by the client from `monster_identity`: the variant name for an unnamed individual, and the variant name followed by the species name for a named one. A participant without `monster_identity` SHALL show no tag.

#### Scenario: Unnamed foe
- **WHEN** the stage target step focuses a synthetic foe with a species name, a variant name and no individual name
- **THEN** the prompt shows the species name with a tag holding the variant name

#### Scenario: Named foe
- **WHEN** the step focuses a synthetic foe with an individual name
- **THEN** the prompt shows the individual name with a tag holding the variant name followed by the species name

#### Scenario: Participant without identity
- **WHEN** the step focuses a party member, or a monster whose identity is null
- **THEN** the prompt shows its name with no variant tag

### Requirement: A figure plate marks a named individual without moving
A plate whose participant has an individual name SHALL show that name in the gold display treatment with a hairline along the plate's top. The plate SHALL keep the size and line positions of an unnamed plate, keep its single crown at rest, and use no selection cue. Its accessible name and title SHALL include the variant tag.

#### Scenario: Named and unnamed plates share geometry
- **WHEN** a named and an unnamed plate render at one form
- **THEN** their slot, name line and stroke positions and sizes are equal, and the name's rendered text is complete

#### Scenario: Plate states still read
- **WHEN** a named plate is the focused target, is acting, or is fallen
- **THEN** it keeps that state's existing cue together with the named treatment

## MODIFIED Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 8.
For a valid active combat session, its available payload SHALL contain exactly
`schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`,
`secondary_actions`, `actors`, `choices`, `draft`, and `suggestions`; `available` SHALL be true, `kind`
SHALL be `combat`, and `suggestions` SHALL be exactly `{"status": "unavailable"}`. Every participant SHALL carry a required `monster_identity` field that is null or exactly `individual_name`, `species_name` and `variant_name`.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, current actions, and the exact `suggestions` object `{"status": "unavailable"}` while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet is in exploration mode
- **THEN** `context_actions` emits the exploration available form and contains no Attack, skill, target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal text output remains usable

#### Scenario: Combat fields never leak outside a combat session
- **WHEN** the active puppet is in exploration mode or creation-pending
- **THEN** `context_actions` contains no `session`, `participants`, `root_actions`,
  `secondary_actions`, `actors`, `choices`, or `draft` field — the exploration available form (exploration mode) or
  the shared unavailable form is emitted instead

#### Scenario: Combat fields stay byte-identical across the version bump
- **WHEN** a v7 party-command fixture is validated by the server and client mirror
- **THEN** the exact v7 actor/choices/draft shape is accepted, v6 conditions and polarity remain present, and old-version or puppet-level skills payloads reject

#### Scenario: Absent location emits the shared unavailable form
- **WHEN** the puppet has an absent location
- **THEN** `context_actions` emits the registered common unavailable form and never
  fabricates combat-shaped fields

#### Scenario: The exploration form belongs to the context-actions capability
- **WHEN** `context_actions` emits the exploration available form in exploration mode
- **THEN** that form is the one owned by the `webclient-context-actions` capability

#### Scenario: Session fields are exact and constrained
- **WHEN** a combat `context_actions` payload is validated
- **THEN** `session` contains exactly `session_id`, `mode`, `round`, `round_revision`, `state`, and
  `reason`: session ID is bounded, mode is `hostile` or `guild_exam`, round is a
  non-negative safe integer, round_revision is a non-negative safe integer equal to the nonnull draft revision, state is `ready` or `recovery`, and reason is null or an
  exact object containing a stable code and a safe Traditional Chinese message

#### Scenario: Ready and recovery sessions carry consistent reason and actions
- **WHEN** a session record is strictly parsed
- **THEN** a ready session has a null reason, and a recovery session has a non-null
  reason, no personal round action, and one confirmed party surrender descriptor

#### Scenario: The presenter only reads and reconstructs the session record
- **WHEN** combat presentation is built
- **THEN** the presenter strictly reads and reconstructs the authenticated puppet's
  current `CombatSessionRecord`, preserves persisted participant order, emits no live
  object or filesystem reference, and mutates no traits, resources, buffs, sexual
  state, battlefield state, session state, quests, location, or world time

#### Scenario: Exploration actions are never fabricated in a combat session
- **WHEN** a valid active combat session renders `context_actions`
- **THEN** the panel never fabricates exploration actions alongside the combat form

#### Scenario: Version 6 adds read-only facts only
- **WHEN** the combat available form is serialized at version 6
- **THEN** its top-level field set is unchanged from version 5, every participant additionally carries `conditions`, every skill descriptor additionally carries `hostile` and `beneficial`, the presenter stays read-only, and the exploration and unavailable forms differ from version 5 only in `schema_version`

#### Scenario: Version 7 adds authoritative party facts
- **WHEN** the combat available form is serialized at version 7
- **THEN** it carries bounded actor summaries, one actor-scoped choices object and durable draft progress, retains participant conditions and skill polarity, stays read-only, and changes exploration/unavailable forms only in schema_version

#### Scenario: Version 8 adds monster identity facts
- **WHEN** the combat available form is serialized at version 8
- **THEN** its top-level field set is unchanged from version 7, every participant additionally carries `monster_identity`, the presenter stays read-only, and the exploration and unavailable forms differ from version 7 only in `schema_version`
