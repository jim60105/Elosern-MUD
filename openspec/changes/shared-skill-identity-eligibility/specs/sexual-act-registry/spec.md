# Spec Delta

## MODIFIED Requirements

### Requirement: Every act applying pleasure to another participant applies non-zero pleasure to its own actor, unless it requires divine arts
`_act_family()` SHALL raise `ValueError`, naming the offending key, for any row whose
`actor_pleasure_ratio` is not strictly greater than zero, unless the family's shared eligibility declares required race capability
`can_use_divine_arts`.

#### Scenario: A zero actor-pleasure-ratio row is rejected for a non-divine family
- **WHEN** `_act_family()` is called with no required divine race capability and a row declaring
  `actor_pleasure_ratio=0.0`
- **THEN** it raises `ValueError` naming that row's key

#### Scenario: A zero actor-pleasure-ratio row is accepted for a divine family
- **WHEN** `_act_family()` is called with the shared eligibility requirement for race capability `can_use_divine_arts` and a row declaring
  `actor_pleasure_ratio=0.0`
- **THEN** construction succeeds

### Requirement: divine_sexual_arts is the eighth hand-built 神之秘法 row
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL contain a hand-built
`(SkillDef, SexualActDef)` pair with key `divine_sexual_arts` declaring the shared eligibility requirement for race capability `can_use_divine_arts`,
`unlock={}`, `ownership_gated=True`, `target_part=None`, `resistible=True`, `actor_counters=()`,
`participant_counters=()`, and `effects=["sexual_event_target:stimulus_applied"]`; it SHALL NOT be
constructed via `_act_family()`, and `world/skills/registry.py` SHALL NOT define this key inline.

#### Scenario: The divine line carries the eighth pair
- **WHEN** `world.skills.sexual_acts.divine.DIVINE_ACTS` is inspected after this change
- **THEN** a pair with key `divine_sexual_arts` is present in the tuple with the fields above, and
  `SKILL_REGISTRY["divine_sexual_arts"]` is the same `SkillDef` object surfaced by the catalogue
  import rather than a main-registry definition

#### Scenario: The shipped row's parsed effect is the target-scoped event effect
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"].parsed_effects` is inspected
- **THEN** it equals one `TargetSexualEventEffect(event_name="stimulus_applied")`; the prefix's
  parse contract is owned by the `sexual-act-effects` capability's parser requirement, not this one

#### Scenario: The eighth act is subject to the resist gate
- **WHEN** `divine_sexual_arts` is cast by its sole owner at a target whose resist contest resolves
  `resisted=True`
- **THEN** the cast succeeds with the resist verdict logged, the resisted target receives no
  `stimulus_applied` event, and no `RejectedAction` is raised

#### Scenario: The mastery blanket still does not reach the eighth act
- **WHEN** an entity directly owns a skill carrying `SexualMasteryEffect` but has no divine-capable
  race and does not own `divine_sexual_arts`
- **THEN** `owned_keys()` includes the full counter-gated catalogue but not `divine_sexual_arts`,
  because the mastery branch excludes acts requiring race capability `can_use_divine_arts` and the counter branch
  excludes `ownership_gated` rows

#### Scenario: The resist gate applies to the catalogue row
- **WHEN** the eighth act is exercised through the sexual act pipeline
- **THEN** because it is a catalogue row with `resistible=True`, the shipped
  `_step4b_sexual_resist_gate` applies to it exactly as it applies to the seven existing divine acts
