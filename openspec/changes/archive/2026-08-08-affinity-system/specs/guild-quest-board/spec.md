## MODIFIED Requirements

### Requirement: Board acceptance and abandonment delegate to quest lifecycle
`accept_guild_offer()` SHALL validate board eligibility and then invoke change 15's `accept_quest()` for
the offer's definition. A successful acceptance SHALL additionally grant +1 affinity (`guild` source)
with the issuing GuildStaff host through the sole-writer affinity API (`world/rules/affinity.py`),
committed in one all-or-nothing operation with the quest record creation: the acceptance SHALL
snapshot the actor's quest-log surface plus the host's affinity record (acceptance creates no
instance pins — stage binding happens only on stage advance), apply the quest
record and the gain inside one transaction, and restore every surface on failure so a failed
affinity write rolls back the acceptance; abandonment SHALL grant no affinity.
`abandon_guild_quest()` SHALL invoke `abandon_quest()` for the exact quest ID.
The guild layer SHALL NOT construct, mutate, or reinterpret quest-record dicts itself.

#### Scenario: Eligible offer creates a normal quest record
- **WHEN** a registered member accepts a visible offer
- **THEN** the resulting record is exactly the record `accept_quest()` creates, no reward is paid,
  and the issuing host's affinity value rises by 1

#### Scenario: Over-rank acceptance is rejected before quest mutation
- **WHEN** an F member directly names an E offer key
- **THEN** no quest record is created and no affinity is granted

#### Scenario: A failed acceptance restores every surface
- **WHEN** persistence is fault-injected after the quest record is written and before the
  affinity gain commits
- **THEN** the quest log and the host's affinity record — and their in-process caches — equal
  their pre-acceptance values

#### Scenario: Abandonment preserves quest-runtime semantics
- **WHEN** a member abandons an active offered quest
- **THEN** the quest runtime records `FAILED` with reason `abandoned`, the guild layer adds no second
  abandonment state, and no affinity is granted
