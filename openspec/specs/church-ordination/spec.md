# church-ordination Specification

## Purpose
Defines the Light Church ordination pipeline (sub-project 1) — opened by this
change with its substrate: the `db.church` merit ledger behind a single-writer
boundary, the `church.yaml` rulebook slice behind the monotonicity and
passive-no-negativity loader gates with the one-row-one-test correspondence
gate, the frozen lore catalogues and the derived church-place set, and the
authored `ChurchHost` clergy hosts. Sibling church changes ADD their own
requirements to this capability (enrollment, accrual, redemption, combat
ministry); none modifies another's.

## Requirements

### Requirement: The merit ledger is persisted character state with a single writer
The system SHALL keep church membership state on the character attribute `db.church`, created lazily by the first church-rules write, carrying `merit: int` (cumulative grace 恩寵), `enrolled_tick: int`, `redeemed: [str, ...]`, `blessing_last_tick: int | null` (the `rite_martial_blessing` cooldown stamp, absent before the first cast), and `daily: {"day": int, "pray": int, "shelter"?: 1}` reset on world-clock day change (the `climax_today` pattern).

#### Scenario: The ledger is created lazily and persists
- **WHEN** a fresh character's first church-rules write commits and she later relogs
- **THEN** `db.church` carries the enrollment tick, zero-or-accrued merit, and the daily counters reset correctly across a clock-day boundary, with no ledger materialized for characters who never touch the church

#### Scenario: Merit cannot leak into the wallet
- **WHEN** any transfer, sell, or currency-mutation path is offered church merit
- **THEN** no path accepts it: merit is readable only by church rules and the redemption catalogue

#### Scenario: Only the church rules module writes the ledger
- **WHEN** the capability ships
- **THEN** no command, typeclass, AI, or presentation module assigns any `db.church` field (grep-enforceable single-writer audit)

#### Scenario: Rite state lives in the ledger and nowhere else
- **WHEN** a holder casts `rite_martial_blessing` and, next day inside a venue, `rite_shelter`
- **THEN** the blessing stamp appears as `db.church["blessing_last_tick"]` and the shelter marker as
  `db.church["daily"]["shelter"]`, no `db.martial_blessing_last_tick` attribute and no root
  `shelter_rest_flag` key is ever written, and the next world-clock day boundary's daily reset
  clears the shelter marker with the prayer counter

#### Scenario: Handler-staged writes still execute inside church.py
- **WHEN** the single-writer audit runs after the cast-rail cut-over
- **THEN** every `db.church` assignment site is inside `world/rules/church.py`, and the rite
  effect handlers mutate the ledger only through its mutators

#### Scenario: The lazy ledger materializes at the first enrollment transaction
- **WHEN** the first church-rules write lands in practice as the first enrollment transaction, once enrollment lands
- **THEN** the ledger is created lazily by that write

#### Scenario: The shelter marker self-resets on the day rollover
- **WHEN** the optional `shelter` marker records that today's `rite_shelter` already ran and the world clock rolls to a new day
- **THEN** the day-rollover `daily.clear()` resets it with no reset code of its own

#### Scenario: The re-pin removes the standalone state keys
- **WHEN** this re-pin ships
- **THEN** rite cooldown and shelter state live ONLY in these ledger keys — no standalone `db.martial_blessing_last_tick` attribute and no root `shelter_rest_flag` key survive

#### Scenario: Merit moves only through the sanctioned rules
- **WHEN** merit changes anywhere
- **THEN** only rulebook accrual rows add merit and only redemption subtracts it

#### Scenario: Merit is not currency
- **WHEN** any trade, wallet, or spending path faces church merit
- **THEN** merit is never tradeable, never moves through any wallet path, and is spendable on nothing except the redemption catalogue, while offering copper pays into the normal integer-copper wallet

#### Scenario: Ledger writes funnel through church.py mechanics
- **WHEN** a church command or a holy-rite effect handler writes the ledger
- **THEN** commands call `world/rules/church.py` mechanics functions and the resolver's holy-rite effect handlers stage `PendingEffect`s whose committed behavior invokes a `church.py` mutator, keeping the grep-enforceable single-writer audit intact across the cast-rail cut-over

#### Scenario: Lore and commands keep their shapes
- **WHEN** the capability ships
- **THEN** lore stays frozen-dataclass registries and commands stay thin

#### Scenario: The ledger survives relogin and every mutation is atomic
- **WHEN** a holder relogs or reloads and any ledger mutation runs
- **THEN** the ledger survives relogin/reload and every mutation happened inside `transaction.atomic()`

### Requirement: The church rulebook slice loads behind the monotonicity and polarity gates
`world/rules/rulebook/church.yaml` SHALL register through the existing `load_rules` loader family and carry `accrual` rows (`pray_completed` with daily cap, `offering_accepted` per offering row, `climax_while_enrolled` gated on enrollment), `acceptance` rows (NPC arousal ordinal 0..4 → accept percent), `pray` rows (duration seconds, merit per pray, daily cap), and `offering` rows (copper payout band, per-row overrides, enrollment requirement).

#### Scenario: A non-monotonic acceptance curve fails at load
- **WHEN** an acceptance row set makes a higher ordinal accept less than a lower one, or drops ordinal 0 from 50% or the top ordinal from 100%
- **THEN** rulebook loading raises naming the row

