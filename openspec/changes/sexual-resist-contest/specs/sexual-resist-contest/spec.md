## ADDED Requirements

### Requirement: resist_verdict is a pure, two-party contest function
`world/rules/sexual_resist.py` SHALL provide `resist_verdict(actor, resister, *, rng=roll_d100) ->
ResistVerdict`, a pure function that mutates no entity state and consults no `Battlefield`. It SHALL
be callable in isolation with only two entities and an optional injectable RNG, and SHALL return a
frozen `ResistVerdict` carrying at minimum `resisted: bool`, `auto_comply: bool`, `roll: int | None`,
`actor_score: float`, and `resister_score: float`.

#### Scenario: The function requires no battlefield
- **WHEN** `resist_verdict(actor, resister)` is called with two bare entity fixtures and no
  `Battlefield` object constructed anywhere in the test
- **THEN** it returns a `ResistVerdict` with no error

#### Scenario: The function performs no state mutation
- **WHEN** `resist_verdict(actor, resister)` is called any number of times in succession
- **THEN** neither entity's traits, sexual state, or affinity records differ before and after any
  call

#### Scenario: roll is None exactly when auto_comply is True
- **WHEN** `resist_verdict()` returns a verdict
- **THEN** `verdict.roll is None` if and only if `verdict.auto_comply is True`

