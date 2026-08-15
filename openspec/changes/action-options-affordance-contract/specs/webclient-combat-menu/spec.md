## Purpose

Delta for `webclient-combat-menu`: `context_actions` is registered at schema version 4 while the
combat available form keeps its exact version-3 fields and semantics. The combat presenter now
emits the combat form only inside an active combat session; outside combat the panel emits the
exploration available form (or the shared unavailable form), never combat-shaped fields.

## MODIFIED Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 4. For a
valid active combat session, its available payload SHALL contain exactly `schema_version`,
`available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, and
`skills`; `available` SHALL be true and `kind` SHALL be `combat`. `session` SHALL contain exactly
`session_id`, `mode`, `round`, `state`, and `reason`: session ID SHALL be bounded, mode SHALL be
`hostile` or `guild_exam`, round SHALL be a non-negative safe integer, state SHALL be `ready` or
`recovery`, and reason SHALL be null or an exact object containing stable code and safe
Traditional Chinese message. A ready session SHALL have a null reason; a recovery session SHALL
have a non-null reason, no cast/flee action, and one confirmed Forfeit descriptor when its record
is strictly parsed. The presenter SHALL strictly read and reconstruct the authenticated puppet's
current `CombatSessionRecord`, SHALL preserve persisted participant order, SHALL emit no live
object or filesystem reference, and SHALL NOT mutate traits, resources, buffs, sexual state,
battlefield state, session state, quests, location, or world time. **Outside a valid active
combat session the combat form SHALL never be emitted** — the panel instead emits the exploration
available form owned by the `webclient-context-actions` capability (in exploration mode) or the
registered common unavailable form (creation-pending or absent location); it SHALL never fabricate
combat-shaped fields, and it SHALL never fabricate exploration actions in a combat session.

**Reason:** The new exploration available form (`webclient-context-actions`) extends the panel to
two kinds at schema version 4 while the combat form stays byte-identical to version 3; the
"rather than fabricate exploration actions" clause is superseded because exploration actions now
have a sanctioned form.

**Migration:** No released users; clients revalidate against the version-4 mirror
(`PANEL_ALLOWLIST.context_actions = 4`) shipped in the same change as the server validator.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, and
  current actions while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet is in exploration mode
- **THEN** `context_actions` emits the exploration available form and contains no Attack, skill,
  target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal
  text output remains usable

#### Scenario: Combat fields never leak outside a combat session
- **WHEN** the active puppet is in exploration mode or creation-pending
- **THEN** `context_actions` contains no `session`, `participants`, `root_actions`,
  `secondary_actions`, or `skills` field — the exploration available form (exploration mode) or
  the shared unavailable form is emitted instead

#### Scenario: The combat form validates exactly as version 3
- **WHEN** a ready-session combat fixture and a recovery-session combat fixture are validated at
  schema version 4
- **THEN** every field serializes byte-identically to version 3, the ready/recovery action
  contracts hold, and only `schema_version` is 4