#### Scenario: A negative-polarity passive row fails at load
- **WHEN** a PASSIVE church catalogue skill carries a rule row that raises a price, lowers a defense, or otherwise worsens baseline
- **THEN** the loader polarity check rejects it, and a data-contract test over shipped rows — written catalogue-driven, not hardcoded — proves every shipped church PASSIVE is positive-polarity only, including rows later changes append

#### Scenario: Every church.yaml row has its test
- **WHEN** the correspondence audit enumerates `church.yaml` rows against the test suite
- **THEN** each row is exercised by exactly one matching test, like `combat_modifiers.yaml`

#### Scenario: A non-monotonic acceptance curve is loader-rejected
- **WHEN** the loader reads an acceptance curve that is not strictly monotonic from ordinal 0 (baseline 50%) to 100% at the top ordinal
- **THEN** loading rejects it

#### Scenario: The passive-no-negativity iron rule rejects negative passives at load
- **WHEN** any PASSIVE catalogue row's rulebook effects are negative relative to baseline
- **THEN** the loader rejects it — every trade-off lives in the redemption price, never in a passive effect; mitigation of an existing penalty counts as positive

#### Scenario: The correspondence gate applies to church.yaml
- **WHEN** the rulebook slice loads
- **THEN** the one-row-one-test correspondence gate applies exactly as it does for `combat_modifiers.yaml`

### Requirement: Church venues and clergy hosts exist as authored content
Places whose authored kwargs carry the `church` flag SHALL form the derived church-place set in `world/lore/church/` (the `shop_key` derivation pattern), and the derivation SHALL fail closed on a duplicate-flagged authoring conflict. The `ChurchHost` typeclass component (sibling of `GuildStaff`, a zero-state capability adapter) SHALL be authored on the one registered clergy NPC roster row (艾莉安娜‧寒水 high celebrant) through her profession blueprint.

#### Scenario: The derived church set is complete and fail-closed
- **WHEN** the lore package derives the church-place set from authored kwargs
- **THEN** every `church`-flagged place appears exactly once, and a duplicate/conflicting church kwarg authoring raises at derivation instead of silently winning

#### Scenario: The clergy host is authored and sync-idempotent
- **WHEN** the profession-blueprint roster derivation and `place-driven-service-sync` converge with `ChurchHost` attached to the celebrant NPC
- **THEN** she resolves through the local-service-host lookup, her spawn data carries the raised initial arousal, the sanctum steward resolves as a plain merchant without the component, and a second sync pass changes nothing

#### Scenario: The clergy row carries the raised initial arousal
- **WHEN** the clergy roster row is authored
- **THEN** that row carries the small raised-initial-arousal authoring kwarg on its spawn data

#### Scenario: The sanctum steward stays a plain merchant
- **WHEN** the roster is authored per owner decision
- **THEN** the sanctum steward 羅海西亞‧芬威克 stays a plain merchant selling the sanctum's wares and carries neither the component nor the arousal seed

#### Scenario: No consumer arrives with this change
- **WHEN** this stage ships
- **THEN** no gameplay mechanic consumes the venue set or the host — the enrollment and accrual changes do — but `place-driven-service-sync` convergence stays idempotent with the new component attached and the derived set is non-empty

### Requirement: The frozen church catalogues ship as validated shells awaiting their pipeline rows
`world/lore/church/` SHALL expose frozen-dataclass `OFFERING_CATALOG` rows `{key, act_key, merit, copper, min_lineage?}` and `REDEEM_CATALOG` rows `{skill_key, merit_price, tier, prereq_keys, polarity}` with row validators exercised at import.

#### Scenario: Shell validators reject malformed rows
- **WHEN** a planted malformed row (bad tier, unknown polarity, missing key, lineage-flavoured prereq machinery) is offered to either catalogue's validator
- **THEN** each is rejected by name, and the shipped shells themselves import clean

#### Scenario: Keys resolve, vessel absent
- **WHEN** the shipped catalogue rows are enumerated
- **THEN** every `act_key` resolves against the act/skill registries with zero duplicated data, and `saintess_vessel` appears nowhere in the redemption catalogue

#### Scenario: The shells carry only seed rows at this stage
- **WHEN** the catalogues ship at this stage
- **THEN** `OFFERING_CATALOG` carries only seed rows for currently-ownable act keys (inert until the offering rail lands) and `REDEEM_CATALOG` is a validated empty shell

#### Scenario: Later changes bring the pipeline rows, never placeholder prices
- **WHEN** the pipeline rows are scheduled
- **THEN** the Series A/B/D rows arrive with the redemption change and Series C/E with the order-catalogue change, and nothing may ship placeholder prices

#### Scenario: Every catalogue key resolves
- **WHEN** the catalogue rows are validated
- **THEN** every catalogue key resolves against the registries it references

#### Scenario: The vessel stays out of the redemption catalogue forever
- **WHEN** the redemption catalogue is checked at any stage
- **THEN** `saintess_vessel` does not appear in it at any stage

### Requirement: Enrollment is a deterministic three-stage transaction behind a ChurchHost
`church join` (aliases 入教／洗禮) SHALL resolve a local `ChurchHost` component (sibling of `GuildStaff`, authored on the registered high celebrant 艾莉安娜‧寒水 only) through the existing local-service-host resolution, pass the schedule gate (`interaction_reason(host, "service_church")`), then run the deterministic `world/rules/church.py::enroll(caller, host)` — no dialogue-model call participates.

#### Scenario: A clean enrollment commits and logs once
- **WHEN** an unaffiliated player character completes `church join` beside an on-duty ChurchHost
- **THEN** the ledger exists, exactly one `church_enrolled` event is emitted at commit, and the whole flow works with every LLM service dead