### Requirement: The ordinary contest reuses the shipped to-hit formula shape with blended scores
When neither auto-comply condition applies, `resist_verdict()` SHALL compute
`resisted = rng() + resister_score >= COMBAT_YAML["to_hit"]["defender_constant"] + actor_score`,
where each participant's score is `agility_component * agility_weight + atk_phys_component *
atk_phys_weight`, with `agility_weight` and `atk_phys_weight` read from
`world/rules/rulebook/sexual_resist.yaml`. The two components use different, stat-specific
adjustment treatments, matching each stat's sole existing production consumer exactly:
`agility_component` is `effective_value("agility")` adjusted via `combat._apply_percent_mod`
against `evaluate_combat_modifiers()`'s `"agility"` key, exactly as
`world.rules.disengage._adjusted_agility` computes it; `atk_phys_component` is
`effective_value("atk_phys")` plus `evaluate_combat_modifiers()`'s `"atk_phys"` key added as a flat
integer, exactly as `world.rules.combat._adjusted_attack` computes it. Neither stat's adjustment is
routed through the other stat's treatment.

#### Scenario: A resister with higher blended stats resists more often
- **WHEN** `resist_verdict()` is computed for a resister whose blended `agility`/`atk_phys` score
  exceeds the actor's, at a fixed roll value via an injected RNG
- **THEN** `resisted` is `True` at that roll value whenever the equivalent lower-scored resister's
  verdict at the same roll value would be `False`, all else equal

#### Scenario: An entity in the 極限 pleasure band resists worse via the existing arousal modifier
- **WHEN** `resist_verdict()` is computed for a resister whose `pleasure` is in the `極限` band
  (triggering the shipped `high_arousal_agility_accuracy_penalty` combat-modifier row)
- **THEN** `resister_score` reflects the `-20%` agility adjustment from `evaluate_combat_modifiers()`,
  with no new rule authored in `combat_modifiers.yaml` for this proposal

#### Scenario: The formula uses the shipped defender_constant unchanged
- **WHEN** `resist_verdict()`'s implementation is inspected
- **THEN** it reads `COMBAT_YAML["to_hit"]["defender_constant"]` rather than a locally hardcoded
  value

#### Scenario: A flat atk_phys bonus applies additively, never as a percentage
- **WHEN** `resist_verdict()` is computed for a participant owning `retainer_martial_training` or
  dual-wielding with `dual_wield_style` (both existing skills whose `combat_modifiers.yaml` row
  produces a flat `atk_phys` integer, never a percentage string)
- **THEN** that participant's blended score reflects the flat bonus added directly to
  `effective_value("atk_phys")`, and no `TypeError` or other error occurs from attempting to parse
  the flat integer as a percentage string

### Requirement: An NPC resister's affinity stage can grant a resist modifier or auto_comply
When `resister` is an `NPC` and `actor` resolves to a `PlayerCharacter`, `resist_verdict()` SHALL
look up `resister.relations.stage_for(actor)` and apply the matching entry from
`sexual_resist.yaml`'s `affinity_resist_modifier` table, keyed by the affinity stage's `id`. An
entry that is a plain number SHALL be added to `resister_score` before the contest formula runs. An
entry of the form `{auto_comply: true}` SHALL short-circuit `resist_verdict()` to
`resisted=False, auto_comply=True, roll=None` without calling `rng()`.

#### Scenario: A stranger-stage NPC gets an easier time resisting
- **WHEN** `resist_verdict()` is computed for an `NPC` resister whose affinity stage toward the actor
  is `初識` (floor 0)
- **THEN** `resister_score` includes that stage's configured positive modifier

#### Scenario: A companion at 至愛 auto-complies without rolling
- **WHEN** `resist_verdict()` is computed for an `NPC` resister whose affinity stage toward the actor
  is `至愛` (floor 90, `beloved`)
- **THEN** the result is `resisted=False`, `auto_comply=True`, `roll=None`, and `rng` is never
  invoked

#### Scenario: A companion at 絕對羈絆 also auto-complies
- **WHEN** `resist_verdict()` is computed for an `NPC` resister whose affinity stage toward the actor
  is `絕對羈絆` (floor 100, `absolute_bond`)
- **THEN** the result is `resisted=False`, `auto_comply=True`, `roll=None`

#### Scenario: A higher affinity stage's numeric modifier is never worse for the resister
- **WHEN** `sexual_resist.yaml`'s five numeric-modifier stages (`acquaintance` through `bonded`) are
  compared in ascending affinity-stage order
- **THEN** each stage's `resister_score` contribution is monotonically non-increasing (a
  higher-affinity companion is never harder to force than a lower-affinity one)

### Requirement: A Monster resister never receives an affinity term and never auto-complies from affinity
When `resister` is a `Monster`, `resist_verdict()` SHALL NOT read `resister.relations` and SHALL NOT
apply any `affinity_resist_modifier` entry; the affinity contribution to `resister_score` SHALL be
exactly `0`, and `auto_comply` from the affinity path SHALL never be `True` for a `Monster` resister.

#### Scenario: A monster resister's score has no affinity term
- **WHEN** `resist_verdict()` is computed for a `Monster` resister that has never interacted with the
  actor (its `.relations` handler holds no record)
- **THEN** `resister_score` equals the blended `agility`/`atk_phys` score alone, with no affinity
  addend

#### Scenario: A monster resister can never auto-comply via the affinity path
- **WHEN** `resist_verdict()` is computed for a `Monster` resister for any actor
- **THEN** `auto_comply` is `False` unless the climax-turn short circuit independently applies

#### Scenario: An NPC resister still receives no affinity term against a non-player actor
- **WHEN** `resist_verdict()` is computed for an `NPC` resister where `actor` is not a
  `PlayerCharacter` (for example, another `NPC` or a `Monster`)
- **THEN** `resister.relations` is not consulted, the affinity contribution to `resister_score` is
  exactly `0`, and `auto_comply` is `False` unless the climax-turn short circuit independently
  applies

### Requirement: A resister mid-climax auto-complies for the first five settlement points, then resists normally
`resist_verdict()` SHALL short-circuit to `resisted=False, auto_comply=True, roll=None` (without
calling `rng()`) whenever `resister.sexual.climax_phase.level == "進行中"` and
`resister.sexual.climax_turns <= climax_turn_auto_comply_limit` (`5`, from `sexual_resist.yaml`).
From the resister's sixth consecutive settlement point in `進行中`
(`climax_turns > climax_turn_auto_comply_limit`), the ordinary contest (including any affinity
modifier) SHALL apply.

#### Scenario: The first climax turn auto-complies
- **WHEN** `resist_verdict()` is computed for a resister whose `climax_phase` is `進行中` and
  `climax_turns` is `1`
- **THEN** the result is `resisted=False`, `auto_comply=True`, `roll=None`

#### Scenario: The fifth climax turn still auto-complies
- **WHEN** `resist_verdict()` is computed for a resister whose `climax_phase` is `進行中` and
  `climax_turns` is `5`
- **THEN** the result is `resisted=False`, `auto_comply=True`, `roll=None`

#### Scenario: The sixth climax turn rolls the ordinary contest
- **WHEN** `resist_verdict()` is computed for a resister whose `climax_phase` is `進行中` and
  `climax_turns` is `6`
- **THEN** `rng()` is invoked and the outcome follows the ordinary contest formula, including any
  applicable affinity modifier

#### Scenario: A resister not in 進行中 never triggers this short circuit
- **WHEN** `resist_verdict()` is computed for a resister whose `climax_phase` is any level other than
  `進行中`, regardless of `climax_turns`
- **THEN** this short circuit does not apply, though the affinity short circuit may still apply
  independently

### Requirement: sexual_resist.yaml validates its shape at load time
`world/rules/rulebook/sexual_resist.yaml` SHALL declare `agility_weight` and `atk_phys_weight`, each
a non-negative float, summing to exactly `1.0`, `climax_turn_auto_comply_limit` (a positive integer),
and `affinity_resist_modifier`, a mapping whose key set SHALL equal exactly the seven stage `id`s
`world.rules.affinity_config.get_config().stages` declares, with no extra or missing key. Each
value SHALL be either a finite number or the single-key mapping `{auto_comply: true}`; any other
shape SHALL raise at load time, before any `resist_verdict()` call.

#### Scenario: The weights sum to 1.0
- **WHEN** `world/rules/rulebook/sexual_resist.yaml` is loaded
- **THEN** `agility_weight + atk_phys_weight` equals exactly `1.0`

#### Scenario: The affinity table covers exactly the seven shipped stages
- **WHEN** `world/rules/rulebook/sexual_resist.yaml` is loaded
- **THEN** `affinity_resist_modifier`'s key set equals exactly
  `{stage.id for stage in get_config().stages}`

#### Scenario: A malformed weight pair fails closed
- **WHEN** a hypothetical `sexual_resist.yaml` declares `agility_weight` and `atk_phys_weight`
  summing to a value other than `1.0`
- **THEN** loading it raises, rather than silently normalizing or proceeding

#### Scenario: A negative weight fails closed even when the pair still sums to 1.0
- **WHEN** a hypothetical `sexual_resist.yaml` declares `agility_weight: 1.5` and
  `atk_phys_weight: -0.5` (summing to exactly `1.0`)
- **THEN** loading it raises, because a negative weight would invert that stat's contribution to the
  contest score

#### Scenario: A missing or extra affinity stage key fails closed
- **WHEN** a hypothetical `sexual_resist.yaml`'s `affinity_resist_modifier` omits one of the seven
  stage ids, or declares an eighth key not present in `get_config().stages`
- **THEN** loading it raises, naming the mismatched key

### Requirement: resist_verdict is deterministic under an injected RNG
`resist_verdict()`'s default `rng` parameter SHALL be `world.rules.dice.roll_d100`, and every call
site SHALL be able to substitute a fixed-value stub. Two calls with an identical stub RNG and
identical entity state SHALL return an identical `ResistVerdict`.

#### Scenario: A fixed-value RNG produces a deterministic verdict
- **WHEN** `resist_verdict(actor, resister, rng=lambda: 42)` is called twice in succession with
  unchanged entity state
- **THEN** both calls return an identical `ResistVerdict`

#### Scenario: The default RNG is the shipped dice roller
- **WHEN** `resist_verdict()` is called with no `rng` argument
- **THEN** it uses `world.rules.dice.roll_d100`, not a private reimplementation
