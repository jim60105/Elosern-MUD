## Purpose

Adds the Light Church ordination ladder to the capability: the 16 Series A/B/D
redemption rows as non-lineage registry skills with their tuned price finals,
the one-shot all-or-nothing `church redeem` / `church merit` rail writing
through the sanctioned granted-skill channel, and the permanent negative-set
pin that the Saintess vessel is never purchasable while the PASSIVE guards
stay untouched.

## ADDED Requirements

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