#### Scenario: Re-enrollment changes nothing
- **WHEN** an already-enrolled character calls `church join` again
- **THEN** the stable rejection is returned and ledger, skills, and inventory are byte-identical with no event

#### Scenario: No host means no enrollment
- **WHEN** `church join` runs with no local ChurchHost, or the host's schedule gate declines
- **THEN** a stable rejection names the reason and no state is written

#### Scenario: Enrollment writes the ledger and logs at commit
- **WHEN** the enrollment transaction commits
- **THEN** it creates the ledger, stamps `enrolled_tick`, and emits `church_enrolled` via the transaction-commit seam

#### Scenario: Re-enrollment is a stable rejection
- **WHEN** an already-enrolled character attempts enrollment
- **THEN** the stable rejection (「你已屬光明教會」) returns with no writes

#### Scenario: Every failure mode and rollback is stable and inert
- **WHEN** the host is missing, the host is off-duty, or any other failure occurs, or an enrollment is rolled back
- **THEN** each failure is a stable rejection message, and a rolled-back enrollment leaves the character byte-identical with no event

### Requirement: Enrollment grants the Saintess office to female royal initiates only, without uniqueness
Within the enrollment transaction, an initiate whose subrace is `human_royal` AND whose sex is female SHALL additionally be granted `saintess_vessel` through the canonical granted-passive write path, emitting the existing `saintess_vessel_granted` observability event exactly once.

#### Scenario: A female royal enrollment grants the vessel in one transaction
- **WHEN** a female `human_royal` character's enrollment transaction commits
- **THEN** her stored passives contain `saintess_vessel`, exactly one `saintess_vessel_granted` event accompanies the single `church_enrolled` event, and her trickle is armed

#### Scenario: Other initiates get no skill
- **WHEN** a non-royal initiate or a male `human_royal` enrolls
- **THEN** no skill is granted and only the plain ledger (plus vestment) is written

#### Scenario: Two eligible royals both become saintesses
- **WHEN** two distinct female `human_royal` characters enroll
- **THEN** both hold `saintess_vessel`; the second grant is not suppressed by the first

#### Scenario: The vessel trickle stays disarmed before enrollment
- **WHEN** the royal preset character settles on the world clock before ever enrolling
- **THEN** her arousal settles byte-identically to a non-holder

#### Scenario: Every other initiate is a plain sister
- **WHEN** an initiate of any other subrace, or a male `human_royal`, enrolls
- **THEN** she becomes a sister with the plain ledger and receives no skill at enrollment

#### Scenario: The clergy passives stay purchasable
- **WHEN** enrollment completes for any initiate
- **THEN** the clergy passives remain redemption purchases

#### Scenario: The office has no uniqueness
- **WHEN** every eligible royal enrolls
- **THEN** each becomes a saintess, with no global office state

#### Scenario: Functionally Saintess from the transaction onward
- **WHEN** a royal's enrollment transaction completes
- **THEN** the trickle, decay-floor, and ceremonial reads arm solely from vessel ownership, so she is functionally Saintess exactly at her enrollment transaction

### Requirement: Enrollment hands over exactly one vestment unconditionally
Every successful enrollment SHALL grant one clerical vestment inside the same transaction through the deterministic item-grant rail: `saintess_vestments` for the vessel branch, `sister_vestments` for ordinary initiates.

#### Scenario: An ordinary initiate receives the sister robe
- **WHEN** a plain initiate's enrollment commits
- **THEN** her inventory carries exactly one `sister_vestments` gained in the enrollment transaction

#### Scenario: The vessel branch receives the saintess robe
- **WHEN** a vessel-branch enrollment without the robe commits
- **THEN** the inventory gains exactly one `saintess_vestments`

#### Scenario: A duplicate is not refused
- **WHEN** an initiate who already carries the vestment key enrolls
- **THEN** the transaction still grants exactly one vestment (quantity +1) and succeeds

#### Scenario: A rolled-back enrollment returns the robe
- **WHEN** the enrollment transaction is forced to fail after the item write
- **THEN** the vestment and the ledger are both absent

#### Scenario: The rail is the deterministic QuestReward quantity rail
- **WHEN** the vestment grant executes
- **THEN** it rides the `QuestReward` item-quantity rail — the LLM `give_item` dialogue intent is NOT the channel

#### Scenario: The celebrant's gift is the rite, not the inventory
- **WHEN** an initiate who already carries that item key enrolls
- **THEN** the handover is unconditional and she receives exactly one more

#### Scenario: The handover is transactional with the ledger
- **WHEN** the enrollment transaction rolls back
- **THEN** the vestment write is removed with the ledger write

#### Scenario: The grant context rides the enrollment event
- **WHEN** the enrollment event is emitted
- **THEN** the grant context rides its context (`char`, `host`, `item`)

### Requirement: The shipped royal preset awaits nothing: the vessel and the robe are enrollment gifts
`violet_altoria.passive_skills` SHALL NOT contain `saintess_vessel` and her `starting_items` SHALL NOT contain `saintess_vestments`; pre-enrollment she is simply a 王女. Her persona SHALL carry NO religious narrative — no 聖女 or 聖女繼承人 wording anywhere — and the rest of her story stays continuous.

#### Scenario: The preset carries neither vessel nor robe
- **WHEN** the preset registry and activation surface are validated
- **THEN** `violet_altoria` lists no `saintess_vessel` passive and no `saintess_vestments` item, and activation writes neither

