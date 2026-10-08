# combat-resolution Specification

## Purpose
Defines the dice-combat resolution formulas: to-hit against the recalibrated defender constant of 51, damage multipliers banded by margin of success with a magnitude-only critical, effective_power combining four effective stats multiplied by max HP, and agility-dominant initiative with d100 jitter. Covers the round-based turn loop's time accounting and upkeep, the actions_per_turn skip, the first-actor override, and golden fixed-seed exchange tests.

## Requirements

### Requirement: To-hit uses a recalibrated defender constant of 51, not the design doc's original 60
`world/rules/rulebook/combat.yaml` SHALL declare `to_hit.defender_constant: 51`. A hit SHALL occur when
`roll_d100() + attacker_effective_agility >= defender_constant + defender_effective_agility`, where both
agility values are read through `SkillHandler.effective_value("agility")` (change 5), adjusted by any
`agility` percentage modifier `evaluate_combat_modifiers()` (change 6) returns for that entity, plus any
`accuracy` modifier the attacker's own bundle returns.

#### Scenario: Exact agility parity yields a 50% hit chance
- **WHEN** attacker and defender have identical effective agility (after modifiers) and 10,000
  `roll_d100()`-driven to-hit checks are run
- **THEN** the observed hit rate is within a small statistical tolerance of 50%, matching
  `(50 + 0) / 100` from design.md D-2's derivation

#### Scenario: A cross-race agility gap saturates to a guaranteed outcome
- **WHEN** a to-hit check is run with an attacker/defender effective-agility difference of 50 or more
  in either direction
- **THEN** the hit rate is exactly 0% (attacker's agility deficit) or exactly 100% (attacker's agility
  surplus), with no roll capable of changing the outcome

#### Scenario: A same-tier or adjacent-tier agility gap never fully saturates
- **WHEN** a to-hit check is run with an attacker/defender effective-agility difference within the
  range any two `STATIC_TIER_REGISTRY` entries for the same race produce (at most 30 points)
- **THEN** the resulting hit rate is strictly between 0% and 100%

#### Scenario: A natural roll of 100 does not override a saturated miss
- **WHEN** an attacker whose effective-agility deficit against the defender is 50 or more rolls the
  maximum possible value on `roll_d100()`
- **THEN** the action still misses — no natural-roll override exists that can defeat the deliberate,
  calibrated saturation from design.md D-2

### Requirement: Damage multiplier is banded by margin of success, with a magnitude-only critical on a
natural 100
`world/rules/rulebook/combat.yaml`'s `damage` section SHALL declare `crit_multiplier`,
`solid_hit_margin`, `solid_hit_multiplier`, `base_multiplier`, and `floor`. Damage SHALL be
`max(round(effective_attack_stat * roll_multiplier * effect_potency) - effective_defense, floor)`,
`roll_multiplier` being `crit_multiplier` on a raw unmodified `roll_d100()` of 100, else
`solid_hit_multiplier` at margin >= `solid_hit_margin`, else `base_multiplier`.

#### Scenario: A bare hit uses the base multiplier
- **WHEN** an attack hits with a margin of success below `solid_hit_margin` and the raw roll is not 100
- **THEN** damage is computed using `base_multiplier`

#### Scenario: The calculation runs only after a successful to-hit check

- **WHEN** damage computation is reached
- **THEN** it runs only when the to-hit check (above) already succeeded — a natural 100 does not cause a miss to become a hit

#### Scenario: A comfortable hit uses the solid-hit multiplier
- **WHEN** an attack hits with a margin of success at or above `solid_hit_margin`
- **THEN** damage is computed using `solid_hit_multiplier`

#### Scenario: A natural 100 always applies the critical multiplier regardless of margin
- **WHEN** an attack's raw, unmodified `roll_d100()` result is exactly 100 and the attack hits
- **THEN** damage is computed using `crit_multiplier`, even if the margin of success would otherwise
  have qualified only for `base_multiplier`

#### Scenario: Damage never drops below the floor
- **WHEN** `effective_attack_stat * roll_multiplier - effective_defense` computes to a value at or
  below zero
