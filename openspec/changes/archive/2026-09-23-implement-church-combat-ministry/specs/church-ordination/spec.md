## Purpose

Adds the Light Church's combat ministry to the ordination capability: the
`charges` buff primitive with its climax-transition consumption hook, the
lamb-seal target-preference narrowing in the monster behaviour policy (with the
no-seal byte-identical baseline), the martyrdom-vow victim-pool filter (with
the no-martyr byte-identical baseline), and the end-to-end proof that the full
church loop — join → pray → offer → climax → redeem — runs offline-deterministic
with every event commit-bound.

## ADDED Requirements

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
