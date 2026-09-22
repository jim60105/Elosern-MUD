## Purpose

Defines the Light Church ordination pipeline (sub-project 1) — opened by this
change with its substrate: the `db.church` merit ledger behind a single-writer
boundary, the `church.yaml` rulebook slice behind the monotonicity and
passive-no-negativity loader gates with the one-row-one-test correspondence
gate, the frozen lore catalogues and the derived church-place set, and the
authored `ChurchHost` clergy hosts. Sibling church changes ADD their own
requirements to this capability (enrollment, accrual, redemption, combat
ministry); none modifies another's.

## ADDED Requirements

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
