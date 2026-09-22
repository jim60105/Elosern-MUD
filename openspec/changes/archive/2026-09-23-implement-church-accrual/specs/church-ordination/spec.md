## Purpose

Adds the Light Church merit-earning behaviours to the ordination capability:
venue-bound, time-costed, capped prayer; the explicit-selection sexual offering
judged by the NPC's arousal ordinal and injected dice — never affinity — with
all-or-nothing settlement; the enrollment-gated climax accrual side-reaction
that fails closed for the unenrolled; and the pipeline-wide
offline-determinism / commit-bound observability contract over these paths.

## ADDED Requirements

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
