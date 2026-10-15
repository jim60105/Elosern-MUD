# Spec Delta

## MODIFIED Requirements

### Requirement: flee is a SkillDef resolved through the unmodified ActionResolver pipeline
The individual mechanism in this requirement SHALL apply to enemies and noninteractive combat. Allied interactive requests SHALL instead enter the confirmed party retreat operation before this effect is invoked.

`world/rules/disengage.py` SHALL declare `FLEE_SKILL_KEY = "flee"` and register a `SkillDef` under that
key into `world.skills.registry.SKILL_REGISTRY` with `kind=SkillKind.ACTIVE`,
`target_spec=TargetSpec.SELF`, `faction_constraint=
FactionConstraint.SELF_ONLY`, `cost={}`, `usable_out_of_combat=False`, and `effects=["disengage:self"]`.

#### Scenario: Downstream policy imports the canonical key and registration owner
- **WHEN** change 10d imports `FLEE_SKILL_KEY` from `world.rules.disengage`
- **THEN** the value is `"flee"` and importing the module has registered both the skill definition
  and disengage effect handler before the policy's request can be resolved

#### Scenario: Combat startup registers disengage without a downstream import
- **WHEN** a production process imports `world.rules.combat` before any test module or change 10d code
- **THEN** `SKILL_REGISTRY` contains `"flee"` and the `disengage` effect handler is registered

#### Scenario: flee is cast identically to any other skill, through CmdCast
- **WHEN** a player issues `cast flee` while a `BattlefieldActionContext` is the active context for
  their `ActionRequest`
- **THEN** `ActionResolver.resolve()` is invoked with `skill_key="flee"`, and no code path other than
  `ActionResolver.resolve()` applies any effect, deducts any resource, or emits an `EventLog` for it

#### Scenario: A battlefield context cannot stage a flee in another battlefield
- **WHEN** `BattlefieldActionContext` receives an `event_context` whose `"battlefield"` object is not
  the context's own battlefield
- **THEN** construction rejects the mismatch before action resolution, and a matching context always
  exposes its own battlefield in `event_context`

#### Scenario: flee targets the actor and runs all four targeting validations
- **WHEN** `resolve()` processes a `flee` request
- **THEN** target resolution runs presence, alive, range, and faction validation against the actor
  itself (per `TargetSpec.SELF`), exactly as it would for any other `SELF`-targeted skill

#### Scenario: A dead or already-fled actor cannot cast flee
- **WHEN** `resolve()` processes a `flee` request for an actor whose `hp.value` is `0`, or for an actor
  whose key is already in `battlefield.fled`
- **THEN** the action rejects with `RejectReason.TARGET_DEAD` or `RejectReason.TARGET_OUT_OF_RANGE`
  respectively, via the identical, unmodified targeting validations every other `SELF`-targeted skill
  uses — no new rejection reason is introduced for this case

#### Scenario: flee is not castable outside combat
- **WHEN** `resolve()` processes a `flee` request whose `ActionContext.battlefield` is `None`
- **THEN** the action rejects with `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT`, via action-resolver's
  existing, unmodified `usable_out_of_combat` gate — no new check is added to `action.py` for this case

#### Scenario: flee costs no mp or sp
- **WHEN** `resolve()` processes a `flee` request for an actor with zero current `mp` and zero current
  `sp`
- **THEN** step 2 (resource check) passes, since `flee`'s `cost` is `{}`

#### Scenario: A successful flee reports the same flat time cost as any other unlisted skill
- **WHEN** a `flee` request resolves successfully
- **THEN** `ActionResult.success().time_cost_seconds` equals `DEFAULT_CAST_SECONDS` (6), since `flee` has
  no entry in `SKILL_TIME_OVERRIDES`

#### Scenario: Casting flee rides the complete eight-step pipeline unchanged
- **WHEN** `flee` is cast
- **THEN** it goes through `ActionResolver.resolve()`'s complete eight-step pipeline with no new
  pipeline step, no new combat-state branch in `action.py` or `targeting.py`, and no dedicated
  command

#### Scenario: Allied interactive escape uses party confirmation
- **WHEN** an allied actor in an interactive player session requests this innate flee mechanism
- **THEN** the request is routed to confirmed party retreat before any individual effect mutates the battlefield; enemy individual flee keeps the mechanism above unchanged


### Requirement: The disengage effect handler computes flee success from the same agility-difference
The individual contest below SHALL remain the enemy and noninteractive mechanism. Allied interactive retreat SHALL use the party contest rather than invoking this individual effect.

formula and the same recalibrated constant dice-combat's own to-hit check uses
`world/rules/disengage.py` SHALL register a `disengage` effect handler via
`register_effect_handler("disengage", ..., surfaces=frozenset({"battlefield"}))`. The handler SHALL
compute success as `roll_d100() + fleeing_entity_adjusted_agility >= combat.COMBAT_YAML["to_hit"]
["defender_constant"] + fastest_pursuer_adjusted_agility`.

#### Scenario: Exact agility parity yields a 50% escape rate
- **WHEN** a flee attempt is evaluated where the fleeing entity's adjusted agility exactly equals the
  fastest living opposing combatant's adjusted agility, over 10,000 fixed-seed trials
