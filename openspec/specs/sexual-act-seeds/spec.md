# sexual-act-seeds Specification

## Purpose

Register the seven unconditionally-available seed acts — one per targeting shape spanned across
the solo, shame, partner, and combat lines — plus the single `sexual.yaml` rule row a shame-line
act needs to raise its own `exposure`. This capability makes the act catalogue enterable from the
first round of play; the full 62-act catalog ships in later proposals.

## Requirements

### Requirement: Seven seed acts are registered with an empty unlock mapping and are unconditionally owned
`world/skills/sexual_acts/solo.py`, `shame.py`, `partner.py`, and `combat.py` SHALL each register at
least one `SexualActDef` whose `unlock` mapping is empty: `solo_self_touch`, `solo_fondle_breasts`,
and `solo_thigh_rub` in `solo.py`; `shame_hem_lift` in `shame.py`; `partner_caress` and
`partner_hand_hold` in `partner.py`; `combat_tease` in `combat.py`. Each SHALL appear in
`SkillHandler.owned_keys()` for an entity whose `SexualState` counters are all zero and whose
`base_owned_keys()` carries no `SexualMasteryEffect`-bearing skill. `world/skills/sexual_acts/
interspecies.py` and `divine.py` SHALL remain empty tuples after this change.

#### Scenario: A freshly created character owns every seed act
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with every `SexualState` lifetime
  counter at zero
- **THEN** the returned set contains all seven seed keys

#### Scenario: interspecies and divine gain no seed
- **WHEN** `world.skills.sexual_acts.interspecies.INTERSPECIES_ACTS` and
  `world.skills.sexual_acts.divine.DIVINE_ACTS` are inspected after this change
- **THEN** both remain equal to `()`

### Requirement: The four SELF-target seeds are unresistable; the three SINGLE-target seeds are resistible
`solo_self_touch`, `solo_fondle_breasts`, `solo_thigh_rub`, and `shame_hem_lift` SHALL declare
`resistible=False`. `partner_caress`, `partner_hand_hold`, and `combat_tease` SHALL declare
`resistible=True`.

#### Scenario: Every SELF-target seed is unresistable
- **WHEN** each of `solo_self_touch`, `solo_fondle_breasts`, `solo_thigh_rub`, and `shame_hem_lift` is
  read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `resistible` field is `False`

#### Scenario: Every SINGLE-target seed is resistible
- **WHEN** each of `partner_caress`, `partner_hand_hold`, and `combat_tease` is read from
  `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `resistible` field is `True`

### Requirement: A new sexual.yaml rule lets an act raise its own actor's exposure, cascading to shame within the same apply_event() call
`world/rules/rulebook/sexual.yaml` SHALL declare `exposure_up_on_self_exposure`
(`when: {event: self_exposure}`, `then: {field: exposure, delta: "+1"}`), loadable by the existing
shared rule loader with no change to `world/rules/sexual_transitions.py`. `shame_hem_lift` SHALL
declare `sexual_events=("self_exposure",)`.

#### Scenario: Casting shame_hem_lift raises the actor's exposure by one level
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_hem_lift` on itself
- **THEN** `entity.sexual.exposure`'s ordinal increases by exactly `1`

#### Scenario: The exposure rise cascades into a shame increase within the same call
- **WHEN** `shame_hem_lift` resolves for an entity whose `shame` is below its vocabulary ceiling
- **THEN** the entity's `shame` ordinal also increases by exactly `1`, produced by the pre-existing
  `shame_up_on_exposure_increase` rule firing within the same `apply_event()` call the
  `sexual_event:self_exposure` effect triggers — no code in this change references `shame` directly

#### Scenario: Every rule id declared by this change has a matching test
- **WHEN** `test_every_rule_id_has_a_test()` (`sexual-transition-rulebook`'s existing structural
  check) is run after this change
- **THEN** it passes, because `test_rule_exposure_up_on_self_exposure` exists in
  `world/rules/tests/test_sexual_transitions.py`

### Requirement: Solo seeds credit masturbation_count on the actor only; only solo_self_touch also emits the masturbation experience-type event
`solo_self_touch`, `solo_fondle_breasts`, and `solo_thigh_rub` SHALL each declare
`actor_counters=("masturbation_count",)` and `participant_counters=()`. Only `solo_self_touch` SHALL
declare a non-empty `sexual_events`, equal to `("masturbation_climax",)`.

#### Scenario: Casting any solo seed increments the actor's masturbation_count by exactly one
- **WHEN** an entity casts `solo_self_touch`, `solo_fondle_breasts`, or `solo_thigh_rub` on itself
- **THEN** `entity.sexual.masturbation_count` increases by exactly `1` and no other entity's counters
  change

#### Scenario: Only solo_self_touch adds the masturbation experience type
- **WHEN** an entity with an empty `experience_types` set casts `solo_fondle_breasts` and then
  `solo_thigh_rub`
- **THEN** `"自慰"` is absent from `entity.sexual.experience_types` afterward

#### Scenario: solo_self_touch adds the masturbation experience type
- **WHEN** an entity with an empty `experience_types` set casts `solo_self_touch`
- **THEN** `"自慰"` is present in `entity.sexual.experience_types` afterward

### Requirement: Partner seeds credit duo_act_count on both participants
`partner_caress` and `partner_hand_hold` SHALL each declare `actor_counters=("duo_act_count",)` and
`participant_counters=("duo_act_count",)`.

#### Scenario: Casting a partner seed increments both participants' duo_act_count
- **WHEN** entity A casts `partner_caress` on entity B, both starting at `duo_act_count == 0`
- **THEN** both `A.sexual.duo_act_count` and `B.sexual.duo_act_count` equal `1` afterward

### Requirement: The combat seed credits hostile_act_count on the actor only
`combat_tease` SHALL declare `actor_counters=("hostile_act_count",)` and
`participant_counters=()`.

#### Scenario: Casting combat_tease increments only the actor's hostile_act_count
- **WHEN** entity A casts `combat_tease` on entity B, both starting at `hostile_act_count == 0`
- **THEN** `A.sexual.hostile_act_count` equals `1` and `B.sexual.hostile_act_count` remains `0`
  afterward

### Requirement: A SINGLE-target sexual act cannot be self-cast
The shared targeting pipeline (`world/rules/targeting.py`) SHALL reject a
`SEXUAL_ACT`-category skill with `target_spec=SINGLE` whose resolved target is
the actor itself. The three SINGLE-target seeds (`partner_caress`,
`partner_hand_hold`, `combat_tease`) are two-participant acts by construction:
their `participant_counters` and the future resist contest assume a second
party, so self-casting would credit lifetime counters (e.g. `duo_act_count`,
`hostile_act_count`) with no partner present.

#### Scenario: Self-casting a partner seed is rejected without crediting counters
- **WHEN** entity A casts `partner_caress` (or `partner_hand_hold`) with A itself as the target
- **THEN** the cast is rejected and `A.sexual.duo_act_count` remains `0`

#### Scenario: Self-casting the combat seed is rejected without crediting counters
- **WHEN** entity A casts `combat_tease` with A itself as the target
- **THEN** the cast is rejected and `A.sexual.hostile_act_count` remains `0`
