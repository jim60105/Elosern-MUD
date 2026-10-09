# Spec Delta

## MODIFIED Requirements

### Requirement: Three hand-built acts are registered, gated exclusively by requires_divine_arts, with no counter unlock
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL contain the three `(SkillDef, SexualActDef)` pairs (`絕頂律令`, `時姦`, `神域搾取`), each declaring the shared eligibility requirement for race capability `can_use_divine_arts`, `unlock={}`, `target_part=None`, `resistible=True`, `actor_counters=()`, `participant_counters=()`.

#### Scenario: A non-divine race cannot cast any of the three acts regardless of counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `False` attempts to cast `絕頂律令`, `時姦`,
  or `神域搾取`, regardless of that actor's lifetime counter values
- **THEN** `the shared identity-eligibility gate` rejects the cast with the named identity-eligibility rejection

#### Scenario: A divine-capable actor can cast all three from zero counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `True` and who owns the skill carrying
  the shared eligibility requirement for race capability `can_use_divine_arts` for one of these three acts is read via `SkillHandler.owned_keys()`,
  with every one of that actor's lifetime counters at `0`
- **THEN** the corresponding skill key is present in the returned set; no counter threshold gates it

#### Scenario: SexualMasteryEffect ownership alone does not unlock any of the three
- **WHEN** an entity directly owns a skill carrying `SexualMasteryEffect` but has no divine-capable
  race
- **THEN** `unlocked_act_keys()`/`owned_keys()` include the full counter-gated catalogue but none of
  `絕頂律令`, `時姦`, or `神域搾取`

#### Scenario: The three pairs are hand-built
- **WHEN** `divine.py`'s construction code is inspected
- **THEN** none of the three pairs is constructed via `_act_family()`

#### Scenario: Later tuple extension does not disturb these three pairs
- **WHEN** `sexual-catalog-divine-mutators` extends the same tuple to seven entries
- **THEN** this requirement pins the identity and fields of these three pairs and is not read as limiting the tuple size; none of the three pairs is modified or removed

### Requirement: The three new effect prefixes are line-agnostic dispatch-table entries
`action.py`'s `_EFFECT_HANDLERS` SHALL register `divine_pleasure_max:`, `divine_climax_extension_stage:`,
and `divine_drain:` as ordinary prefixes. Neither handler SHALL read the calling skill's identity eligibility or
otherwise branch on the calling `SkillDef`'s line.

#### Scenario: A hypothetical non-divine SkillDef naming one of the three prefixes is handled identically
- **WHEN** a hypothetical `SkillDef` outside the 神之秘法 line declares
  `effects=["divine_pleasure_max:test"]` and is cast
- **THEN** the handler applies the same two-call `_apply_pleasure_gain` sequence to its targets as it
  would for `絕頂律令`, without rejecting the cast for having no required divine race capability

