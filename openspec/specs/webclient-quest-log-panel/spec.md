# webclient-quest-log-panel Specification

## Purpose
The host-independent quest-log read model — one exact read-only version-1 panel disclosing every stored record with canonical describe-seam prose, issuer and settlement disclosure, all-or-nothing degradation, bounded payloads with client mirror parity, and push timing on every quest-log mutation seam.

## Requirements

### Requirement: The quest log panel is an exact read-only version-2 presentation panel

The presentation registry SHALL register a `quest_log` panel at schema version 2. Its available form SHALL contain exactly `schema_version`, `available`, and `rows`, where `rows` is the holder's stored quest records in quest-log order, at most the shared `MAX_QUEST_ROWS` bound of twelve. The presenter SHALL be read-only: it SHALL NOT mutate the quest log, tracking state, reward claims, inventory, wallet, traits, or world state, and SHALL emit no live object or filesystem reference.

#### Scenario: A two-quest log serializes exactly the bounded rows
- **WHEN** a puppeted holder with two stored records receives a full snapshot
- **THEN** `quest_log.rows` carries two rows in quest-log order with the exact field set

#### Scenario: The presenter mutates nothing
- **WHEN** the panel is built twice in a row for the same holder
- **THEN** the holder's quest log, tracking flags, reward claims, wallet, and inventory are byte-for-byte unchanged
  and both serializations are identical

#### Scenario: An empty log is available, not unavailable
- **WHEN** a holder with no stored records receives a snapshot
- **THEN** the panel is available with `rows: []`

#### Scenario: The common unavailable form is the shared one
- **WHEN** the registered common unavailable form for this panel is inspected
- **THEN** it keeps the shared field set, reason, and semantics

#### Scenario: An over-cap log carries the first twelve records
- **WHEN** the holder stores more records than the cap
- **THEN** the panel carries the first `MAX_QUEST_ROWS` records in stored quest-log order

#### Scenario: The exact row field set
- **WHEN** any row is serialized
- **THEN** it contains exactly `quest_id`, `definition_key`, `display_name`, `state`, `category`, `grade`, `stage_index`, `stage_total`, `stage_progress`, `objective_quantity`, `objective_line`, `objective_note`, `deadline_line`, `rationale`, `flavor`, `tracked`, `issuer`, `settlement`, `reward`, `reward_claimed`, and `track`, and it contains no `detail` and no `reward_line`

#### Scenario: State is bounded to the stored states
- **WHEN** a row's `state` is serialized
- **THEN** it is one of the bounded stored states `in_progress`, `completed`, `failed`

#### Scenario: Category is a closed stable wire vocabulary
- **WHEN** a row's `category` is serialized
- **THEN** it is one of `gather`, `defeat`, `escort`, `explore`, `emergency`, naming the definition's quest type by a stable key rather than its display label

#### Scenario: Grade is the definition's authored guild rank key
- **WHEN** a row's `grade` is serialized
- **THEN** it is the definition's authored rank key, a non-empty string of at most eight characters, and it is never derived from a targeted individual's danger grade

