# Spec Delta

## MODIFIED Requirements

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

#### Scenario: Morning devotion raises the prayer cap by its authored increment
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
