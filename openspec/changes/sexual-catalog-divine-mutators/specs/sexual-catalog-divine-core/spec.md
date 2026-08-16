## MODIFIED Requirements

### Requirement: Three hand-built acts are registered, gated exclusively by requires_divine_arts, with no counter unlock
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL contain the three
`(SkillDef, SexualActDef)` pairs — `絕頂律令`, `時姦`, `神域搾取` — each declaring
`requires_divine_arts=True`, `unlock={}`, `target_part=None`, `resistible=True`,
`actor_counters=()`, `participant_counters=()`. None SHALL be constructed via `_act_family()`.
`sexual-catalog-divine-mutators` extends the same tuple to seven entries; this requirement pins
the identity and fields of these three pairs and SHALL NOT be read as limiting the tuple size —
none of the three pairs SHALL be modified or removed.

#### Scenario: A non-divine race cannot cast any of the three acts regardless of counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `False` attempts to cast `絕頂律令`, `時姦`,
  or `神域搾取`, regardless of that actor's lifetime counter values
- **THEN** `_step1_divine_arts_gate` rejects the cast with `RejectReason.DIVINE_ARTS_FORBIDDEN`

#### Scenario: A divine-capable actor can cast all three from zero counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `True` and who owns the skill carrying
  `requires_divine_arts=True` for one of these three acts is read via `SkillHandler.owned_keys()`,
  with every one of that actor's lifetime counters at `0`
- **THEN** the corresponding skill key is present in the returned set — no counter threshold gates it

#### Scenario: SexualMasteryEffect ownership alone does not unlock any of the three
- **WHEN** an entity directly owns a skill carrying `SexualMasteryEffect` but has no divine-capable
  race
- **THEN** `unlocked_act_keys()`/`owned_keys()` include the full counter-gated catalogue but none of
  `絕頂律令`, `時姦`, or `神域搾取`
