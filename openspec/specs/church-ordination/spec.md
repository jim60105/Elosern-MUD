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
The system SHALL keep church membership state on the character attribute `db.church`, created lazily by the first church-rules write (in practice the first enrollment transaction, once enrollment lands), carrying `merit: int` (cumulative grace 恩寵), `enrolled_tick: int`, `redeemed: [str, ...]`, and `daily: {"day": int, "pray": int}` reset on world-clock day change (the `climax_today` pattern). Only rulebook accrual rows SHALL add merit and only redemption SHALL subtract it. Merit SHALL NOT be currency: it SHALL NOT be tradeable, SHALL NOT move through any wallet path, and SHALL be spendable on nothing except the redemption catalogue; offering copper pays into the normal integer-copper wallet. Every write to `db.church` SHALL live in `world/rules/church.py`; lore stays frozen-dataclass registries and commands stay thin. The ledger SHALL survive relogin/reload and every mutation SHALL be inside `transaction.atomic()`.

#### Scenario: The ledger is created lazily and persists
- **WHEN** a fresh character's first church-rules write commits and she later relogs
- **THEN** `db.church` carries the enrollment tick, zero-or-accrued merit, and the daily counters reset correctly across a clock-day boundary, with no ledger materialized for characters who never touch the church

#### Scenario: Merit cannot leak into the wallet
- **WHEN** any transfer, sell, or currency-mutation path is offered church merit
- **THEN** no path accepts it: merit is readable only by church rules and the redemption catalogue

#### Scenario: Only the church rules module writes the ledger
- **WHEN** the capability ships
- **THEN** no command, typeclass, AI, or presentation module assigns any `db.church` field (grep-enforceable single-writer audit)

### Requirement: The church rulebook slice loads behind the monotonicity and polarity gates
`world/rules/rulebook/church.yaml` SHALL register through the existing `load_rules` loader family and carry `accrual` rows (`pray_completed` with daily cap, `offering_accepted` per offering row, `climax_while_enrolled` gated on enrollment), `acceptance` rows (NPC arousal ordinal 0..4 → accept percent), `pray` rows (duration seconds, merit per pray, daily cap), and `offering` rows (copper payout band, per-row overrides, enrollment requirement). The loader SHALL reject an acceptance curve that is not strictly monotonic from ordinal 0 (baseline 50%) to 100% at the top ordinal, and SHALL reject any PASSIVE catalogue row whose rulebook effects are negative relative to baseline (the passive-no-negativity iron rule — every trade-off lives in the redemption price, never in a passive effect; mitigation of an existing penalty counts as positive). The one-row-one-test correspondence gate SHALL apply exactly as it does for `combat_modifiers.yaml`.

#### Scenario: A non-monotonic acceptance curve fails at load
- **WHEN** an acceptance row set makes a higher ordinal accept less than a lower one, or drops ordinal 0 from 50% or the top ordinal from 100%
- **THEN** rulebook loading raises naming the row

#### Scenario: A negative-polarity passive row fails at load
- **WHEN** a PASSIVE church catalogue skill carries a rule row that raises a price, lowers a defense, or otherwise worsens baseline
- **THEN** the loader polarity check rejects it, and a data-contract test over shipped rows — written catalogue-driven, not hardcoded — proves every shipped church PASSIVE is positive-polarity only, including rows later changes append

#### Scenario: Every church.yaml row has its test
- **WHEN** the correspondence audit enumerates `church.yaml` rows against the test suite
- **THEN** each row is exercised by exactly one matching test, like `combat_modifiers.yaml`

### Requirement: Church venues and clergy hosts exist as authored content
Places whose authored kwargs carry the `church` flag SHALL form the derived church-place set in `world/lore/church/` (the `shop_key` derivation pattern), and the derivation SHALL fail closed on a duplicate-flagged authoring conflict. The `ChurchHost` typeclass component (sibling of `GuildStaff`, a zero-state capability adapter) SHALL be authored on the one registered clergy NPC roster row (艾莉安娜·寒水 high celebrant) through her profession blueprint — per owner decision the sanctum steward 羅海西亞·芬威克 stays a plain merchant selling the sanctum's wares and SHALL NOT carry the component nor the arousal seed — and that row SHALL carry the small raised-initial-arousal authoring kwarg on its spawn data. No gameplay mechanic consumes the venue set or the host at this stage — the enrollment and accrual changes do — but `place-driven-service-sync` convergence SHALL stay idempotent with the new component attached and the derived set SHALL be non-empty.

