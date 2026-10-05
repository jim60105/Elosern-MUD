## MODIFIED Requirements

### Requirement: Board acceptance and abandonment delegate to quest lifecycle
`accept_guild_offer()` SHALL validate board eligibility and then invoke change 15's `accept_quest()` for
the offer's definition, naming the issuing branch as the issuer key in the canonical
`guild:<branch_key>` form derived from the resolved `GuildStaff` host's `branch_key`. The guild layer
SHALL NOT construct that key by string concatenation; it SHALL use the shared issuer-key
constructor, so the board path and the read seam can never disagree about the key's spelling. A
successful acceptance SHALL additionally grant +1 affinity (`guild` source)
with the issuing GuildStaff host through the sole-writer affinity API (`world/rules/affinity.py`),
committed in one all-or-nothing operation with the quest record creation: the acceptance SHALL
snapshot the actor's quest-log surface plus the host's affinity record (acceptance creates no
instance pins — stage binding happens only on stage advance), apply the quest
record and the gain inside one transaction, and restore every surface on failure so a failed
affinity write rolls back the acceptance; abandonment SHALL grant no affinity.
When `accept_quest()` refuses a species-hunt offer because the hunt cannot be legally satisfied (the
target-availability guarantee fails), the board path SHALL surface that named refusal as an ordinary
rejection — no quest record, no affinity gain, no partial provisioning left behind.
`abandon_guild_quest()` SHALL invoke `abandon_quest()` for the exact quest ID.
The guild layer SHALL NOT construct, mutate, or reinterpret quest-record dicts itself.

#### Scenario: Eligible offer creates a normal quest record
- **WHEN** a registered member accepts a visible offer
- **THEN** the resulting record is exactly the record `accept_quest()` creates, its issuer key is
  `guild:<the issuing host's branch key>`, no reward is paid, and the issuing host's affinity value
  rises by 1

#### Scenario: Over-rank acceptance is rejected before quest mutation
- **WHEN** an F member directly names an E offer key
- **THEN** no quest record is created and no affinity is granted

#### Scenario: A failed acceptance restores every surface
- **WHEN** persistence is fault-injected after the quest record is written and before the
  affinity gain commits
- **THEN** the quest log and the host's affinity record — and their in-process caches — equal
  their pre-acceptance values

#### Scenario: A legally unsatisfiable hunt offer is refused cleanly
- **WHEN** a member accepts a species-hunt offer whose ordinary-eligible target guarantee cannot be met
- **THEN** the refusal names the reason, and the quest log, affinity record, and every individual owned by the ambient/site managers equal their pre-acceptance values

#### Scenario: Abandonment preserves quest-runtime semantics
- **WHEN** a member abandons an active offered quest
- **THEN** the quest runtime records `FAILED` with reason `abandoned`, the guild layer adds no second
  abandonment state, and no affinity is granted

#### Scenario: Two branches offering one definition produce distinguishable records
- **WHEN** the same definition is accepted at one branch, completed, and later accepted at a second
  branch offering it
- **THEN** the two records carry that branch's own issuer key, and each resolves to its own branch's
  registered reward

### Requirement: Board listing and quest log surface objective guidance
`guild list` SHALL render each eligible offer with a one-line Traditional
Chinese summary of the offered definition's first objective, in addition to the
existing key, display name, and reward; a regional species hunt SHALL render as one
deterministic line naming the region, species, and count. `guild log` SHALL render a hint that
`guild show <quest_id>` reveals full objective detail. Both SHALL be read-only
presentation over existing registries and records, and SHALL NOT change board
eligibility or quest state.

#### Scenario: Board rows show a first-objective one-liner
- **WHEN** an F member lists a board containing the `introductory_hunt` offer
- **THEN** the row shows the offered definition's first objective summary (for
  example a DEFEAT goal) alongside the name and reward

#### Scenario: A species-hunt offer renders its one-liner
- **WHEN** a board contains a species-hunt offer
- **THEN** its row shows region, species, and required count in one deterministic Traditional Chinese line

#### Scenario: Quest log hints at the detail command
- **WHEN** a player with at least one quest record runs `guild log`
- **THEN** the output points the player to `guild show` for full objective
  detail

#### Scenario: Objective summaries never affect eligibility
- **WHEN** a board is listed with objective summaries enabled
- **THEN** rank-eligible filtering and ordering are byte-for-byte identical to
  the behavior without summaries
