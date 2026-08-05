## MODIFIED Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 2. For a valid
active combat session, its available payload SHALL contain exactly `schema_version`, `available`,
`kind`, `session`, `participants`, `root_actions`, `secondary_actions`, and `skills`; `available`
SHALL be true and `kind` SHALL be `combat`. `session` SHALL contain exactly `session_id`, `mode`,
`round`, `state`, and `reason`: session ID SHALL be bounded, mode SHALL be `hostile` or
`guild_exam`, round SHALL be a non-negative safe integer, state SHALL be `ready` or `recovery`, and
reason SHALL be null or an exact object containing stable code and safe Traditional Chinese message.
A ready session SHALL have a null reason; a recovery session SHALL have a non-null reason, no
cast/flee action, and one confirmed Forfeit descriptor when its record is strictly parsed. The
presenter SHALL strictly read and reconstruct the authenticated puppet's current
`CombatSessionRecord`, SHALL preserve persisted participant order, SHALL emit no live object or
filesystem reference, and SHALL NOT mutate traits, resources, buffs, sexual state, battlefield
state, session state, quests, location, or world time. Outside combat it SHALL use the registered
common unavailable form rather than fabricate exploration actions.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, and
  current actions while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet has no combat session
- **THEN** `context_actions` uses its schema-valid unavailable form and contains no Attack, skill,
  target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal
  text output remains usable

### Requirement: Combat presentation enumerates complete deterministic choices
The combat panel SHALL list each unique owned active `SkillDef` in `SkillHandler.owned_keys()` order
after passive filtering, including innate skills, without alphabetical reordering. Each skill
descriptor SHALL contain its stable key, registry label and description, exact resource cost, target
specification, nullable element key, enabled state, nullable stable disabled reason, ordered valid
participant IDs, and applicable approved AREA shorthands. Participants SHALL be ordered from
`player_ids` then `enemy_ids` and SHALL contain a positive opaque identity, stable session token,
bounded display name, team, living/fled/knocked-out state, current/maximum HP, and a nullable
server-authored portrait reference. `portrait_ref` SHALL equal the opaque art catalog key for that
participant when the participant is present in the `webclient-art-panel` portrait catalog — including
an entry that resolves to a placeholder card — and SHALL be `null` only when the participant is
absent from that catalog. The server SHALL derive the reference from the catalog it actually builds
(character named-policy with adult gate, generic-monster bestiary archetype, or unavailable
placeholder), and the browser SHALL NOT construct a portrait subject key or URL from entity data.
Lists and strings SHALL have explicit bounds and the serialized envelope SHALL remain within the OOB
protocol limit.

#### Scenario: Stored skill order and passive exclusion are preserved
- **WHEN** a player owns active skills in the stored order `wind_blade`, `fire_ball` and also owns a
  passive skill
- **THEN** the panel lists those active skills in that order, excludes the passive, and retains
  innate active skills in their deterministic handler order

#### Scenario: Unavailable skill remains visible
- **WHEN** an owned active skill lacks resources, has no valid target, has an unavailable effect
  handler, or the actor cannot act
- **THEN** its descriptor remains focusable with `enabled: false`, one stable code, and a
  Traditional Chinese explanation derived from the rules preview

#### Scenario: Portrait reference is server-authored and nullable
- **WHEN** combat presentation is built after the art-panel change
- **THEN** each participant's `portrait_ref` equals the opaque art catalog key for that participant
  when the participant is present in the art catalog — including an entry that resolves to a
  placeholder — and is `null` only when the participant is absent from the catalog, and the browser
  never derives a subject key or URL from the participant

### Requirement: Combat results update canonical panels and preserve narrative logs
After an admitted combat action settles, the server SHALL emit every returned EventLog and terminal
message through Evennia's ordinary escaped text output path. The dispatcher SHALL then publish
canonical `status`, `context_actions`, and `art` replacements at one newer revision before sending
the matching safe `ui_action_result`, so a combat result that changes the participant roster, combat
mode, or session state replaces the portrait catalog and scene in the same `ui_update`. The browser
SHALL keep submission locked until that declared presentation revision is accepted. It SHALL NOT
parse narrative prose to update resources, participants, round, art, or menu state.

#### Scenario: One combat round updates text, panels, and art
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** every committed EventLog appears in narrative, status, combat choices, and the art catalog
  reflect committed state at one newer revision, and the dock unlocks only after that revision is
  accepted

#### Scenario: A defeated or fled participant leaves the art catalog in the same revision
- **WHEN** an accepted combat action removes a participant from the session (defeat, flee, or
  terminal settlement)
- **THEN** the `art` panel at the same newer revision no longer contains that participant's catalog
  entry, and the browser never keeps a portrait for a no-longer-present entity

#### Scenario: Rejected preflight emits no fabricated combat prose
- **WHEN** current deterministic validation rejects before initiative
- **THEN** no combat EventLog is fabricated, the result contains a stable safe reason, and refreshed
  panel state permits another legal choice

#### Scenario: Duplicate request does not repeat a round or prose
- **WHEN** one live request ID is delivered twice
- **THEN** the adapter and combat round execute once, EventLog text is emitted once, and the
  duplicate receives the cached result