#### Scenario: The derived church set is complete and fail-closed
- **WHEN** the lore package derives the church-place set from authored kwargs
- **THEN** every `church`-flagged place appears exactly once, and a duplicate/conflicting church kwarg authoring raises at derivation instead of silently winning

#### Scenario: The clergy host is authored and sync-idempotent
- **WHEN** the profession-blueprint roster derivation and `place-driven-service-sync` converge with `ChurchHost` attached to the celebrant NPC
- **THEN** she resolves through the local-service-host lookup, her spawn data carries the raised initial arousal, the sanctum steward resolves as a plain merchant without the component, and a second sync pass changes nothing

### Requirement: The frozen church catalogues ship as validated shells awaiting their pipeline rows
`world/lore/church/` SHALL expose frozen-dataclass `OFFERING_CATALOG` rows `{key, act_key, merit, copper, min_lineage?}` and `REDEEM_CATALOG` rows `{skill_key, merit_price, tier, prereq_keys, polarity}` with row validators exercised at import. At this stage `OFFERING_CATALOG` carries only seed rows for currently-ownable act keys (inert until the offering rail lands) and `REDEEM_CATALOG` is a validated empty shell — the Series A/B/D rows arrive with the redemption change and Series C/E with the order-catalogue change; nothing may ship placeholder prices. Every catalogue key SHALL resolve against the registries it references, and `saintess_vessel` SHALL NOT appear in the redemption catalogue at any stage.

#### Scenario: Shell validators reject malformed rows
- **WHEN** a planted malformed row (bad tier, unknown polarity, missing key, lineage-flavoured prereq machinery) is offered to either catalogue's validator
- **THEN** each is rejected by name, and the shipped shells themselves import clean

#### Scenario: Keys resolve, vessel absent
- **WHEN** the shipped catalogue rows are enumerated
- **THEN** every `act_key` resolves against the act/skill registries with zero duplicated data, and `saintess_vessel` appears nowhere in the redemption catalogue

### Requirement: Enrollment is a deterministic three-stage transaction behind a ChurchHost
`church join` (aliases 入教／洗禮) SHALL resolve a local `ChurchHost` component (sibling of `GuildStaff`, authored on the registered high celebrant 艾莉安娜·寒水 only) through the existing local-service-host resolution, pass the schedule gate (`interaction_reason(host, "service_church")`), then run the deterministic `world/rules/church.py::enroll(caller, host)` — no dialogue-model call participates. Enrollment SHALL create the ledger, stamp `enrolled_tick`, and emit `church_enrolled` via the transaction-commit seam. Re-enrollment SHALL be a stable rejection (「你已屬光明教會」) with no writes. Missing host, off-duty host, and every other failure SHALL be a stable rejection message, and a rolled-back enrollment SHALL leave the character byte-identical with no event.

#### Scenario: A clean enrollment commits and logs once
- **WHEN** an unaffiliated player character completes `church join` beside an on-duty ChurchHost
- **THEN** the ledger exists, exactly one `church_enrolled` event is emitted at commit, and the whole flow works with every LLM service dead

#### Scenario: Re-enrollment changes nothing
- **WHEN** an already-enrolled character calls `church join` again
- **THEN** the stable rejection is returned and ledger, skills, and inventory are byte-identical with no event

#### Scenario: No host means no enrollment
- **WHEN** `church join` runs with no local ChurchHost, or the host's schedule gate declines
- **THEN** a stable rejection names the reason and no state is written

### Requirement: Enrollment grants the Saintess office to female royal initiates only, without uniqueness
Within the enrollment transaction, an initiate whose subrace is `human_royal` AND whose sex is female SHALL additionally be granted `saintess_vessel` through the canonical granted-passive write path, emitting the existing `saintess_vessel_granted` observability event exactly once. Every other initiate (any other subrace, and a male `human_royal`) SHALL become a sister with the plain ledger and SHALL receive no skill at enrollment; the clergy passives remain redemption purchases. There SHALL be no office uniqueness: every eligible royal who enrolls becomes a saintess, with no global office state. The trickle, decay-floor, and ceremonial reads arm solely from vessel ownership, so a royal becomes functionally Saintess exactly at her enrollment transaction.

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