- **THEN** the observed success rate is within a small statistical tolerance of 50%

#### Scenario: A cross-race agility gap saturates flight to a guaranteed outcome, with no special case
- **WHEN** a flee attempt is evaluated where the fleeing entity's adjusted agility differs from the
  fastest living opposing combatant's adjusted agility by 50 or more, in either direction
- **THEN** the success rate is exactly 0% (fleeing entity's deficit) or exactly 100% (fleeing entity's
  surplus), with no roll capable of changing the outcome, and no conditional in `world/rules/
  disengage.py` branches on an overwhelm ratio, an `effective_power()` value, or any
  `classify_overwhelm()`-related concept to produce this result

#### Scenario: A human cannot escape a pursuing elf
- **WHEN** a flee attempt is evaluated for a human-elite-tier fleeing entity (effective agility in
  `STATIC_TIER_REGISTRY`'s human elite band, e.g. 9) against an elf-tier pursuer (effective agility in
  that registry's elf band, e.g. 92)
- **THEN** the escape rate is exactly 0% — the same agility-difference saturation that makes the human
  unable to land a to-hit roll against that elf also makes escape from them impossible

#### Scenario: An elf can always escape a pursuing human
- **WHEN** a flee attempt is evaluated for an elf-tier fleeing entity (effective agility 92) against a
  human-elite-tier pursuer (effective agility 9)
- **THEN** the escape rate is exactly 100%

#### Scenario: The comparison uses the fastest living opposing combatant, not an average or a
player-chosen target
- **WHEN** a flee attempt is evaluated against an opposing team with multiple living, non-fled members
  of differing adjusted agility
- **THEN** the comparison uses the single greatest adjusted-agility value among them, not an average or
  any other aggregate

#### Scenario: accuracy modifiers are never read by the flee success check
- **WHEN** `_adjusted_agility()`'s implementation is inspected
- **THEN** it reads only the `agility` key of `evaluate_combat_modifiers()`'s returned bundle, never the
  `accuracy` key

#### Scenario: No living, non-fled opposing combatant makes escape automatic
- **WHEN** a flee attempt is evaluated and every member of the opposing team is dead or already fled
- **THEN** the attempt succeeds unconditionally, without calling `roll_d100()`

#### Scenario: The threshold constant is combat's own, reused verbatim
- **WHEN** the success check's `defender_constant` is sourced
- **THEN** it uses `world.rules.combat.COMBAT_YAML`'s existing constant verbatim — no new constant
  is declared for this check

#### Scenario: Agility adjustment uses the agility percentage only
- **WHEN** the adjusted-agility inputs to the success check are computed
- **THEN** they are adjusted by `evaluate_combat_modifiers()`'s `agility` percentage, never its
  `accuracy` value

#### Scenario: The pursuer term is the greatest effective_value("agility")
- **WHEN** `fastest_pursuer_adjusted_agility` is computed
- **THEN** it is the greatest `effective_value("agility")` among every living, non-fled member of
  the opposing team

#### Scenario: Allied interactive escape uses party confirmation
- **WHEN** an allied actor in an interactive player session requests this innate flee mechanism
- **THEN** the request is routed to confirmed party retreat before any individual effect mutates the battlefield; enemy individual flee keeps the mechanism above unchanged


### Requirement: A successful flee adds the fleeing entity's key to Battlefield.fled; a failed attempt
The individual mutation below SHALL remain the enemy and noninteractive mechanism. Allied interactive exit SHALL mutate the whole party only through confirmed retreat.

mutates nothing
`_handle_disengage()`'s returned `PendingEffect` SHALL, on success, stage `battlefield.fled.add(actor.
key)` as its sole mutation. On failure, it SHALL stage a no-op (`apply` performs no mutation). Neither
outcome SHALL write to any entity's `traits`, `sexual`, `buffs`, or `skill_grants`.

#### Scenario: A successful flee is reflected in Battlefield.fled after commit
- **WHEN** a `flee` request resolves successfully with the underlying attempt succeeding
- **THEN** the actor's key is present in `battlefield.fled` after `resolve()` returns

#### Scenario: A failed flee attempt leaves Battlefield.fled unchanged
- **WHEN** a `flee` request resolves with the underlying attempt failing
- **THEN** the actor's key is absent from `battlefield.fled` after `resolve()` returns, and no entity's
  `traits`, `sexual`, `buffs`, or `skill_grants` values differ from their pre-call state

#### Scenario: Both outcomes still produce a real EventLog
- **WHEN** a `flee` request resolves, whether the underlying attempt succeeds or fails
- **THEN** `ActionResult.success()` returns a non-`None` `event_log` containing an entry describing the
  attempt's outcome, and the standard flat time cost is reported in both cases

#### Scenario: Allied interactive escape uses party confirmation
- **WHEN** an allied actor in an interactive player session requests this innate flee mechanism
- **THEN** the request is routed to confirmed party retreat before any individual effect mutates the battlefield; enemy individual flee keeps the mechanism above unchanged


