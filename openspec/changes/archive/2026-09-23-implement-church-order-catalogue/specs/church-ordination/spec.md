## Purpose

Completes the 24-row redemption catalogue shipped by `implement-church-core`: the Series C discipline passives and Series E utility rows (pure-positive only, behind the iron-rule polarity gate) with their `church.yaml` rule rows and catalogue prices.

## ADDED Requirements

### Requirement: Series C discipline passives ship pure-positive with no baseline downside
The redemption catalogue SHALL gain the five Series C rows as `SKILL_REGISTRY` PASSIVE skills: `poverty_vow` (offering copper income and pray merit up — the original "shop prices rise" downside is REMOVED per the passive-no-negativity iron rule: there is no unequip-a-passive concept, so every trade-off lives in the redemption price), `obedience` (merit doubled while the holder is under a domination/submission status), `chastity_discipline` (pray merit up), `temple_endurance` (mitigates the EXISTING high-arousal defense penalty by 25% — mitigation of an existing penalty is positive relative to baseline and therefore allowed), `public_devotion` (merit from acts performed in public venues up). No Series C row SHALL carry any effect negative relative to baseline, none SHALL appear in any lineage tree, and the redemption pipeline SHALL be their only acquisition path. Their prices SHALL land inside the design's tuned bands.

#### Scenario: Every Series C passive is positive-only
- **WHEN** the shipped rule rows of each Series C passive are enumerated through the loader's polarity reading
- **THEN** each is positive-vs-baseline (or the sanctioned penalty-mitigation reading for `temple_endurance`), and the planted-downside probe (e.g. a price-increase row on `poverty_vow`) is loader-rejected

#### Scenario: Obedience doubles merit only under the status
- **WHEN** a holder earns offering/climax merit while under a domination/submission status and while not under one
- **THEN** the credit is exactly doubled in the first case and unchanged in the second

#### Scenario: Temple endurance mitigates, never adds a penalty
- **WHEN** a holder at the high-arousal defense-penalty tier is compared against baseline and against a non-holder
- **THEN** the holder's penalty magnitude is 25% smaller than baseline and the non-holder's penalty is byte-identical to the pre-change value

### Requirement: Series E utility rows feed the core loop
The redemption catalogue SHALL gain the three Series E rows: `rite_martial_blessing` (ACTIVE: pre-fight single-stat buff, cooled by the world clock), `rite_shelter` (sanctuary rest bonus recorded as a ledger flag), `rite_morning_devotion` (ACTIVE: the pray daily cap +1 — feeding the pray → merit → redeem loop). None SHALL appear in any lineage tree; the redemption pipeline is the only acquisition path; prices land inside the tuned bands.

#### Scenario: Morning devotion raises the prayer cap by exactly one
- **WHEN** a redeemed holder prays once past her base daily cap
- **THEN** the prayer succeeds, and without the skill the same prayer hit the cap's stable rejection

#### Scenario: Martial blessing is clock-cooled and single-stat
- **WHEN** `rite_martial_blessing` is cast before a fight and recast inside its cooldown
- **THEN** the first mounts exactly one stat buff and the second is the stable cooldown rejection

#### Scenario: Shelter marks the ledger, not the wallet
- **WHEN** an enrolled sister rests at a sanctuary venue holding `rite_shelter`
- **THEN** the rest bonus applies once with its ledger flag recorded, and no copper or merit moves outside the configured bonus

### Requirement: Series C/E rule rows load under the correspondence and polarity gates
Each Series C/E mechanic SHALL be tunable by a `world/rules/rulebook/church.yaml` row (no hardcoded numbers in Python), each row exercising the existing one-row-one-test correspondence gate. The core change owns the shared price BANDS (entry/mid/high) and the pray/accrual BASE values; this change decides and records its OWN eight price finals inside those bands and its own Series C/E numeric finals (scales, mitigation factor, buff magnitude, cooldown, cap increment) in the `REDEEM_CATALOG`/`church.yaml` authoring, and the correspondence tests assert those recorded finals. The catalogue SHALL enumerate 24 rows total once these 8 land, with Series C/E prereq-free (catalogue-internal prereqs stay on the Series D high rows only).

#### Scenario: One row, one test
- **WHEN** the correspondence audit runs over the grown `church.yaml`
- **THEN** every new Series C/E row has exactly one matching test

#### Scenario: The catalogue completes at 24
- **WHEN** the shipped `REDEEM_CATALOG` is enumerated
- **THEN** it holds the 16 Series A/B/D rows plus these 8, no duplicate keys, no lineage membership anywhere, and `saintess_vessel` still absent