### Requirement: Enrollment hands over exactly one vestment unconditionally
Every successful enrollment SHALL grant one clerical vestment inside the same transaction through the deterministic item-grant rail (the `QuestReward` item-quantity rail; the LLM `give_item` dialogue intent is NOT the channel): `saintess_vestments` for the vessel branch, `sister_vestments` for ordinary initiates. The handover SHALL be unconditional — even an initiate who already carries that item key receives exactly one more, because the celebrant's gift is the rite, not the inventory — and SHALL be transactional with the ledger write (rollback removes it). The grant context SHALL ride the enrollment event context (`char`, `host`, `item`).

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

### Requirement: The shipped royal preset awaits nothing: the vessel and the robe are enrollment gifts
`violet_altoria.passive_skills` SHALL NOT contain `saintess_vessel` and her `starting_items` SHALL NOT contain `saintess_vestments`; pre-enrollment she is simply a 王女. Her persona SHALL carry NO religious narrative: no 聖女 or 聖女繼承人 wording anywhere, the public identity loses the church clause, and the personality's temple-blessing passages and the life story's consecration/duty sentences are DELETED — not rewritten into a successor framing — while the rest of her story stays continuous. All preset data-contract tests follow the row edit.

#### Scenario: The preset carries neither vessel nor robe
- **WHEN** the preset registry and activation surface are validated
- **THEN** `violet_altoria` lists no `saintess_vessel` passive and no `saintess_vestments` item, and activation writes neither

#### Scenario: No successor wording remains
- **WHEN** the preset's persona fields are searched
- **THEN** 聖女 and 聖女繼承人 appear nowhere, and the removed passages are absent rather than rephrased around a church claim

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
`church offer <npc> [row_key]` SHALL gate on enrollment only (NOT venue-bound — ministry travels with the sister) and SHALL never auto-count ordinary partnered sex. The selectable rows SHALL be exactly the `OFFERING_CATALOG` rows whose `act_key` the player currently owns through the existing counter-gated unlock projection (no new unlock system; advanced rows reference the Series D acts by shared key). Acceptance SHALL read the NPC's arousal ordinal, map it through the monotonic `acceptance` curve, and resolve via `roll_d100` through the existing injected-dice gate; affinity SHALL play no role. On accept, the act SHALL execute through the existing action-resolution pipeline (all pleasure/shame/exposure/counter rails run normally on both bodies) and the same transaction SHALL add the row's merit plus its copper payout, emitting `church_offering_accepted`; on decline, `church_offering_declined` with zero writes, no penalty, and no cooldown. Normal partnered sex outside the offering flow SHALL be byte-identical.

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

### Requirement: Climax accrual rides the side-reaction rail and fails closed for the unenrolled
A `climax_while_enrolled` accrual row SHALL ride the same side-reaction rail as `state_reactions.yaml` rows: entering 進行中 while enrolled adds a small configured merit. The enrollment condition SHALL fail closed: an unenrolled entity's climax settlement (accrual, event, and byte-level writes) SHALL stay byte-identical to before this change.

#### Scenario: An enrolled climax credits merit once per entry
- **WHEN** an enrolled character's climax phase transitions into 進行中
- **THEN** the configured accrual applies exactly for that transition

#### Scenario: Unenrolled climaxes are byte-identical
- **WHEN** an unenrolled character completes the identical climax sequence
- **THEN** every write matches the pre-change baseline

### Requirement: The accrual paths are offline-deterministic with commit-bound observability
No `world/ai/` module SHALL participate in prayer, offering, or climax accrual (AI is prose overlay only). Their state writes SHALL sit inside `transaction.atomic()`, and their events SHALL flow only through the `world.observability` facade with plain-data contexts (`char`, `npc`, `row`, `tick`): `church_pray`, `church_offering_accepted`, `church_offering_declined` (`church_enrolled` lands with enrollment; `church_skill_redeemed` with redemption). Every event SHALL be commit-bound (a rolled-back transaction emits nothing), and every failure mode SHALL have a stable rejection message (not enrolled, outside venue, daily cap, row not unlocked, NPC declined). The full cross-loop end-to-end AI-dead integration proof is landed by the combat-ministry change; this one covers its own paths.

#### Scenario: The accrual paths run with AI dead
- **WHEN** pray → offer (accept and decline branches) → climax accrual execute with every LLM service unavailable
- **THEN** each step produces its deterministic mechanical result and the three events are observed at commit