- **THEN** the applied damage equals `damage.floor`, never zero or negative

#### Scenario: A miss deals no damage and applies no floor
- **WHEN** the to-hit check fails
- **THEN** no damage is applied to the target's `hp`, and the damage floor does not apply (a miss is
  not a "zero-damage hit")

#### Scenario: Conditional damage preserves nonlethal outcome
- **WHEN** a configured defense bypass and maximum-HP component would cross a protected target below zero
- **THEN** final HP is 1 with one knockout outcome and no ordinary defeat

#### Scenario: Freeform scaling follows every damage component
- **WHEN** a freeform-scaled cast of a skill carrying a maximum-HP component hits
- **THEN** the declared freeform magnitude scaling applies after the maximum-HP component is added, so the rider is scaled by the same stage rather than remaining unscaled

#### Scenario: Unconditional execution bypass ignores any target's defense
- **WHEN** a synthetic policy with `bypass_defense=True` and an empty predicate damages a high-defense
  and a low-defense target, and separately authoring attaches an attack multiplier to an empty predicate
- **THEN** both hits subtract no defense while the identical coefficient without bypass differs by the
  targets' defense, and the multiplier-with-empty-predicate authoring still raises at construction

#### Scenario: Divert runs after the full formula and pays from the named gauge
- **WHEN** a synthetic divert profile (fraction, cap) is active on a target whose authored hit amount
  (post-defense, post-rider, post-scale) exceeds the fraction's product with the target's budget
- **THEN** exactly `round(amount × fraction)` capped by remaining budget and current gauge is paid
  from the gauge through the canonical writer, HP drops only by the residual, and the same roll
  without the profile delivers the full authored HP amount

#### Scenario: Budget, gauge shortage and expiry bound the divert
- **WHEN** successive hits exhaust the cumulative cap, one hit exceeds the holder's remaining gauge,
  and a later hit lands after expiry
- **THEN** each divert equals the minimum of its three bounds, cap exhaustion stops all further
  diversion while the duration lives, an expiry restores full damage, and no stage ever diverts more
  than the incoming residual

#### Scenario: Stacked profiles follow one deterministic residual order
- **WHEN** two synthetic divert profiles with different definition keys are active on one hit
- **THEN** they apply in definition-key-ascending order each against the previous residual, the two
  payments plus final HP loss sum exactly to the incoming amount, and repeated resolution never
  reorders them

#### Scenario: Feedback and defeat see only the HP residual
- **WHEN** a diverting hit would otherwise cross the holder's HP through zero and a loss-driven
  reaction listener is qualified
- **THEN** the listener and any defeat projection observe only `amount − diverted`, the diverted MP
  payment is attributed to the profile's grant-time source, and a commit failure restores HP, gauge
  and consumed budget together

#### Scenario: effect_potency is the validated per-effect coefficient

- **WHEN** damage is computed for a configured effect
- **THEN** `effect_potency` is the validated per-effect coefficient, defaulting to 1.0

#### Scenario: A conditional policy uses the matched attack multiplier once

- **WHEN** a declared conditional policy's damage is computed
- **THEN** the attack component additionally uses the matched attack multiplier once

#### Scenario: Defense is zero only under a matched or unconditional bypass

- **WHEN** a declared conditional policy resolves defense
- **THEN** defense is zero only when its configured bypass predicate matches or the policy declares the unconditional execution-tier bypass — `bypass_defense=True` with an empty predicate, which validates at construction (an attack multiplier with an empty predicate stays invalid)

#### Scenario: The maximum-HP component is added after defense subtraction

- **WHEN** a declared conditional policy with a maximum-HP fraction hits
- **THEN** floor(max_hp * declared_fraction) is added after defense subtraction on a successful hit

#### Scenario: Existing ordering rules follow the new components

- **WHEN** damage components are combined
- **THEN** the existing damage floor, freeform magnitude scaling and final floor follow these components, and unconfigured effects retain the ordinary formula

