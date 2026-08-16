# sexual-catalog-interspecies Specification

## Purpose

Register the seven 異種線 acts, filling the interspecies line from its pre-declared empty tuple to
the full allotment the source catalog specifies. Tiers 1 and 2 open on `hostile_act_count` (10, then
30), Tier 3 adds a `climax_count >= 20` compound gate on 異種交合 — the sole emitter of
`sexual_activity_with_nonhuman` — and Tier 4 opens on `interspecies_act_count >= 20`. Every act
targets a single `Monster`, declares no `target_part` (異種 is a parless line), credits
`interspecies_act_count` on the actor only, and is `resistible=True`. No rulebook row is added:
`experience_interspecies_added` has shipped since the transition rulebook landed.

## Requirements

### Requirement: Seven Tier 1-4 interspecies acts are registered, gated by hostile_act_count and/or climax_count and/or interspecies_act_count thresholds
`world/skills/sexual_acts/interspecies.py`'s `INTERSPECIES_ACTS` tuple SHALL contain: two acts each
declaring `unlock={"hostile_act_count": 10}` (`interspecies_touch`, `interspecies_caress`); two acts
each declaring `unlock={"hostile_act_count": 30}` (`interspecies_entangle`,
`interspecies_receive`); one act declaring the compound gate `unlock={"hostile_act_count": 30,
"climax_count": 20}` (`interspecies_mating`); and two acts each declaring
`unlock={"interspecies_act_count": 20}` (`interspecies_domination`, `interspecies_resonance`). Every
one of these seven acts SHALL declare `target_spec=TargetSpec.SINGLE`, `target_part=None`,
`resistible=True`, `actor_counters=("interspecies_act_count",)`, and `participant_counters=()`.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 9`
- **THEN** `interspecies_touch` is absent from the returned set
- **WHEN** the same entity's `hostile_act_count` becomes `10`
- **THEN** `interspecies_touch` is present in the returned set

#### Scenario: interspecies_mating requires both hostile_act_count and climax_count, not hostile_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 30` and
  `climax_count == 19`
- **THEN** `interspecies_mating` is absent from the returned set
- **WHEN** the same entity's `climax_count` becomes `20`
- **THEN** `interspecies_mating` is present in the returned set

#### Scenario: A Tier 4 act is gated by interspecies_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `interspecies_act_count == 20` and
  `hostile_act_count == 0`
- **THEN** `interspecies_domination` is present in the returned set

#### Scenario: Casting any of the seven acts credits interspecies_act_count on the actor only, never on the Monster target
- **WHEN** entity A casts `interspecies_touch` targeting a `Monster` B, both starting at
  `interspecies_act_count == 0`
- **THEN** afterward `A.sexual.interspecies_act_count` equals `1` and `B.sexual.interspecies_act_count`
  remains `0`

### Requirement: Every act declares target_part=None, never a BODY_PARTS member
Every one of the seven acts added by this change SHALL declare `target_part=None`.

#### Scenario: A Monster target always resolves to the generic body-part channel
- **WHEN** any of the seven acts is cast with a `Monster` as the resolved target
- **THEN** `resolve_part` returns `GENERIC_BODY_PART` for that target regardless of the act's
  `actor_part`

### Requirement: interspecies_mating is the sole emitter of sexual_activity_with_nonhuman
`interspecies_mating` SHALL declare `sexual_events=("sexual_activity_with_nonhuman",)`. Every other
act added by this change SHALL declare `sexual_events=()`.

#### Scenario: Casting interspecies_mating emits sexual_activity_with_nonhuman
- **WHEN** entity A casts `interspecies_mating` targeting a `Monster` B
- **THEN** `apply_event` is invoked with event name `"sexual_activity_with_nonhuman"`, and no other
  act added by this change ever names that event

### Requirement: interspecies_receive declares the highest actor_pleasure_ratio among this change's seven acts
`interspecies_receive` SHALL declare `actor_pleasure_ratio=0.9`, strictly greater than every other
act this change adds.

#### Scenario: interspecies_receive's ratio exceeds every sibling act's ratio
- **WHEN** the `actor_pleasure_ratio` of all seven acts this change adds is compared
- **THEN** `interspecies_receive`'s value (`0.9`) is strictly greater than each of the other six

### Requirement: interspecies_mating grants the actor strictly more pleasure than interspecies_receive despite the lower ratio
`interspecies_mating` SHALL declare `base_pleasure=26`. Combined with `interspecies_receive`'s
`base_pleasure=18, actor_pleasure_ratio=0.9`, this SHALL hold even at the worst-case multiplier
combination (`普通` sensitivity, `強烈` shame, `participant_count == 2`).

#### Scenario: Worst-case actor-side gain still orders interspecies_mating above interspecies_receive
- **WHEN** `compute_pleasure_gain` is evaluated for the same actor at `普通` sensitivity (multiplier
  `1.0`), `強烈` shame (multiplier `0.65`), and `participant_count == 2` for both
  `interspecies_mating` and `interspecies_receive`
- **THEN** `interspecies_mating`'s resulting gain is strictly greater than `interspecies_receive`'s
