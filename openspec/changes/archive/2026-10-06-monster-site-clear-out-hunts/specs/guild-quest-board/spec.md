## MODIFIED Requirements

### Requirement: Guild boards expose only local rank-eligible offers
`list_guild_offers(actor, staff)` SHALL require valid registration and local GuildStaff. It SHALL return
only offers issued by that staff's branch whose quest-rank order is less than or equal to the actor's
canonical `guild_rank` order, in stable rank/key order. It SHALL never read registration snapshot values
or `disguised_stats` for eligibility. A bound clear-out over an authored site SHALL additionally be
offered only while its site can currently supply the objective's quantity of living individuals, read
through the same quest-layer read the acceptance-time guarantee uses, so the board never advertises work
that acceptance would refuse; a cleared one-shot site's clear-out is therefore absent from the board, and
a recoverable site's clear-out returns once its authored in-game condition has matured and it has
repopulated. A site the world has not yet populated SHALL be treated the same way: its clear-out is absent
until the world clock's own settlement populates the site, and no quest, board read, or acceptance ever
populates one. The availability rule SHALL narrow the listing only: it SHALL NOT change the acceptance
precheck, and it SHALL be independent of rank eligibility, of the objective-summary rendering, and of the
ordering key: a board listed with summaries and without them returns the same offers in the same order.

#### Scenario: F member sees only local F offers
- **WHEN** an F member lists a board containing local F/E offers and a remote F offer
- **THEN** only the local F offer is returned

#### Scenario: True exceptional power does not bypass rank
- **WHEN** a true-stat elf registered at F lists the board
- **THEN** offers above F remain hidden despite the elf's combat power

#### Scenario: A cleared one-shot site's clear-out leaves the board
- **WHEN** a one-shot site's individuals are defeated and the site is declared cleared, then the board is listed again
- **THEN** its clear-out is not offered, and no other offer's eligibility or order changed

#### Scenario: A recovered site's clear-out returns to the board
- **WHEN** a cleared recoverable site's authored condition matures and it repopulates with fresh individuals
- **THEN** its clear-out is offered again, and acceptance binds those fresh individuals rather than any previously defeated one

#### Scenario: An unpopulated site's clear-out is absent until the world settles it
- **WHEN** the board is listed before any world-clock advance has populated a site
- **THEN** that site's clear-out is absent, and no individual is created for it by listing or accepting

#### Scenario: Availability never reorders the board
- **WHEN** a board containing clear-outs and species hunts is listed with and without objective summaries
- **THEN** the returned offers and their order are identical, and only the rendered rows differ

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
instance pins — a stage's instance binding is made at stage advance, and a site clear-out's stage-zero
target binding is made at acceptance without an instance pin), apply the quest
record and the gain inside one transaction, and restore every surface on failure so a failed
affinity write rolls back the acceptance; abandonment SHALL grant no affinity.
When `accept_quest()` refuses an offer because the hunt cannot be legally satisfied (the
target-availability guarantee fails) — a regional species hunt whose region cannot supply the count, or a
bound clear-out whose site cannot supply its living individuals — the board path SHALL surface that named
refusal as an ordinary rejection: no quest record, no affinity gain, and no partial provisioning,
population, or binding left behind.
The acceptance precheck SHALL remain the issuing branch plus the actor's rank alone: the availability rule
narrows what the board lists, never what acceptance will attempt, so a player who names an offer's key
directly or who accepts a listing taken before the site changed state receives the lifecycle's named
refusal instead of a generic eligibility error.
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