#### Scenario: No successor wording remains
- **WHEN** the preset's persona fields are searched
- **THEN** 聖女 and 聖女繼承人 appear nowhere, and the removed passages are absent rather than rephrased around a church claim

#### Scenario: The church clause and sacred sentences are deleted, not reframed
- **WHEN** the preset row is edited
- **THEN** the public identity loses the church clause, and the personality's temple-blessing passages and the life story's consecration/duty sentences are DELETED — not rewritten into a successor framing

#### Scenario: The preset data-contract tests follow the row edit
- **WHEN** the preset row ships without the vessel and the robe
- **THEN** all preset data-contract tests follow the row edit

### Requirement: Lore documents state the no-uniqueness office and current status
The lore documents SHALL match the shipped mechanics: `docs/lore/overview.md` §宗教信仰 SHALL retire the once-per-generation donated-princess framing (and any sibling wording) in favour of "any female royal may be donated to the church and consecrated at enrollment"; the `docs/lore/skill-trees/light.md` 聖女 footnote SHALL reflect the enrollment grant; `docs/lore/settlement-locations.md` §神殿／聖所 status tags SHALL move 〔提案〕→〔已實作〕 with their mechanics.

#### Scenario: The retired framing is gone
- **WHEN** the lore documents are searched for the once-per-generation claim
- **THEN** it appears nowhere, and the no-uniqueness framing appears in its place

#### Scenario: Status tags track the landing
- **WHEN** the settlement-locations 神殿／聖所 section is read after this change
- **THEN** the ministry counter's tag reads 〔已實作〕

### Requirement: The church join command is documented in the docs trio
The player command `church join` (aliases 入教／洗禮) SHALL be documented in `docs/game/commands.md` and `docs/game/command-reference.md` in the same change, with `tests/test_command_docs.py` green over the new surface. The remaining church subcommands are documented by the changes that land them (`church pray`/`offer` with the accrual change, `church redeem`/`merit` with the redemption change).

#### Scenario: Docs and commands agree
- **WHEN** the command-docs test runs against the shipped `church join` command
- **THEN** the subcommand and both aliases appear in both documents and the test passes

### Requirement: Prayer is a time-costed, capped, venue-bound accrual
`church pray` SHALL require an existing ledger (the unenrolled are told to speak with the celebrant) and a place whose authored kwargs carry the `church` flag (derived in the lore package, the `shop_key` pattern). `world/rules/church.py::pray_step` SHALL check the daily cap, advance the world clock by the rulebook duration through the existing non-combat clock source (the prayer IS the time cost), apply the `pray_completed` accrual row, commit, and emit `church_pray`. No rolls, no RNG.

#### Scenario: A prayer spends time and earns merit
- **WHEN** an enrolled character prays inside a church-flagged place below her daily cap
- **THEN** the clock advanced by the configured duration, merit increased by the accrual row, and one `church_pray` event logged at commit

#### Scenario: The cap and the venue reject cleanly
- **WHEN** pray is called at the daily cap, outside a church venue, or by the unenrolled
- **THEN** each returns its stable rejection and the clock, ledger, and events are untouched

### Requirement: Sexual offering is explicit-selection ministry gated on the NPC's arousal, never affinity
`church offer <npc> [row_key]` SHALL gate on enrollment only (NOT venue-bound — ministry travels with the sister) and SHALL never auto-count ordinary partnered sex. Acceptance SHALL read the NPC's arousal ordinal, map it through the monotonic `acceptance` curve, and resolve via `roll_d100` through the existing injected-dice gate; affinity SHALL play no role.

#### Scenario: The row menu projects unlocked acts only
- **WHEN** an enrolled sister lists her offering options
- **THEN** exactly the catalogue rows whose `act_key` she owns appear, and an unowned `row_key` is a stable rejection

#### Scenario: Acceptance follows the arousal curve, not affinity
- **WHEN** the same offering is proposed to an NPC at ordinal 0 and to the same NPC later at the top ordinal, with affinity held constant and dice injected at the boundary values
- **THEN** ordinal 0 accepts exactly within its 50% band and the top ordinal accepts unconditionally, with no affinity term consulted anywhere in the decision

#### Scenario: An accepted offering settles in one transaction
- **WHEN** the die accepts an offering row
- **THEN** the act's full normal rails ran on both bodies, merit and copper moved in the same commit, and one `church_offering_accepted` event logged; a rolled-back settlement leaves neither

#### Scenario: A declined offering writes nothing
- **WHEN** the die declines
- **THEN** one `church_offering_declined` event logs and ledger, wallet, and act state are byte-identical, with the offer immediately re-proposable

#### Scenario: The selectable rows are the unlocked catalogue rows
- **WHEN** the offering menu is built
- **THEN** the selectable rows are exactly the `OFFERING_CATALOG` rows whose `act_key` the player currently owns through the existing counter-gated unlock projection (no new unlock system; advanced rows reference the Series D acts by shared key)

#### Scenario: An accepted offering runs the act and settles in one transaction
- **WHEN** the dice accept an offering
- **THEN** the act executes through the existing action-resolution pipeline (all pleasure/shame/exposure/counter rails run normally on both bodies) and the same transaction adds the row's merit plus its copper payout, emitting `church_offering_accepted`

#### Scenario: A declined offering is free to retry
- **WHEN** the dice decline an offering
- **THEN** `church_offering_declined` fires with zero writes, no penalty, and no cooldown