#### Scenario: Divert profiles are validated buff profiles with gauge, fraction, and cap

- **WHEN** the damage stage consults divert handling after the full authored amount pipeline completes
- **THEN** it reads only the target's ACTIVE validated divert profiles — a `modifiers.divert` buff profile naming a gauge, a fraction in (0,1] and a cumulative cap

#### Scenario: Each divert converts a bounded share of the residual

- **WHEN** an active divert profile applies to a residual
- **THEN** it converts `min(round(residual * fraction), cap − consumed, owner's current gauge amount)` of the RESIDUAL into a payment from the owner's gauge through the canonical resource writer, the reduced HP amount is the only HP write staged, and the payment is attributed to the profile's persisted grant-time source

#### Scenario: Diversion never fakes HP loss and never runs on a miss

- **WHEN** damage is diverted, a miss or zero-amount hit lands, or a diverting commit is rolled back
- **THEN** diverted damage is not reported as HP loss to loss-driven feedback, a miss or zero-amount hit neither stages a divert nor consumes budget, and a rolled-back commit restores the gauge payment and consumed budget

#### Scenario: Budget accounting follows the retain-or-replace posture

- **WHEN** consumed-budget accounting is loaded
- **THEN** it follows the loaded retain-or-replace posture: a fresh cast's grant replaces the instance budget, a data-omitting refresh retains it

#### Scenario: Nonlethal projection runs before defeat consumers

- **WHEN** a diverting or rider-bearing hit approaches zero
- **THEN** the existing nonlethal projection applies before defeat/knockout event consumers

### Requirement: effective_power combines four effective stats multiplied by max hp
`world/rules/combat.py` SHALL provide `effective_power(entity) -> float`, computed as the sum of
`SkillHandler.effective_value()` for `atk_phys`, `agility`, `defense`, and `magic_power`, multiplied by
`max(entity.traits.hp.max, 0)` — the entity's race/tier hp ceiling, never its current, depletable hp
value. This function SHALL NOT write to any entity attribute.

#### Scenario: effective_power reads every stat through effective_value, never raw traits
- **WHEN** an entity has an active stat-multiplier skill (e.g. 身體強化) affecting `atk_phys`
- **THEN** `effective_power()`'s result reflects the multiplied value, not `entity.traits.atk_phys.value`

#### Scenario: An elf's effective_power vastly exceeds a human elite's, driven by max hp
- **WHEN** `effective_power()` is computed for an elf reference character (e.g. stats matching Yuka,
  88/92/90, max hp 10000) and a human-elite reference character (e.g. stats matching Lidzia, 8/9/7, max
  hp 120)
- **THEN** the ratio of the elf's `effective_power()` to the human's is at least 100 — large enough
  that a downstream overwhelm check (change 10) could treat this matchup as overwhelming, unlike a
  stat-only ratio which would understate the gap to roughly 10

#### Scenario: A mid-tier monster's effective_power exceeds a human elite's without becoming overwhelming
- **WHEN** `effective_power()` is computed for a mid-tier monster (`MonsterTier["mid"]`'s band, e.g.
  16/16/16, max hp 300) and a human elite (Lidzia-equivalent, max hp 120)
- **THEN** the ratio of the monster's `effective_power()` to the human's is greater than 1 but well
  below 100, reflecting a fight that requires a party rather than one that is mathematically decided

#### Scenario: effective_power is unaffected by current-hp attrition within a fight
- **WHEN** `effective_power()` is computed for the same entity at full current hp and again after its
  `entity.traits.hp.value` (not `.max`) has been reduced by combat damage, with no change to its
  `effective_value()` outputs
- **THEN** both computations return the identical value — attrition is represented by the turn loop's
  own death check and the hp gauge itself, not by this function

#### Scenario: effective_power changes when a true effective stat changes mid-fight
- **WHEN** `effective_power()` is computed for the same entity before and after a stat-multiplier
  skill (e.g. 身體強化) becomes active
- **THEN** the second computation differs from the first; `disguised_stats` is never read because it
  is display-only under architectural decision D2

