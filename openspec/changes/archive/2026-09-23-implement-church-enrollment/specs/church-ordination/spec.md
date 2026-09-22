## Purpose

Adds the Light Church enrollment surface to the ordination capability: the
deterministic three-stage `church join` transaction behind a `ChurchHost`, the
subrace/sex-gated Saintess office branch without uniqueness, the unconditional
vestment handover, and the authored-data consequences — the royal preset sheds
the vessel, the robe, and all religious narrative, and the lore documents
retire the once-per-generation framing.

## ADDED Requirements

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