#### Scenario: Sex outside the offering flow is untouched
- **WHEN** normal partnered sex happens outside the offering flow
- **THEN** it is byte-identical to before this change

### Requirement: Climax accrual rides the side-reaction rail and fails closed for the unenrolled
A `climax_while_enrolled` accrual row SHALL ride the same side-reaction rail as `state_reactions.yaml` rows: entering 進行中 while enrolled adds a small configured merit. The enrollment condition SHALL fail closed: an unenrolled entity's climax settlement (accrual, event, and byte-level writes) SHALL stay byte-identical to before this change.

#### Scenario: An enrolled climax credits merit once per entry
- **WHEN** an enrolled character's climax phase transitions into 進行中
- **THEN** the configured accrual applies exactly for that transition

#### Scenario: Unenrolled climaxes are byte-identical
- **WHEN** an unenrolled character completes the identical climax sequence
- **THEN** every write matches the pre-change baseline

### Requirement: The accrual paths are offline-deterministic with commit-bound observability
No `world/ai/` module SHALL participate in prayer, offering, or climax accrual (AI is prose overlay only). Their state writes SHALL sit inside `transaction.atomic()`, and their events SHALL flow only through the `world.observability` facade with plain-data contexts (`char`, `npc`, `row`, `tick`): `church_pray`, `church_offering_accepted`, `church_offering_declined`.

#### Scenario: The accrual paths run with AI dead
- **WHEN** pray → offer (accept and decline branches) → climax accrual execute with every LLM service unavailable
- **THEN** each step produces its deterministic mechanical result and the three events are observed at commit

#### Scenario: Rollbacks emit nothing
- **WHEN** any church transaction is rolled back after its event registration
- **THEN** no facade event for that transaction appears

#### Scenario: A successful rite cast logs one commit-bound event
- **WHEN** a `rite_martial_blessing` or `rite_shelter` cast settles successfully
- **THEN** exactly one `rite_cast` facade event is observed at the settlement commit with `char`,
  `rite`, and `tick` in its context, and a rolled-back cast emits none

#### Scenario: The sibling events land with their own changes
- **WHEN** enrollment, redemption, or a successful holy-rite cast settles
- **THEN** `church_enrolled` lands with enrollment, `church_skill_redeemed` with redemption, and `rite_cast` with each successful holy-rite cast settlement

#### Scenario: Events are commit-bound and failures are stable
- **WHEN** a transaction rolls back or any failure mode (not enrolled, outside venue, daily cap, row not unlocked, NPC declined) occurs
- **THEN** every event is commit-bound so a rolled-back transaction emits nothing, and every failure mode has a stable rejection message

#### Scenario: The cross-loop proof belongs to the combat-ministry change
- **WHEN** the full cross-loop end-to-end AI-dead integration proof is scheduled
- **THEN** it is landed by the combat-ministry change; this one covers its own paths

### Requirement: The church pray and offer commands are documented in the docs trio
The player commands `church pray` and `church offer <npc> [row_key]` SHALL be documented in `docs/game/commands.md` and `docs/game/command-reference.md` in the same change, with `tests/test_command_docs.py` green over the new surface. `church join` is already documented by the enrollment change; `church redeem`/`merit` arrive with the redemption change.

#### Scenario: Docs and commands agree
- **WHEN** the command-docs test runs against the shipped church commands
- **THEN** `pray` and `offer` appear in both documents alongside the already-documented `join`, and the test passes

### Requirement: Redemption is a one-shot, all-or-nothing grace purchase
`church redeem list` SHALL print the catalogue with current merit and redeemed marks. `church redeem <key>` SHALL validate (row exists ∧ not already redeemed ∧ merit sufficient ∧ catalogue-internal prereqs met), then in ONE transaction subtract merit, write the skill through the sanctioned granted-skill write (PASSIVE rows to `db.skills.passive`, ACTIVE rows to `db.skills.active`), append the key to `redeemed`, and emit `church_skill_redeemed`.

#### Scenario: A funded redemption writes the skill atomically
- **WHEN** an initiate with sufficient merit redeems an affordable, prereq-met row
- **THEN** merit decreased by the price, the skill is in the right `db.skills` store for its kind, the key is in `redeemed`, and one `church_skill_redeemed` event logged at commit

#### Scenario: Every rejection is inert
- **WHEN** redemption is attempted for an unknown key, an already-redeemed key, insufficient merit, or unmet prereq
- **THEN** the matching stable rejection returns and every store is byte-identical

#### Scenario: Prereqs are plain catalogue keys
- **WHEN** catalogue-internal prereqs are evaluated
- **THEN** they are a plain list of other catalogue keys, never lineage machinery

#### Scenario: The vessel is never purchasable
- **WHEN** the redemption catalogue is enumerated
- **THEN** `saintess_vessel` is absent, and `church redeem saintess_vessel` is the unknown-key rejection

#### Scenario: Rollback mid-redemption leaves everything
- **WHEN** the redemption transaction is forced to fail after the merit subtraction
- **THEN** merit, skills, and `redeemed` equal their pre-attempt values and no event emits

#### Scenario: Every failure is a stable, inert rejection
- **WHEN** redemption fails (unknown key, repeat redemption, insufficient merit, unmet prereq)
- **THEN** merit, skills, and `redeemed` are left untouched with a stable rejection

#### Scenario: Repeat redemption is impossible
- **WHEN** an already-redeemed key is offered again
- **THEN** redemption is impossible

#### Scenario: The vessel ban is permanently pinned
- **WHEN** the redemption catalogue is guarded
- **THEN** `saintess_vessel` NEVER appears in it at any price — pinned by a permanent negative-set test

