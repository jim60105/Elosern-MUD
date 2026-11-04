# Spec Delta

## MODIFIED Requirements

### Requirement: Board acceptance and abandonment delegate to quest lifecycle
`accept_guild_offer()` SHALL validate board eligibility and then invoke change 15's `accept_quest()` for
the offer's definition, naming the issuing branch as the issuer key in the canonical
`guild:<branch_key>` form derived from the resolved `GuildStaff` host's `branch_key`.
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

#### Scenario: A legally unsatisfiable clear-out offer is refused cleanly
- **WHEN** a member accepts a bound clear-out whose site can no longer supply its living individuals
- **THEN** the refusal names the site-cleared or site-short reason, no quest record and no affinity gain exist, and the site's durable state and its individuals are unchanged

#### Scenario: A state change between listing and acceptance is reported by name
- **WHEN** a site's individuals are defeated after the board was listed and the member then accepts the now-unsatisfiable offer from that listing or by naming its key directly
- **THEN** the lifecycle's named refusal reaches the member, and the board precheck does not present it as an unknown or ineligible offer

#### Scenario: Abandonment preserves quest-runtime semantics
- **WHEN** a member abandons an active offered quest
- **THEN** the quest runtime records `FAILED` with reason `abandoned`, the guild layer adds no second
  abandonment state, and no affinity is granted

#### Scenario: Two branches offering one definition produce distinguishable records
- **WHEN** the same definition is accepted at one branch, completed, and later accepted at a second
  branch offering it
- **THEN** the two records carry that branch's own issuer key, and each resolves to its own branch's
  registered reward

#### Scenario: The issuer key comes from the shared constructor, never concatenation
- **WHEN** the guild layer builds the `guild:<branch_key>` issuer key
- **THEN** it SHALL NOT use string concatenation but the shared issuer-key constructor, so the board path and the read seam can never disagree about the key's spelling

#### Scenario: Acceptance grants its affinity gain through the sole-writer API atomically
- **WHEN** an offer acceptance succeeds
- **THEN** it additionally grants +1 affinity (`guild` source) with the issuing GuildStaff host through the sole-writer affinity API (`world/rules/affinity.py`), committed in one all-or-nothing operation with the quest record creation
- **AND** the acceptance snapshots the actor's quest-log surface plus the host's affinity record, applies the quest record and the gain inside one transaction, and restores every surface on failure so a failed affinity write rolls back the acceptance

#### Scenario: Acceptance creates no instance pins
- **WHEN** an offer is accepted
- **THEN** acceptance creates no instance pins — a stage's instance binding is made at stage advance, and a site clear-out's stage-zero target binding is made at acceptance without an instance pin

#### Scenario: Abandonment grants no affinity
- **WHEN** an offered quest is abandoned through the guild layer
- **THEN** no affinity is granted

#### Scenario: An unsatisfiable hunt refusal is surfaced by name with nothing left behind
- **WHEN** `accept_quest()` refuses an offer because a bound clear-out's site cannot supply its standing bound individuals
- **THEN** the board path surfaces that named refusal as an ordinary rejection: no quest record, no affinity gain, and no partial provisioning, population, or binding left behind

#### Scenario: The acceptance precheck remains branch plus rank alone
- **WHEN** acceptance eligibility is evaluated after board availability has narrowed the listing
- **THEN** the precheck remains the issuing branch plus the actor's rank alone — the availability rule narrows what the board lists, never what acceptance will attempt — so a player who names an offer's key directly or who accepts a listing taken before the site changed state receives the lifecycle's named refusal instead of a generic eligibility error

#### Scenario: Regional shortage is not a board refusal
- **WHEN** a rank-eligible member accepts a valid source-backed regional hunt at zero living supply
- **THEN** the quest and normal affinity gain commit without creating targets, changing population state or hiding habitat guidance

#### Scenario: A legally unsatisfiable hunt offer is refused cleanly
- **WHEN** acceptance validation encounters an invalid regional selector with no lawful authored source
- **THEN** the named definition/source refusal leaves no quest record, affinity gain or population write; a valid source with too few living targets still accepts