#### Scenario: Rollbacks emit nothing
- **WHEN** any church transaction is rolled back after its event registration
- **THEN** no facade event for that transaction appears

### Requirement: The church pray and offer commands are documented in the docs trio
The player commands `church pray` and `church offer <npc> [row_key]` SHALL be documented in `docs/game/commands.md` and `docs/game/command-reference.md` in the same change, with `tests/test_command_docs.py` green over the new surface. `church join` is already documented by the enrollment change; `church redeem`/`merit` arrive with the redemption change.

#### Scenario: Docs and commands agree
- **WHEN** the command-docs test runs against the shipped church commands
- **THEN** `pray` and `offer` appear in both documents alongside the already-documented `join`, and the test passes

### Requirement: Redemption is a one-shot, all-or-nothing grace purchase
`church redeem list` SHALL print the catalogue with current merit and redeemed marks. `church redeem <key>` SHALL validate (row exists ∧ not already redeemed ∧ merit sufficient ∧ catalogue-internal prereqs met — a plain list of other catalogue keys, never lineage machinery), then in ONE transaction subtract merit, write the skill through the sanctioned granted-skill write (PASSIVE rows to `db.skills.passive`, ACTIVE rows to `db.skills.active`), append the key to `redeemed`, and emit `church_skill_redeemed`. Any failure SHALL leave merit, skills, and `redeemed` untouched with a stable rejection (unknown key, repeat redemption, insufficient merit, unmet prereq). Repeat redemption SHALL be impossible. `saintess_vessel` SHALL NEVER appear in the redemption catalogue at any price — pinned by a permanent negative-set test — and the existing PASSIVE practice/unlock/conferral guards SHALL stay untouched and green (the pipeline is the sanctioned channel, not a bypass). `church merit` SHALL print the ledger (merit, enrollment day, redeemed marks, daily prayer usage) read-only.

#### Scenario: A funded redemption writes the skill atomically
- **WHEN** an initiate with sufficient merit redeems an affordable, prereq-met row
- **THEN** merit decreased by the price, the skill is in the right `db.skills` store for its kind, the key is in `redeemed`, and one `church_skill_redeemed` event logged at commit

#### Scenario: Every rejection is inert
- **WHEN** redemption is attempted for an unknown key, an already-redeemed key, insufficient merit, or unmet prereq
- **THEN** the matching stable rejection returns and every store is byte-identical

#### Scenario: The vessel is never purchasable
- **WHEN** the redemption catalogue is enumerated
- **THEN** `saintess_vessel` is absent, and `church redeem saintess_vessel` is the unknown-key rejection

#### Scenario: Rollback mid-redemption leaves everything
- **WHEN** the redemption transaction is forced to fail after the merit subtraction
- **THEN** merit, skills, and `redeemed` equal their pre-attempt values and no event emits

### Requirement: Series A/B/D rows ship as registry skills earned only through the church pipeline
The catalogue SHALL carry the 16 Series A/B/D rows as new `SKILL_REGISTRY` entries: Series A clergy qualifier passives `pain_to_pleasure`, `priestly_grace`, `rapture_renewal` (first-time catalogue entry — the 「聖職敘階授予」 channel itself) and new `vow_of_service` (offering copper +25% and offering/climax merit +10%, ledger multipliers only, pure-positive); Series B rite actives `rite_heal_light`, `rite_cleanse`, `rite_calm`, `rite_bless_water`, `rite_sanctify_ground`, `rite_absolution`, `rite_lamb_mark`, `rite_martyrdom_vow`; Series D sexual-ministry actives `rite_holy_kiss`, `rite_milk_blessing`, `rite_confession_bed`, `rite_anointing_touch` (doubling as advanced `OFFERING_CATALOG` rows by shared key, zero duplication). No row SHALL appear in any lineage tree, and the redemption pipeline SHALL be the only acquisition path. Price bands follow the tuned finals recorded in this change's tasks; catalogue-internal prereq chains ride the Series D high rows only. (The two combat rite rails — the lamb-seal charge buff and the martyr-vow pool filter — are separate requirements landed by the combat-ministry change; here the rows register with their declarations.)