#### Scenario: The existing passive guards stay green
- **WHEN** the redemption pipeline ships
- **THEN** the existing PASSIVE practice/unlock/conferral guards stay untouched and green — the pipeline is the sanctioned channel, not a bypass

#### Scenario: church merit prints the ledger read-only
- **WHEN** `church merit` runs
- **THEN** it prints the ledger (merit, enrollment day, redeemed marks, daily prayer usage) read-only

### Requirement: Series A/B/D rows ship as registry skills earned only through the church pipeline
The catalogue SHALL carry the 16 Series A/B/D rows as new `SKILL_REGISTRY` entries, shipping the full Series A/B/D rosters pinned by the scenarios below. No row SHALL appear in any lineage tree, and the redemption pipeline SHALL be the only acquisition path.

#### Scenario: Every Series A/B/D row is a redeemable, non-lineage skill
- **WHEN** the shipped catalogue and the lineage graphs are enumerated
- **THEN** all 16 keys exist in `SKILL_REGISTRY` and the catalogue, none appears in any lineage tree or unlock rule, and each prices within its tuned band

#### Scenario: Offering rows reuse the act keys
- **WHEN** a Series D advanced offering row is selected from the offering menu
- **THEN** its `act_key` equals its redemption skill key, and the offering projection and the redemption catalogue reference the same registry row with no duplicated data

#### Scenario: Series A clergy qualifier passives
- **WHEN** the Series A rows are registered
- **THEN** they are `pain_to_pleasure`, `priestly_grace`, `rapture_renewal` (first-time catalogue entry ;  the 「聖職敘階授予」 channel itself) and new `vow_of_service` (authored positive offering copper and offering/climax merit adjustments, ledger multipliers only, pure-positive)

#### Scenario: Series B rite actives
- **WHEN** the Series B rows are registered
- **THEN** they are `rite_heal_light`, `rite_cleanse`, `rite_calm`, `rite_bless_water`, `rite_sanctify_ground`, `rite_absolution`, `rite_lamb_mark`, `rite_martyrdom_vow`

#### Scenario: Series D sexual-ministry actives
- **WHEN** the Series D rows are registered
- **THEN** they are `rite_holy_kiss`, `rite_milk_blessing`, `rite_confession_bed`, `rite_anointing_touch`, doubling as advanced `OFFERING_CATALOG` rows by shared key, zero duplication

#### Scenario: Prices and prereqs follow the recorded finals
- **WHEN** the catalogue rows are priced and chained
- **THEN** prices validate against the current authored bands without historical final-value tables, and catalogue-internal prereq chains ride the Series D high rows only

#### Scenario: The combat rails are separate requirements
- **WHEN** the two combat rite rails ;  the lamb-seal charge buff and the martyr-vow pool filter ;  are scheduled
- **THEN** they are separate requirements landed by the combat-ministry change; here the rows register with their declarations

### Requirement: The church redeem and merit commands are documented in the docs trio
The player commands `church redeem [list|<key>]` and `church merit` SHALL be documented in `docs/game/commands.md` and `docs/game/command-reference.md` in the same change, with `tests/test_command_docs.py` green over the completed surface (`join` documented by the enrollment change, `pray`/`offer` by the accrual change).

#### Scenario: Docs and commands agree
- **WHEN** the command-docs test runs against the completed church command surface
- **THEN** `redeem` and `merit` appear in both documents alongside the previously documented subcommands, and the test passes

### Requirement: Lamb mark narrows monster target preference with a charging buff
`rite_lamb_mark` SHALL mount the `lamb_seal` combat buff using ONE new buff-declaration primitive `charges: int`: each transition of the bearer's climax phase into 進行中 consumes one charge; at zero the buff is removed (the seal lifts after the bearer's second climax). In `monster_behaviour_policy`, BEFORE target-strategy evaluation, if any living enemy carries `lamb_seal`, single-target candidates SHALL narrow to seal-bearers.

#### Scenario: The seal redirects single-target selection
- **WHEN** a monster with a `lowest_hp` (or `highest_effective_power`) strategy faces a seal-bearer and a lower-priced normal target
- **THEN** the seal-bearer is chosen, and with no seal anywhere the decision trace is byte-identical to the pre-change policy

#### Scenario: Two climaxes lift the seal
- **WHEN** the bearer's climax phase enters 進行中 twice
- **THEN** the first consumption leaves the seal live, the second removes it, and subsequent fights show no seal without a fresh cast

#### Scenario: Multi-seal falls to canonical order
- **WHEN** two living enemies carry seals
- **THEN** the player-bearer is preferred, then ascending pk among NPC bearers

#### Scenario: Area and marker rails are untouched
- **WHEN** a monster casts an AREA skill, or a positional marker exclusion applies
- **THEN** the seal neither narrows nor substitutes those paths

#### Scenario: The charges primitive is tested in isolation
- **WHEN** the `charges` primitive ships
- **THEN** it is tested standalone — declaration round-trip, save/restore, the two-transition consumption sequence, and a rolled-back consumption that does not burn a charge

#### Scenario: Several seal-bearers fall to the canonical tie-break order
- **WHEN** several seal-bearers are eligible as single-target candidates
- **THEN** the canonical order is player first, then ascending pk

#### Scenario: With no seal present nothing changes
- **WHEN** no living enemy carries `lamb_seal`
- **THEN** every monster decision is byte-identical to today

