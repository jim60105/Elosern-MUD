# webclient-quest-log-panel Specification

## Purpose
The host-independent quest-log read model — one exact read-only version-1 panel disclosing every stored record with canonical describe-seam prose, issuer and settlement disclosure, all-or-nothing degradation, bounded payloads with client mirror parity, and push timing on every quest-log mutation seam.

## Requirements
### Requirement: The quest log panel is an exact read-only version-1 presentation panel

The presentation registry SHALL register a `quest_log` panel at schema version 1. Its available form
SHALL contain exactly `schema_version`, `available`, and `rows`, where `rows` is the holder's stored
quest records in quest-log order, at most the shared `MAX_QUEST_ROWS` bound of twelve, and the
registered common unavailable form SHALL keep the shared field set, reason, and semantics.
When the holder stores more records than the cap, the panel SHALL carry the first `MAX_QUEST_ROWS`
records in stored quest-log order.

Each row SHALL contain exactly `quest_id`, `definition_key`, `display_name`, `state`, `stage_index`,
`stage_total`, `stage_progress`, `objective_quantity`, `objective_line`, `deadline_line`, `detail`,
`tracked`, `issuer`, `settlement`, `reward_line`, and `track`. `state` SHALL be one of the bounded
stored states `in_progress`, `completed`, `failed`. `issuer` SHALL contain exactly `kind` (`guild` or
`npc`), `key` (the record's stored issuer key, a grammar-valid issuer key whose namespace matches
`kind`), and `label` (the bounded display name of the commissioner). `settlement` SHALL be the
resolved issuance's settlement (`counter` or `auto`), or `null` when that issuance cannot be
resolved. `deadline_line` and `reward_line` SHALL be nullable.
`track` SHALL be the `guild.quest_track` action descriptor, always enabled.

The presenter SHALL be read-only: it SHALL NOT mutate the quest log, tracking state, inventory,
wallet, traits, or world state, and SHALL emit no live object or filesystem reference.

#### Scenario: A two-quest log serializes exactly the bounded rows
- **WHEN** a puppeted holder with two stored records receives a full snapshot
- **THEN** `quest_log.rows` carries two rows in quest-log order with the exact field set

#### Scenario: The presenter mutates nothing
- **WHEN** the panel is built twice in a row for the same holder
- **THEN** the holder's quest log, tracking flags, wallet, and inventory are byte-for-byte unchanged
  and both serializations are identical

#### Scenario: An empty log is available, not unavailable
- **WHEN** a holder with no stored records receives a snapshot
- **THEN** the panel is available with `rows: []`

### Requirement: The quest log panel is host-independent

The panel SHALL be built without resolving any service host. It SHALL NOT require a local
`GuildStaff`, a local `QuestIssuer`, a guild registration, a service schedule, or a specific room.
Its availability SHALL depend only on the holder being a puppeted character whose quest log can be
read, so the player's own quest book is readable anywhere the player stands.

#### Scenario: The log is readable far from any counter
- **WHEN** a holder with stored records stands in a wilderness room with no NPC present
- **THEN** the panel is available and carries every stored record

#### Scenario: A private commission with no counter still appears
- **WHEN** a holder carries a record whose issuer is `npc`-namespaced
- **THEN** the row is present with its issuer kind `npc` and its settlement `auto`

### Requirement: Row prose comes only from the canonical describe seams

`objective_line` SHALL be `describe_objective` for the record's current stage objective,
`deadline_line` SHALL be `describe_deadline` for the record's deadline against the current world
tick, `detail` SHALL be `describe_quest_detail`, and `reward_line` SHALL be `describe_reward` for the
resolved issuance. The presenter SHALL NOT compose, reword, truncate mid-sentence, or invent any of
these lines, so the quest book, the objective tracker, and the guild counter render byte-identical
prose for the same record.

#### Scenario: The quest book and the tracker agree
- **WHEN** the same tracked in-progress record is rendered into `quest_log` and into `objectives`
- **THEN** the objective line and the deadline line are byte-identical in both panels

#### Scenario: The quest book and the counter agree
- **WHEN** the same record is rendered into `quest_log` and into the `services` guild quest rows
  while a clerk is present
- **THEN** the objective summary, the deadline line, and the detail are byte-identical in both

### Requirement: An unresolvable issuance yields no reward line rather than a fabricated one

When a record's issuer key resolves to no registered issuance, the row SHALL carry `reward_line`
`null` and `settlement` `null`, and SHALL still render every other field. The panel SHALL NOT
fabricate a reward or settlement, substitute another issuance's reward, omit the row, or become
unavailable. The two commission fields SHALL be null together or present together, and both the
server validator and the client mirror SHALL reject a payload pairing one null with one present.

#### Scenario: A withdrawn commission still lists its quest
- **WHEN** a holder carries a record whose issuance has been unregistered
- **THEN** the row is present with `reward_line` null, `settlement` null, and every other field
  intact

#### Scenario: No reward is ever invented
- **WHEN** any row's issuance cannot be resolved
- **THEN** no copper, item, or merit figure appears anywhere in that row

### Requirement: A corrupt quest log degrades the whole panel, never a partial list

Any `QuestDataError` from the shared strict record reader SHALL make the WHOLE panel degrade to the
registry-owned common unavailable form. The panel SHALL NOT ship the records that happened to parse,
SHALL NOT skip the malformed entry, and SHALL NOT rewrite or reset the stored log.

#### Scenario: One malformed entry hides the whole panel
- **WHEN** a holder's stored quest log contains one entry the strict reader rejects
- **THEN** the panel is the common unavailable form and no row is shipped

#### Scenario: Degradation never repairs the stored log
- **WHEN** the panel degrades on a corrupt record
- **THEN** `db.quest_log` is byte-for-byte unchanged

### Requirement: The panel is bounded and closes with the shared envelope check

Every string field SHALL carry an explicit code-point bound, every integer field an explicit range,
and the row list the shared twelve-row cap. The panel SHALL close with the shared
`MAX_CANONICAL_JSON_BYTES` envelope guard and FAIL CLOSED on a violation rather than truncating, so a
producer bug surfaces as a loud failure. The client-side validator SHALL mirror these exact bounds,
guarded by the existing dual-direction parity test.

#### Scenario: An over-bound field fails closed
- **WHEN** a producer bug yields a row field exceeding its declared bound
- **THEN** the panel raises its named validation error rather than truncating or shipping the value

#### Scenario: The client mirror rejects a payload the server would not emit
- **WHEN** a payload with an extra row field, a thirteenth row, or an unknown `state` value reaches
  the client validator
- **THEN** the client rejects it rather than rendering it

### Requirement: The panel is pushed on every quest-log mutation

The coordinator SHALL mark the panel dirty and push it on the existing quest-log mutation seams —
acceptance, abandonment, tracking, stage advance, completion, and deadline settlement — so the quest
book never lags the stored record. The panel SHALL be pushed for exploration and combat puppets
alike, because a quest can complete mid-combat.

#### Scenario: Completing a quest refreshes the book
- **WHEN** a record transitions to `COMPLETED` during a committed action
- **THEN** the `quest_log` panel is pushed carrying the new state

#### Scenario: Tracking refreshes the book
- **WHEN** the holder submits `guild.quest_track`
- **THEN** the panel is pushed carrying the new `tracked` value for that row