#### Scenario: The issuer sub-object's exact shape
- **WHEN** a row's `issuer` is serialized
- **THEN** it contains exactly `kind` (`guild` or `npc`), `key` (the record's stored issuer key, a grammar-valid issuer key whose namespace matches `kind`), and `label` (the bounded display name of the commissioner)

#### Scenario: Settlement reflects the resolved issuance
- **WHEN** a row's `settlement` is serialized
- **THEN** it is the resolved issuance's settlement (`counter` or `auto`), or `null` when that issuance cannot be resolved

#### Scenario: The reward object's exact shape
- **WHEN** a row's `reward` is present
- **THEN** it contains exactly `copper` and `merit` (non-negative safe integers) and `items`, a list of at most one entry in the issuance's declared order, each containing exactly `item_key`, `display_name`, and a positive safe-integer `quantity`

#### Scenario: Nullable lines and the always-enabled track descriptor
- **WHEN** a row's `objective_note`, `deadline_line`, `rationale`, `flavor`, `reward`, and `track` are serialized
- **THEN** the first five are nullable, and `track` is the `guild.quest_track` action descriptor, always enabled

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

`objective_line` and `objective_note` SHALL be the canonical objective describe seam's line and note for the record's current objective, composing to `describe_objective` byte for byte as `objective_line（objective_note）`. `deadline_line` SHALL be `describe_deadline` against the current world tick; `rationale` and `flavor` SHALL be the definition's authored rationale and flavor verbatim, or null when absent; `reward` SHALL be the resolved issuance's reward with registry item display names.

#### Scenario: The quest book and the tracker agree
- **WHEN** the same tracked in-progress record is rendered into `quest_log` and into `objectives`
- **THEN** the composed objective line and the deadline line are byte-identical in both panels

#### Scenario: The quest book and the counter agree
- **WHEN** the same record is rendered into `quest_log` and into the `services` guild quest rows
  while a clerk is present
- **THEN** the composed objective line equals the counter row's objective summary and the deadline lines are byte-identical

#### Scenario: A species hunt splits its variant clause into the note
- **WHEN** a record's current objective is a regional species hunt
- **THEN** `objective_line` names the region, quantity, and species, and `objective_note` carries the counted-variant clause without the surrounding full-width brackets

#### Scenario: Other objectives carry no note
- **WHEN** a record's current objective is not a regional species hunt
- **THEN** `objective_note` is null and `objective_line` equals `describe_objective`

#### Scenario: Authored prose is shipped verbatim
- **WHEN** a definition carries a rating rationale and a background flavor
- **THEN** `rationale` and `flavor` equal those authored strings exactly, and a definition without them yields null for each

#### Scenario: All three surfaces render identical prose
- **WHEN** the same record is rendered by the quest book, the objective tracker, and the guild counter
- **THEN** the quest book's composed objective line and its deadline line are byte-identical to the prose the other two surfaces render for that record

#### Scenario: The presenter never composes or alters prose
- **WHEN** any of these fields is rendered
- **THEN** the presenter does not compose, reword, prefix, truncate mid-sentence, or invent any of them

### Requirement: An unresolvable issuance yields no reward rather than a fabricated one

When a record's issuer key resolves to no registered issuance, the row SHALL carry `reward`
`null` and `settlement` `null`, and SHALL still render every other field. The panel SHALL NOT
fabricate a reward or settlement, substitute another issuance's reward, omit the row, or become
unavailable. The two commission fields SHALL be null together or present together, and both the
server validator and the client mirror SHALL reject a payload pairing one null with one present.

#### Scenario: A withdrawn commission still lists its quest
- **WHEN** a holder carries a record whose issuance has been unregistered
- **THEN** the row is present with `reward` null, `settlement` null, and every other field
  intact

#### Scenario: No reward is ever invented
- **WHEN** any row's issuance cannot be resolved
- **THEN** no copper, item, or merit figure appears anywhere in that row

#### Scenario: A mismatched commission pair is rejected
- **WHEN** a payload row carries a present `settlement` with a null `reward`, or the reverse
- **THEN** both the server validator and the client mirror reject it

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

### Requirement: Each row discloses whether its reward has been claimed

Each row SHALL carry `reward_claimed`: whether the row's quest ID is present in the holder's canonical reward claims, read without mutation through the same strict reader the guild counter uses. Counter turn-in and automatic settlement append to that same claims ledger, so the quest book can tell a claimed reward from a pending one while standing away from any counter. Unreadable claims storage SHALL degrade the whole panel to the common unavailable form, never a guessed value.

#### Scenario: A completed counter quest awaiting turn-in is unclaimed
- **WHEN** a holder carries a completed record whose settlement is `counter` and whose quest ID is absent from the reward claims
- **THEN** the row's `reward_claimed` is false

#### Scenario: A turned-in counter quest is claimed
- **WHEN** the same quest ID has been recorded in the holder's reward claims
- **THEN** the row's `reward_claimed` is true, and it stays true when the panel is built away from any clerk

#### Scenario: A completed private commission reports its automatic settlement
- **WHEN** a holder completes a record whose settlement is `auto` and the completing transaction records its claim
- **THEN** the row's `reward_claimed` is true

#### Scenario: Malformed claims degrade the whole panel
- **WHEN** the holder's stored reward claims fail the strict reader
- **THEN** the panel is the common unavailable form and the stored claims are unchanged

#### Scenario: An in-progress quest is not claimed
- **WHEN** a holder carries an in-progress record
- **THEN** the row's `reward_claimed` is false

#### Scenario: Claim disclosure is host-independent
- **WHEN** the panel is built in a room with no service host
- **THEN** `reward_claimed` is computed exactly as in front of a clerk, and no host is resolved to compute it