#### Scenario: The seal is preference, not threat
- **WHEN** a seal is live in a fight
- **THEN** there is no accumulation, decay, or transfer, and the seal ends with the fight

#### Scenario: AREA skills and positional markers stay orthogonal
- **WHEN** a monster uses an AREA skill or a positional marker exclusion applies
- **THEN** AREA skills are unaffected and positional markers remain an orthogonal exclusion that the seal SHALL NOT substitute

### Requirement: Martyrdom vow collapses the defeat-aftermath victim pool to the marked martyr
`rite_martyrdom_vow` cast during a fight SHALL stamp `martyr_key` (with the durable session id) on the combat session record. At defeat settlement, `_violation_pool` SHALL apply one additional filter: if the session stamp matches a non-fled pool member, the pool collapses to `[her]` and the existing single-member short-circuit returns her with zero target rolls (resist contests keep their normal draws).

#### Scenario: The marked sister is chosen with zero target rolls
- **WHEN** a defeated fight's session carries a valid martyr stamp for a non-fled survivor in the pool
- **THEN** `_violation_pool` collapses to her and returns with zero target-selection rolls

#### Scenario: Every edge falls back to the normal pool
- **WHEN** the marker died, fled, the stamp is stale, or no stamp exists
- **THEN** the pool behaves byte-identically to the pre-change filter chain

#### Scenario: Victory consumes the stamp
- **WHEN** the marked fight ends in victory
- **THEN** the stamp is spent and a later defeat in another session cannot fire it

#### Scenario: The edge rules keep the normal pool
- **WHEN** the marker died before the wipe, or the marker fled so the filter finds no eligible martyr, or the session id mismatches (a stale stamp that can never fire)
- **THEN** the pool follows its normal path in every case

#### Scenario: Multiple markers resolve canonically
- **WHEN** several pool members carry the martyr marker
- **THEN** the first by canonical order is chosen

#### Scenario: Rollback-retry determinism holds
- **WHEN** a defeat settlement is rolled back and retried
- **THEN** the stamp is durable record state and the draws stay state-derived, so the retry is deterministic

### Requirement: The combat rails are offline-deterministic and the full church loop runs end-to-end with AI dead
No `world/ai/` module SHALL participate in the lamb-seal narrowing, the martyr-vow pool filter, or their buff machinery. The full sub-project-1 loop — `church join` → `church pray` → `church offer` → climax accrual → `church redeem` — SHALL execute as one registered integration test with every LLM service stubbed to raise.

#### Scenario: The full loop runs with AI dead
- **WHEN** join → pray → offer → climax → redeem execute with every LLM service unavailable
- **THEN** every step produces its deterministic mechanical result and all five events are observed

#### Scenario: Rollbacks emit nothing anywhere in the loop
- **WHEN** any church transaction is rolled back after its event registration
- **THEN** no facade event for that transaction appears

#### Scenario: All five events are observed at their commits
- **WHEN** the full loop integration test runs
- **THEN** the five observability events (`church_enrolled`, `church_pray`, `church_offering_accepted`, `church_offering_declined`, `church_skill_redeemed`) are observed at their commits

#### Scenario: The observability lint reports zero findings
- **WHEN** the observability lint (facade-only, commit-bound) runs over every module the church pipeline touched
- **THEN** it reports zero findings

### Requirement: Series C discipline passives ship pure-positive with no baseline downside
The redemption catalogue SHALL gain five Series C rows as `SKILL_REGISTRY` PASSIVE skills ;  `poverty_vow`, `obedience`, `chastity_discipline`, `temple_endurance`, `public_devotion` ;  with the per-row effects pinned by the scenarios below. No Series C row SHALL carry any effect negative relative to baseline, and the loader's polarity gate SHALL reject any row that does.

#### Scenario: Every Series C passive is positive-only
- **WHEN** the shipped rule rows of each Series C passive are enumerated through the loader's polarity reading
- **THEN** each is positive-vs-baseline (or the sanctioned penalty-mitigation reading for `temple_endurance`), and the planted-downside probe (e.g. a price-increase row on `poverty_vow`) is loader-rejected

#### Scenario: Obedience doubles merit only under the status
- **WHEN** a holder earns offering/climax merit while under a domination/submission status and while not under one
- **THEN** the credit increases by its declared positive multiplier in the first case and unchanged in the second

#### Scenario: Temple endurance mitigates, never adds a penalty
- **WHEN** a holder at the high-arousal defense-penalty tier is compared against baseline and against a non-holder
- **THEN** the holder's penalty magnitude is smaller by its declared mitigation fraction than baseline and the non-holder's penalty is byte-identical to the pre-change value

#### Scenario: Poverty vow and chastity discipline raise income
- **WHEN** a holder earns offering copper or pray merit
- **THEN** `poverty_vow` raises offering copper income and pray merit, and `chastity_discipline` raises pray merit

#### Scenario: The price-rise downside is removed
- **WHEN** `poverty_vow` is authored
- **THEN** the original "shop prices rise" downside is REMOVED per the passive-no-negativity iron rule: there is no unequip-a-passive concept, so every trade-off lives in the redemption price

#### Scenario: Temple endurance is sanctioned mitigation
- **WHEN** `temple_endurance` is authored
- **THEN** it mitigates the EXISTING high-arousal defense penalty by its declared positive mitigation fraction ;  mitigation of an existing penalty is positive relative to baseline and therefore allowed

#### Scenario: Public devotion rewards public acts
- **WHEN** a holder performs acts in public venues
- **THEN** `public_devotion` raises the merit earned from those acts

