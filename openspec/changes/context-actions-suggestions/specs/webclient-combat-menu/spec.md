## MODIFIED Requirements

### Requirement: Combat context actions are an exact read-only panel

The production presentation registry SHALL register `context_actions` schema version 5. For a
valid active combat session, its available payload SHALL contain exactly `schema_version`,
`available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, `skills`,
and `suggestions`; `available` SHALL be true, `kind` SHALL be `combat`, and `suggestions` SHALL
be exactly `{"status": "unavailable"}`. `session` SHALL contain exactly `session_id`, `mode`,
`round`, `state`, and `reason`: session ID SHALL be bounded, mode SHALL be `hostile` or
`guild_exam`, round SHALL be a non-negative safe integer, state SHALL be `ready` or `recovery`,
and reason SHALL be null or an exact object containing stable code and safe Traditional Chinese
message. A ready session SHALL have a null reason; a recovery session SHALL have a non-null
reason, no cast/flee action, and one confirmed Forfeit descriptor when its record is strictly
parsed. The presenter SHALL strictly read and reconstruct the authenticated puppet's current
`CombatSessionRecord`, SHALL preserve persisted participant order, SHALL emit no live object or
filesystem reference, and SHALL NOT mutate traits, resources, buffs, sexual state, battlefield
state, session state, quests, location, or world time. Outside combat it SHALL use the registered
common unavailable form rather than fabricate exploration actions.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, current actions, and the exact `suggestions` object `{"status": "unavailable"}` while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet has no combat session
- **THEN** `context_actions` uses its schema-valid unavailable form and contains no Attack, skill, target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal text output remains usable

#### Scenario: Combat fields stay byte-identical across the version bump
- **WHEN** a v4-compatible combat fixture is validated by the version-5 validator and the client mirror
- **THEN** every combat field serializes exactly as it did at schema version 4, with only `schema_version` equal to 5 and the `suggestions` object added