#### Scenario: A current-hp-driven ratio would misrepresent a saturated matchup — the case that ruled it
out
- **WHEN** `effective_power()` is computed for an elf reduced to a small fraction of current hp against
  a full-current-hp human elite, using **max** hp as specified above
- **THEN** the ratio still favors the elf by roughly the same margin as the full-hp case (≈677, per
  D-4's worked table) — it does NOT flip to favor the human, even though the human's own current-hp
  advantage is large, because current hp plays no role in this function; a `damage-effect-handlers`- or
  `combat-resolution`-level to-hit check on this same matchup independently confirms the human's hit
  rate remains 0% (saturated) regardless of either combatant's current hp, so no consumer of either
  signal is misled by hp attrition

### Requirement: Initiative order is agility-dominant with d100 jitter
`world/rules/combat.py` SHALL provide `roll_initiative(battlefield) -> list[str]`, returning roster
keys ordered to act, computed as `effective_agility * initiative.agility_weight + roll_d100()` per
entity, sorted descending. `rulebook/combat.yaml` SHALL declare `initiative.agility_weight`.

#### Scenario: A large agility gap guarantees turn order regardless of the jitter roll
- **WHEN** two combatants' effective agility differs by at least `agility_weight` (10)
- **THEN** the higher-agility combatant's initiative score is greater than the lower-agility
  combatant's for every possible pair of `roll_d100()` outcomes

#### Scenario: A small agility gap can be reordered by the jitter roll
- **WHEN** two combatants' effective agility differs by less than `agility_weight`
- **THEN** there exists at least one pair of `roll_d100()` outcomes for which the lower-agility
  combatant's initiative score exceeds the higher-agility combatant's

### Requirement: The turn loop reports elapsed time as rounds times 6 seconds and never advances a clock
`world/rules/combat.py`'s `run_battle()` SHALL return a `total_seconds` value equal to
`rounds_elapsed * 6` (design doc §6.3). No function in `world/rules/combat.py` SHALL call
`WorldClock.advance()` or any equivalent — this change reports a time cost and does not itself cause
time to pass.

#### Scenario: A three-round battle reports 18 seconds
- **WHEN** `run_battle()` completes after exactly 3 rounds
- **THEN** `total_seconds == 18`

#### Scenario: No WorldClock call exists anywhere in this change's code
- **WHEN** `world/rules/combat.py`'s and `world/rules/dice.py`'s source is inspected
- **THEN** neither file references `WorldClock` or calls anything named `advance()`

### Requirement: Per-round upkeep ticks buffs and advances sexual decay by the round duration
`world/rules/combat.py`'s per-round upkeep SHALL call change 6's `tick_buffs(entity)` for every living
roster member unconditionally and SHALL call change 7's
`world.rules.sexual_state.decay_tick(entity, round_seconds)` with the configured round duration.

#### Scenario: Buff ticks run every round with no self-arming guard
- **WHEN** a round completes with a poisoned combatant present
- **THEN** `tick_buffs()` is called for that combatant exactly once, unconditionally, with no
  try/except around the call

#### Scenario: Sexual decay accumulates exactly one round of elapsed time
- **WHEN** a round completes for a living roster member
- **THEN** `decay_tick` is called once for that entity with
  `COMBAT_YAML["round"]["seconds"]`

#### Scenario: A roster member in 進行中 with no staged extension climaxes by the end of the round
- **WHEN** a round completes for a living roster member whose `climax_phase` is `進行中` and who has no
  staged climax extension
- **THEN** `climax_ends` fires for that entity during that round's upkeep, immediately after
  `decay_tick`, and `climax_phase` becomes `餘韻`

#### Scenario: A roster member in 進行中 with a staged extension remains locked for another round
- **WHEN** a round completes for a living roster member whose `climax_phase` is `進行中` and who has an
  extension staged via `stage_climax_extension()`
- **THEN** `climax_extended` fires for that entity during that round's upkeep instead of `climax_ends`,
  and `climax_phase` remains `進行中`

#### Scenario: Upkeep tick records reach the round settlement
- **WHEN** a round completes with a `fire_scorch`-afflicted living roster member whose tick fires
- **THEN** the round's EventLogs include the tick's `damage` entry and, on a lethal crossing, a single `target_defeated` entry, staged with the round's other effects

#### Scenario: Round policy flags reach the upkeep settlement
- **WHEN** `run_round` is called with `simulated=True` or with `nonlethal_keys` naming a roster member
- **THEN** upkeep defeat entries are tagged `simulated` with no kill credit, and protected members floor at 1 HP and are marked knocked out instead of defeated

#### Scenario: Climax settlement follows decay_tick immediately

- **WHEN** upkeep finishes `decay_tick` for a living roster member
- **THEN** it immediately calls `world.rules.sexual_state.climax_settlement_action(entity)` and, when that returns `"extend"` or `"end"`, emits the correspondingly named event (`climax_extended` or `climax_ends`) through `world.rules.sexual_transitions.apply_event()`

#### Scenario: Damaging tick records feed the round's upkeep settlement

- **WHEN** `tick_buffs` returns damaging tick records for roster members
- **THEN** the upkeep collects them per roster member and hands them to the round's upkeep settlement (`world/rules/upkeep.py`) so the round's EventLogs and staged effects include the settled tick damage, defeat crossings, and quest effects

#### Scenario: run_round accepts and forwards the policy flags

- **WHEN** `run_round` is invoked
- **THEN** it accepts keyword-only `simulated` and `nonlethal_keys` policy flags and forwards them to the upkeep settlement

### Requirement: The turn loop consumes actions_per_turn as the round's action count, with zero skipping before ActionResolver is called
`world/rules/combat.py`'s `run_round()` SHALL consult each acting combatant's combat-modifier
evaluation (the merged bundle and the matched rules' per-rule bundles) and consume the table's
`actions_per_turn` output as that combatant's action count for the round. The zero-lock decision
SHALL read the matched rules' per-rule zero-action results, and every entity not locked SHALL
provision its count from the merged bundle's positive `actions_per_turn` value.

#### Scenario: A climax-in-progress combatant's turn is skipped, not attempted
- **WHEN** `evaluate_combat_modifiers(entity)` returns `{"actions_per_turn": 0}` for the acting
  combatant
- **THEN** `ActionResolver.resolve()` is never called for that combatant this round, and the round's
  event list contains an `"action_skipped"` entry naming that combatant

#### Scenario: No source-level branch distinguishes the modifier's origin
- **WHEN** `world/rules/combat.py`'s source is inspected
- **THEN** it contains no conditional that special-cases a sexual-origin `actions_per_turn` modifier
  differently from a buff-origin one — both are read from the identical bundle key

#### Scenario: An absent or one-valued key resolves exactly one action
- **WHEN** a round runs with every combatant's bundle carrying no `actions_per_turn` key or the
  value `1`
- **THEN** each capable combatant receives exactly one provider interaction and the round's event
  sequence matches the pre-widening behaviour value-for-value

#### Scenario: A count of two grants a second slot at the same position and a mid-round defeat cuts it
- **WHEN** a synthetic bundle gives one combatant `actions_per_turn: 2`, the provider returns a
  resolvable request for both slots, and a separate fixture has an earlier actor's strike defeat or
  knock out that combatant after its first slot lands
- **THEN** the first fixture's combatant resolves two provider interactions inside the one round
  transaction with both events ordered after its original sequence position, and the second
  fixture's combatant resolves only its first slot with no event and no provider call for the
  cut slot

#### Scenario: A runaway bundle hits the fuse, not an unbounded loop
- **WHEN** a synthetic merge produces an `actions_per_turn` value above the loop's declared maximum
- **THEN** the combatant provisions exactly the declared maximum number of slots and round
  resolution completes without error

#### Scenario: An action lock dominates a co-existing grant
- **WHEN** a synthetic combatant simultaneously matches a shipped-shaped `actions_per_turn: 0`
  lock rule and a `+1` extra-action grant rule whose generic numeric merge alone would read as a
  positive count
- **THEN** the lock leg is evaluated first and skips the combatant's whole turn (chance rules
  resolving per the chance requirement) with no provider call, exactly as a lone lock does today

#### Scenario: Slots re-check liveness inside the single round transaction

- **WHEN** a combatant's provisioned action slots are requested during the round
- **THEN** each slot re-checks the round's liveness predicate (fled, knocked out, or depleted) before requesting an action, so a combatant defeated or knocked out by an earlier actor's settlement loses its remaining slots without an event, and the round's settlement stays one transaction per round either way

#### Scenario: Pre-widening bundles resolve byte-identically

- **WHEN** any bundle shipped before this widening — none of which co-matches a grant with a lock — is read
- **THEN** an absent `actions_per_turn` key means one action and the bundle resolves byte-identically to pre-widening behavior

#### Scenario: Only output keys are read, never rule identities

- **WHEN** the loop reads the combat-modifier rules' output
- **THEN** it reads the output keys only, with no branch distinguishing which underlying rule (poison, paralysis, arousal, climax phase, or an extra-action grant) produced the value

#### Scenario: A matched zero-action rule skips the turn outright

- **WHEN** an entity matches any zero-action rule
- **THEN** its turn is skipped entirely (producing an `EventLog` with kind `"action_skipped"`) without calling `ActionResolver.resolve()`

### Requirement: Golden fixed-seed tests cover a normal exchange and a lopsided exchange
`world/rules/tests/` SHALL contain a fixed-seed golden test for a same-tier ("normal") combat exchange
and a separate fixed-seed golden test for a cross-race ("lopsided") exchange, per design doc §10.

#### Scenario: The normal-exchange golden test asserts an exact hit/miss/damage sequence
- **WHEN** the normal-exchange golden test runs under its fixed seed
- **THEN** it asserts the exact sequence of hit/miss outcomes and damage values `roll_d100()` produces
  for that seed, failing if the to-hit constant, damage bands, or initiative weight are ever changed
  without updating the fixture

#### Scenario: The lopsided-exchange golden test asserts full saturation for the entire fixture
- **WHEN** the lopsided-exchange golden test (elf attacker vs. human-elite defender, and the reverse)
  runs under its fixed seed for multiple rounds
- **THEN** every attack from the elf attacker hits and every attack from the human attacker misses,
  regardless of the specific roll values the seed produces

### Requirement: Skill heal magnitude scales by the merged heal_gain percent

The skill-heal magnitude funnel SHALL read the caster's magic stat through the
same equipment-adjusted magic path as magic-school damage, and SHALL apply the
merged bundle's `heal_gain` signed percentage with one normative formula:
`max(floor(base_amount × (1 + percent/100)), heal.floor)`.

#### Scenario: Holy gear amplifies a skill heal

- **WHEN** an actor wearing a `heal_gain +20%` accessory casts a heal whose
  unamplified base amount is 40
- **THEN** the restored amount is 48, capped at the effective maximum

#### Scenario: Rounding is floored, not banker-rounded

- **WHEN** the unamplified base amount is 3 and `heal_gain` is +20%
- **THEN** the restored amount is 3 (floor of 3.6), not 4

#### Scenario: Potions ignore heal_gain

- **WHEN** the same actor drinks a registered healing potion
- **THEN** the restore amount equals the item-effect rulebook amount exactly

#### Scenario: The merged percentage is rule-table and equipment contributions

- **WHEN** the funnel reads `heal_gain`
- **THEN** it applies the merged bundle's signed percentage with rule-table and equipment contributions merged

#### Scenario: The unamplified base amount is computed as today

- **WHEN** the funnel computes `base_amount` before amplification
- **THEN** the unamplified base amount is computed as today: `max(round(adjusted_magic × multiplier), heal.floor)`

### Requirement: run_round accepts an optional first-actor override that reorders the rolled sequence and nothing else
`world/rules/combat.py`'s `run_round()` SHALL accept a keyword-only
`first_actor: str | None = None`. When it is `None`, `run_round()` SHALL behave exactly as it does
without the parameter, including the call it makes into `roll_initiative()`. When it names a key
present in `roll_initiative(battlefield)`'s returned sequence, `run_round()` SHALL move that key to
the head of the sequence and SHALL preserve the relative order of every other key, then iterate the
resulting order.

#### Scenario: The named combatant acts first while everyone else keeps their rolled relative order
- **WHEN** `run_round(battlefield, provider, first_actor=key)` runs under a fixed seed for a
  battlefield in which `roll_initiative()` would not have placed `key` first
- **THEN** `key`'s action resolves before every other combatant's, and the remaining combatants act
  in the same relative order they would have under the identical seed with `first_actor=None`

#### Scenario: The override changes order only, never the number of actions
- **WHEN** the same round is run twice under a fixed seed, once with `first_actor=key` and once with
  `first_actor=None`
- **THEN** both rounds resolve exactly one action per capable combatant, and the multiset of acting
  keys is identical between the two runs

#### Scenario: roll_initiative is still the only source of order
- **WHEN** `run_round()`'s implementation is inspected
- **THEN** it obtains its iteration order from `roll_initiative(battlefield)` and applies the
  override as a reordering of that returned sequence, with no alternative scoring path and no extra
  `roll_d100()` call attributable to the override

#### Scenario: A first_actor of None is byte-identical to the pre-parameter behavior
- **WHEN** a round is resolved with `first_actor` omitted and again with `first_actor=None` under
  the identical seed and starting battlefield
- **THEN** every entity's final hp, the emitted `EventLog` sequence including every `"roll"`-kind
  entry's recorded value, and the acting order are identical

#### Scenario: A stale or ineligible first_actor key is a silent no-op
- **WHEN** `run_round()` is called with a `first_actor` naming a combatant who is dead, has fled, is
  knocked out, or is not in the roster at all
- **THEN** the round resolves in the unmodified rolled order without raising, and no combatant is
  added to or removed from the sequence

#### Scenario: Honoring the override never changes action counts

- **WHEN** `run_round()` honors a `first_actor` override
- **THEN** it does not re-roll, re-score, or bypass `roll_initiative()` to honor the override, does not grant the named combatant an additional action, and does not skip any other combatant

#### Scenario: An absent first_actor key never raises

- **WHEN** `first_actor` names a key absent from the rolled sequence — a dead, fled, knocked-out, or non-roster key
- **THEN** the override is a silent no-op that leaves the rolled order untouched and does not raise

### Requirement: The round loop folds declarative in-round order operations into its sequence
`world/rules/combat.py`'s round loop SHALL treat the initiative sequence as a per-round snapshot
that declarative position markers may reshape before each remaining combatant's turn: a live buff
instance whose definition declares an in-round order operation relocates its holder's not-yet-acted
key within the snapshot.

#### Scenario: An advance marker moves a not-yet-acted combatant ahead of the remaining tail
- **WHEN** a synthetic buff instance declaring an advance operation is live on a combatant that has
  not acted yet this round, applied before its original turn by an earlier actor's settlement
- **THEN** that combatant acts ahead of every other combatant still to act this round, every other
  key's relative order is unchanged, and the following round's order is again the rolled order

#### Scenario: A retreat marker pushes hit combatants to the tail and cannot reach an already-acted key
- **WHEN** a settlement applies a retreat-declaring marker instance to a struck combatant that has
  not acted yet this round, and an identical instance lands on a combatant that already acted
- **THEN** the first combatant moves behind every combatant still to act this round while the
  second keeps its completed turn with no further action, and no round's rolled sequence is mutated

#### Scenario: Actions stay one-per-slot through a relocation
- **WHEN** a combatant is relocated by an order operation and its action count for the round is
  taken from the modifier bundle
- **THEN** the relocation changes only WHEN the combatant acts, never HOW MANY times, and the
  combatant's action count is not altered by any order operation

#### Scenario: Advance moves ahead and retreat moves behind the remaining tail

- **WHEN** an in-round order operation relocates a not-yet-acted key within the snapshot
- **THEN** an advance operation moves the key ahead of the combatants still to act, a retreat operation moves it behind them, and same-key operations collapse last-declared-wins

#### Scenario: Operations on ineligible keys are silent no-ops

- **WHEN** an operation names a combatant that already acted this round, fled, or was never in the sequence
- **THEN** it is a silent no-op

#### Scenario: Markers are the single declarative source of order changes

- **WHEN** effect resolution wants to change turn order
- **THEN** it never mutates the initiative sequence directly — the marker instances are the single declarative source the loop reads, and the next round's sequence is produced by the untouched round-start roll

#### Scenario: The shipped first-actor override is untouched

- **WHEN** in-round order operations exist alongside the opening-only first-actor override
- **THEN** the shipped override and its move-to-head semantics stay exactly as written

### Requirement: A declared action-loss chance gates the round skip with one recorded roll
A combat-modifier rule's zero-action lock MAY declare a probability for the loss, validated fail
closed at rule load (the declaration is legal only alongside a zero action count, within the closed
percentage range). The decision SHALL read the matched rules' per-rule bundles: any matched
zero-action rule WITHOUT a declared chance SHALL force the certain skip regardless of co-existing
chances, and otherwise the maximum declared chance among matched zero-action rules SHALL decide.

#### Scenario: A chance-bearing lock skips on a losing roll and acts on a winning one
- **WHEN** a synthetic lock rule declares a chance on its zero-action `then` and fixed dice make one
  gated combatant lose and another win the per-round contest
- **THEN** the loser produces the `action_skipped` event whose data records the declared chance and
  the consumed roll, the loser takes no action, and the winner resolves its normal action with no
  skip event

#### Scenario: A certainty co-existing with a chance still skips and the highest chance wins
- **WHEN** one gated combatant matches both a chance-bearing zero-action rule and a chance-free
  certain zero-action rule under fixed winning dice, and another combatant matches two
  chance-bearing zero-action rules of different declared values
- **THEN** the first combatant skips regardless of its dice — a declared chance can never
  probabilistically unlock a co-existing certainty — and the second combatant's contest is decided
  by the higher declared chance alone

#### Scenario: Modifier evaluation and preview never roll
- **WHEN** `evaluate_combat_modifiers()` and the side-effect-free action preview run against a
  chance-bearing lock's holder
- **THEN** both return their deterministic bundle/preview result, no dice value is consumed, and
  the resolution-time roll remains the single authoritative decision

#### Scenario: A malformed chance fails the rule load closed
- **WHEN** a rule declares a chance outside the closed range, on a non-zero `then` value, with a
  non-integer, or as a boolean
- **THEN** rule loading raises naming the offending rule id, and every previously valid rule file
  loads unchanged

#### Scenario: The skip leg is the sole consumer with one recorded roll

- **WHEN** a chance-decided zero is resolved in the round loop
- **THEN** `evaluate_combat_modifiers()` and its shipped generic merge have stayed pure reads that never rolled, and the loop — the sole consumer — rolls exactly once for that combatant this round using the shared dice seam: at or under the decided chance the shipped skip event is produced with its roll and chance recorded in the event data, above it the combatant acts normally

#### Scenario: An undeclared-zero lock skips with certainty as shipped

- **WHEN** a zero-action lock declares no chance and no chance-declaring rule co-matches
- **THEN** the combatant skips with certainty exactly as shipped

#### Scenario: A chance-decided winner provisions slots like an unlocked entity

- **WHEN** a combatant wins its chance contest
- **THEN** it provisions its action slots from the merged bundle's positive `actions_per_turn` value with a floor of one action exactly like an entity whose turn was never locked (co-matching grant rules count toward that count)

#### Scenario: The action preview never consumes the roll

- **WHEN** the side-effect-free action preview runs against a chance-bearing lock holder
- **THEN** it keeps reporting the deterministic bundle state without ever consuming the roll
