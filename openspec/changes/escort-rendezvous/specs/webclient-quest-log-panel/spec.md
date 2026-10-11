# Spec Delta

## MODIFIED Requirements

### Requirement: The quest log panel is an exact read-only version-2 presentation panel
The version-2 quest_log panel SHALL retain its exact envelope, ordered twelve-row bound, read-only ownership, existing canonical row fields and bounds. Rows SHALL additionally carry nullable terminal_reason and abandon fields. State SHALL include invalidated; its reason SHALL be a bounded code/message object, its track descriptor disabled, and its abandon null. Active owned private escorts SHALL carry host-independent abandonment descriptors; ordinary counter descriptors remain service-owned.

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
- **THEN** the existing exact row field set is retained with terminal_reason and abandon added; terminal_reason is null or exactly code/message under shared reason bounds, and abandon is null or a bounded existing action descriptor for guild.quest_abandon with quest_id

#### Scenario: State is bounded to the stored states
- **WHEN** a row state is serialized or validated
- **THEN** server and client mirrors accept exactly in_progress, completed, failed and invalidated and reject unknown states

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
- **WHEN** nullable prose/reward/action fields are serialized
- **THEN** existing nullable prose fields remain; track retains guild.quest_track with invalidated records disabled as quest_terminal, and abandon is present only for active owned private escorts eligible for host-independent abandonment

#### Scenario: Private escort abandonment works without a guild host
- **WHEN** an active owned private escort appears in the quest book away from any issuer or guild staff
- **THEN** its enabled abandon descriptor targets its exact quest ID, while an invalidated row shows its reason and no enabled tracking, abandonment or payout

### Requirement: The panel is pushed on every quest-log mutation
The existing acceptance, abandonment, tracking, stage, completion and deadline push seams SHALL also refresh after committed invalidation and escort source/offer changes. Exploration and combat views SHALL use only committed records and reason/action descriptors. Rollback SHALL emit no success view.

#### Scenario: Completing a quest refreshes the book
- **WHEN** a record transitions to `COMPLETED` during a committed action
- **THEN** the `quest_log` panel is pushed carrying the new state

#### Scenario: Tracking refreshes the book
- **WHEN** the holder submits `guild.quest_track`
- **THEN** the panel is pushed carrying the new `tracked` value for that row

#### Scenario: Invalidation refreshes open quest history
- **WHEN** exclusive resolution invalidates a visible accepted alternative
- **THEN** the next committed quest_log update shows invalidated and its reason, with no stale active controls
