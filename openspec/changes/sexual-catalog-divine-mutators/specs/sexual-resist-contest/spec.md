## MODIFIED Requirements

### Requirement: The ordinary contest reuses the shipped to-hit formula shape with blended scores
When no auto-comply condition applies, `resist_verdict()` SHALL compute
`resisted = rng() + resister_score >= COMBAT_YAML["to_hit"]["defender_constant"] + actor_score`,
where each participant's score is `agility_component * agility_weight + atk_phys_component *
atk_phys_weight`, with `agility_weight` and `atk_phys_weight` read from
`world/rules/rulebook/sexual_resist.yaml`. The two components use different, stat-specific
adjustment treatments, matching each stat's sole existing production consumer exactly:
`agility_component` is `effective_value("agility")` adjusted via `combat._apply_percent_mod`
against `evaluate_combat_modifiers_no_create()`'s `"agility"` key, exactly as
`world.rules.disengage._adjusted_agility` computes it; `atk_phys_component` is
`effective_value("atk_phys")` plus `evaluate_combat_modifiers_no_create()`'s `"atk_phys"` key added
as a flat integer, exactly as `world.rules.combat._adjusted_attack` computes it. Neither stat's
adjustment is routed through the other stat's treatment. The no-create query is load-bearing:
the live variant materializes the `sexual` handler, which persists traits on first access and
would break Requirement 1's no-mutation contract, so every contest read SHALL use
`evaluate_combat_modifiers_no_create()` and never the live `evaluate_combat_modifiers()`.

#### Scenario: A resister with higher blended stats resists more often
- **WHEN** `resist_verdict()` is computed for a resister whose blended `agility`/`atk_phys` score
  exceeds the actor's, at a fixed roll value via an injected RNG
- **THEN** `resisted` is `True` at that roll value whenever the equivalent lower-scored resister's
  verdict at the same roll value would be `False`, all else equal

#### Scenario: An entity in the 極限 pleasure band resists worse via the existing arousal modifier
- **WHEN** `resist_verdict()` is computed for a resister whose `pleasure` is in the `極限` band
  (triggering the shipped `high_arousal_agility_accuracy_penalty` combat-modifier row)
- **THEN** `resister_score` reflects the `-20%` agility adjustment from
  `evaluate_combat_modifiers_no_create()`, with no new rule authored in `combat_modifiers.yaml`
  for this proposal

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

## ADDED Requirements

### Requirement: A resister marked as submissive to a specific caster auto-complies against that caster only
`resist_verdict()` SHALL read `resister.attributes.get("submission_marks", default=frozenset(),
category="sexual_state")` directly (never through `resister.sexual`, preserving the no-create
contract) and, when `str(actor.id)` is a member of that set, SHALL short-circuit to `resisted=False,
auto_comply=True, roll=None` without calling `rng()`, exactly as the existing affinity and climax-turn
short circuits do. The check SHALL be keyed by `actor.id` (a guaranteed-unique per-instance database
identifier), never by `actor.key`/`_entity_key(actor)`, since `.key` is not guaranteed unique across
distinct entities. The check SHALL be keyed to the specific `(actor, resister)` pair — a mark naming
one caster SHALL NOT short-circuit a contest against a different actor, even one sharing the marked
caster's `.key`.

#### Scenario: A caster named in the resister's submission_marks auto-complies
- **WHEN** `resist_verdict(actor, resister)` is called and `resister`'s stored `submission_marks`
  contains `str(actor.id)`
- **THEN** the result is `resisted=False`, `auto_comply=True`, `roll=None`, and `rng()` is never
  called

#### Scenario: A mark naming a different caster does not short-circuit
- **WHEN** `resist_verdict(actor, resister)` is called and `resister`'s stored `submission_marks`
  contains some other entity's `id` but not `str(actor.id)`
- **THEN** the ordinary contest (or another applicable short-circuit) resolves the verdict, unaffected
  by the unrelated mark

#### Scenario: An entity sharing the marked caster's .key but not its id does not short-circuit
- **WHEN** `resist_verdict(other, resister)` is called, where `other.key` equals the originally-marked
  caster's `.key` but `other.id` differs (e.g. two `Monster` instances of the same species)
- **THEN** the mark does not short-circuit this contest — `str(other.id)` is not a member of
  `submission_marks`, even though `other.key` matches the marked entity's display name

#### Scenario: The submission check never materializes entity.sexual
- **WHEN** `resist_verdict()`'s implementation is inspected for its `submission_marks` read
- **THEN** it reads via `resister.attributes.get(..., category="sexual_state")`, never via
  `resister.sexual.submission_marks` or any other access that would construct a `SexualState` handler