#### Scenario: Every Series A/B/D row is a redeemable, non-lineage skill
- **WHEN** the shipped catalogue and the lineage graphs are enumerated
- **THEN** all 16 keys exist in `SKILL_REGISTRY` and the catalogue, none appears in any lineage tree or unlock rule, and each prices within its tuned band

#### Scenario: Offering rows reuse the act keys
- **WHEN** a Series D advanced offering row is selected from the offering menu
- **THEN** its `act_key` equals its redemption skill key, and the offering projection and the redemption catalogue reference the same registry row with no duplicated data

### Requirement: The church redeem and merit commands are documented in the docs trio
The player commands `church redeem [list|<key>]` and `church merit` SHALL be documented in `docs/game/commands.md` and `docs/game/command-reference.md` in the same change, with `tests/test_command_docs.py` green over the completed surface (`join` documented by the enrollment change, `pray`/`offer` by the accrual change).

#### Scenario: Docs and commands agree
- **WHEN** the command-docs test runs against the completed church command surface
- **THEN** `redeem` and `merit` appear in both documents alongside the previously documented subcommands, and the test passes

### Requirement: Lamb mark narrows monster target preference with a charging buff
`rite_lamb_mark` SHALL mount the `lamb_seal` combat buff using ONE new buff-declaration primitive `charges: int`: each transition of the bearer's climax phase into 進行中 consumes one charge; at zero the buff is removed (the seal lifts after the bearer's second climax). The primitive SHALL be tested in isolation — declaration round-trip, save/restore, the two-transition consumption sequence, and a rolled-back consumption that does not burn a charge. In `monster_behaviour_policy`, BEFORE target-strategy evaluation, if any living enemy carries `lamb_seal`, single-target candidates SHALL narrow to seal-bearers (multi-seal canonical order: player first, then ascending pk). With no seal present, every monster decision SHALL be byte-identical to today. The seal is preference, not threat: no accumulation, decay, or transfer; it ends with the fight; AREA skills are unaffected; positional markers are an orthogonal exclusion and SHALL NOT be substituted by the seal.

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

### Requirement: Martyrdom vow collapses the defeat-aftermath victim pool to the marked martyr
`rite_martyrdom_vow` cast during a fight SHALL stamp `martyr_key` (with the durable session id) on the combat session record. At defeat settlement, `_violation_pool` SHALL apply one additional filter: if the session stamp matches a non-fled pool member, the pool collapses to `[her]` and the existing single-member short-circuit returns her with zero target rolls (resist contests keep their normal draws). Victory consumes the stamp. Edge rules: the marker died before the wipe → normal pool; the marker fled → filter finds no eligible martyr → normal pool; multiple markers → first by canonical order; a session-id mismatch (stale stamp) can never fire. Rollback-retry determinism SHALL hold (the stamp is durable record state; the draws stay state-derived).

#### Scenario: The marked sister is chosen with zero target rolls
- **WHEN** a defeated fight's session carries a valid martyr stamp for a non-fled survivor in the pool
- **THEN** `_violation_pool` collapses to her and returns with zero target-selection rolls

#### Scenario: Every edge falls back to the normal pool
- **WHEN** the marker died, fled, the stamp is stale, or no stamp exists
- **THEN** the pool behaves byte-identically to the pre-change filter chain

#### Scenario: Victory consumes the stamp
- **WHEN** the marked fight ends in victory
- **THEN** the stamp is spent and a later defeat in another session cannot fire it

### Requirement: The combat rails are offline-deterministic and the full church loop runs end-to-end with AI dead
No `world/ai/` module SHALL participate in the lamb-seal narrowing, the martyr-vow pool filter, or their buff machinery. The full sub-project-1 loop — `church join` → `church pray` → `church offer` → climax accrual → `church redeem` — SHALL execute as one registered integration test with every LLM service stubbed to raise, all five observability events (`church_enrolled`, `church_pray`, `church_offering_accepted`, `church_offering_declined`, `church_skill_redeemed`) observed at their commits, and the observability lint (facade-only, commit-bound) reporting zero findings over every module the church pipeline touched.

#### Scenario: The full loop runs with AI dead
- **WHEN** join → pray → offer → climax → redeem execute with every LLM service unavailable
- **THEN** every step produces its deterministic mechanical result and all five events are observed

#### Scenario: Rollbacks emit nothing anywhere in the loop
- **WHEN** any church transaction is rolled back after its event registration
- **THEN** no facade event for that transaction appears
