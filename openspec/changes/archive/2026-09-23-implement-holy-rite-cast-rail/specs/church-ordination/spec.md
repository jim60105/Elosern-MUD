# church-ordination — delta for implement-holy-rite-cast-rail

## MODIFIED Requirements

### Requirement: The merit ledger is persisted character state with a single writer
The system SHALL keep church membership state on the character attribute `db.church`, created lazily by the first church-rules write (in practice the first enrollment transaction, once enrollment lands), carrying `merit: int` (cumulative grace 恩寵), `enrolled_tick: int`, `redeemed: [str, ...]`, `blessing_last_tick: int | null` (the `rite_martial_blessing` cooldown stamp, absent before the first cast), and `daily: {"day": int, "pray": int, "shelter"?: 1}` reset on world-clock day change (the `climax_today` pattern): the optional `shelter` marker records that today's `rite_shelter` already ran, and the day-rollover `daily.clear()` resets it with no reset code of its own. Rite cooldown and shelter state SHALL live ONLY in these ledger keys — no standalone `db.martial_blessing_last_tick` attribute and no root `shelter_rest_flag` key survive this re-pin. Only rulebook accrual rows SHALL add merit and only redemption SHALL subtract it. Merit SHALL NOT be currency: it SHALL NOT be tradeable, SHALL NOT move through any wallet path, and SHALL be spendable on nothing except the redemption catalogue; offering copper pays into the normal integer-copper wallet. Every write to `db.church` SHALL execute in `world/rules/church.py`: church commands call its mechanics functions, and the resolver's holy-rite effect handlers SHALL stage `PendingEffect`s whose committed behavior invokes a `church.py` mutator — the grep-enforceable single-writer audit stays intact across the cast-rail cut-over. Lore stays frozen-dataclass registries and commands stay thin. The ledger SHALL survive relogin/reload and every mutation SHALL be inside `transaction.atomic()`.

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


### Requirement: The accrual paths are offline-deterministic with commit-bound observability
No `world/ai/` module SHALL participate in prayer, offering, or climax accrual (AI is prose overlay only). Their state writes SHALL sit inside `transaction.atomic()`, and their events SHALL flow only through the `world.observability` facade with plain-data contexts (`char`, `npc`, `row`, `tick`): `church_pray`, `church_offering_accepted`, `church_offering_declined` (`church_enrolled` lands with enrollment; `church_skill_redeemed` with redemption; `rite_cast` with each successful holy-rite cast settlement). Every event SHALL be commit-bound (a rolled-back transaction emits nothing), and every failure mode SHALL have a stable rejection message (not enrolled, outside venue, daily cap, row not unlocked, NPC declined). The full cross-loop end-to-end AI-dead integration proof is landed by the combat-ministry change; this one covers its own paths.

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


### Requirement: Series E utility rows feed the core loop
The redemption catalogue SHALL gain the three Series E rows. `rite_martial_blessing` (ACTIVE, `holy_rite`) SHALL be a cast-rail mechanic: its registry row declares `effects=("rite_blessing:martial_blessing",)`, the `rite_blessing` handler stages the ledger cooldown stamp and the single-stat buff mount, and recasting inside the `church.yaml` cooldown window is the stable `RITE_COOLDOWN_ACTIVE` rejection — no standalone engine API participates, and time cost rides the settlement's ordinary COMMAND charge. `rite_shelter` (ACTIVE, `holy_rite`) SHALL be a cast-rail mechanic: its row declares `effects=("rite_shelter",)`, the handler gates on the church venue (`RITE_OUTSIDE_VENUE`) and the current day-block (`RITE_ALREADY_SHELTERED`), and stages the `church.yaml` `rest_bonus` hp/sp gain plus the `daily["shelter"]` marker; a new world-clock day makes the rite available again with no reset code. `rite_morning_devotion` SHALL be re-judged `PASSIVE` (its effect is the pray daily cap +1, purely ownership-triggered — a cast could only burn time), granted to `db.skills.passive` by the ordinary redemption rail and still feeding the pray → merit → redeem loop. None SHALL appear in any lineage tree; the redemption pipeline is the only acquisition path; prices land inside the tuned bands.

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
- **THEN** both settle through `settle_out_of_combat_cast` — buff mounted with its cooldown stamp,
  rest bonus applied with its day marker, one `rite_cast` event each — and a forced commit failure
  restores ledger, buffs, traits, and tick byte-identically

#### Scenario: Morning devotion is a passive grant, not a cast
- **WHEN** a sister redeems `rite_morning_devotion` and then attempts to cast it
- **THEN** the skill landed in `db.skills.passive`, the cast is the stable PASSIVE rejection, and
  her pray daily cap is raised by one from the moment of redemption

#### Scenario: Shelter re-arms after the day boundary
- **WHEN** a holder uses `rite_shelter`, the world clock crosses a day boundary, and she casts it
  again inside a venue
- **THEN** the second cast succeeds with its rest bonus, while a same-day third attempt stays the
  stable `RITE_ALREADY_SHELTERED` rejection