### Requirement: Series E utility rows feed the core loop
The redemption catalogue SHALL gain the three Series E rows as cast-rail or ownership mechanics ;  `rite_martial_blessing`, `rite_shelter`, and `rite_morning_devotion` ;  whose handler and gating details are pinned by the scenarios below. None SHALL appear in any lineage tree; the redemption pipeline is the only acquisition path; prices land inside the tuned bands.

#### Scenario: Morning devotion raises the prayer cap by exactly one
- **WHEN** a redeemed holder prays once past her base daily cap
- **THEN** the prayer succeeds, and without the skill the same prayer hit the cap's stable rejection

#### Scenario: Martial blessing is clock-cooled and single-stat
- **WHEN** `rite_martial_blessing` is cast before a fight and recast inside its cooldown
- **THEN** the first mounts exactly one stat buff and the second is the stable cooldown rejection

#### Scenario: Shelter marks the ledger, not the wallet
- **WHEN** an enrolled sister rests at a sanctuary venue holding `rite_shelter`
- **THEN** the rest bonus applies once with its ledger flag recorded, and no copper or merit moves outside the configured bonus

#### Scenario: Blessing and shelter resolve through the shared resolver face
- **WHEN** a redeemed holder casts `rite_martial_blessing` before a fight and, inside a venue,
  `rite_shelter`
- **THEN** both settle through `settle_out_of_combat_cast` ;  buff mounted with its cooldown stamp,
  rest bonus applied with its day marker, one `rite_cast` event each ;  and a forced commit failure
  restores ledger, buffs, traits, and tick byte-identically

#### Scenario: Morning devotion is a passive grant, not a cast
- **WHEN** a sister redeems `rite_morning_devotion` and then attempts to cast it
- **THEN** the skill landed in `db.skills.passive`, the cast is the stable PASSIVE rejection, and
  her pray daily cap is raised by its authored positive increment from the moment of redemption

#### Scenario: Shelter re-arms after the day boundary
- **WHEN** a holder uses `rite_shelter`, the world clock crosses a day boundary, and she casts it
  again inside a venue
- **THEN** the second cast succeeds with its rest bonus, while a same-day third attempt stays the
  stable `RITE_ALREADY_SHELTERED` rejection

#### Scenario: Martial blessing is a cast-rail mechanic
- **WHEN** `rite_martial_blessing` (ACTIVE, `holy_rite`) is cast
- **THEN** its registry row declares `effects=("rite_blessing:martial_blessing",)`, the `rite_blessing` handler stages the ledger cooldown stamp and the single-stat buff mount, and recasting inside the `church.yaml` cooldown window is the stable `RITE_COOLDOWN_ACTIVE` rejection

#### Scenario: Blessing uses no standalone engine API
- **WHEN** the blessing resolves
- **THEN** no standalone engine API participates, and time cost rides the settlement's ordinary COMMAND charge

#### Scenario: Shelter is a cast-rail mechanic
- **WHEN** `rite_shelter` (ACTIVE, `holy_rite`) is cast
- **THEN** its row declares `effects=("rite_shelter",)`, the handler gates on the church venue (`RITE_OUTSIDE_VENUE`) and the current day-block (`RITE_ALREADY_SHELTERED`), and stages the `church.yaml` `rest_bonus` hp/sp gain plus the `daily["shelter"]` marker

#### Scenario: Shelter re-arms on the new day with no reset code
- **WHEN** a new world-clock day arrives after a shelter use
- **THEN** the rite is available again with no reset code

#### Scenario: Morning devotion is re-judged PASSIVE
- **WHEN** `rite_morning_devotion` is classified
- **THEN** it is re-judged `PASSIVE` (its effect is the authored positive pray daily cap increment, purely ownership-triggered ;  a cast could only burn time), granted to `db.skills.passive` by the ordinary redemption rail and still feeding the pray → merit → redeem loop

### Requirement: Series C/E rule rows load under the correspondence and polarity gates
Each Series C/E mechanic SHALL be tunable by a `world/rules/rulebook/church.yaml` row (no hardcoded numbers in Python), each row exercising the existing one-row-one-test correspondence gate.

#### Scenario: One row, one test
- **WHEN** the correspondence audit runs over the grown `church.yaml`
- **THEN** every new Series C/E row has exactly one matching test

#### Scenario: The catalogue completes at 24
- **WHEN** the shipped `REDEEM_CATALOG` is enumerated
- **THEN** it holds the 16 Series A/B/D rows plus these 8, no duplicate keys, no lineage membership anywhere, and `saintess_vessel` still absent

#### Scenario: The core change owns the shared bands and bases
- **WHEN** prices and bases are sourced
- **THEN** the core change owns the shared price BANDS (entry/mid/high) and the pray/accrual BASE values

#### Scenario: This change records its own finals
- **WHEN** this change authors its numbers
- **THEN** it decides and records its OWN eight price finals inside those bands and its own Series C/E numeric finals (scales, mitigation factor, buff magnitude, cooldown, cap increment) in the `REDEEM_CATALOG`/`church.yaml` authoring, and correspondence tests validate row IDs, predicates, reference resolution and polarity; shared fixed synthetic tests validate calculations without final-value pins

#### Scenario: Series C/E rows are prereq-free
- **WHEN** the grown catalogue is enumerated
- **THEN** the catalogue enumerates 24 rows total once these 8 land, with Series C/E prereq-free (catalogue-internal prereqs stay on the Series D high rows only)

