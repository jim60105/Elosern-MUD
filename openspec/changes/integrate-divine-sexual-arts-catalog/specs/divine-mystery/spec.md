## MODIFIED Requirements

### Requirement: Divine Mystery skills are gated by RaceProfile.can_use_divine_arts
The six 神之秘法 family skills (`divine_sexual_mastery`, `divine_sexual_arts`, and the four
unmechanized mysteries) SHALL declare `SkillDef.requires_divine_arts=True` and be ownable/castable
only by an entity whose race's `RaceProfile.can_use_divine_arts` is `True`. Skills without the marker
(including the generic `sexual_event` mechanism) SHALL NOT be race-gated by this change. This
change SHALL NOT modify `can_use_divine_arts` itself or its existing per-race values — it only adds
consumers gated by the already-landed field. As of the `integrate-divine-sexual-arts-catalog`
integration, `divine_sexual_arts` is additionally a `resistible=True` `SEXUAL_ACT_REGISTRY` row, so
its targets may resist it through the shipped `_step4b_sexual_resist_gate` exactly like the
`divine.py` acts; the race gate itself is unchanged.

#### Scenario: A non-elf cannot cast a Divine Mystery skill even if granted ownership
- **WHEN** a `human` or `beastfolk` entity somehow owns `divine_sexual_arts`
- **THEN** casting it is rejected, since `RACE_REGISTRY["human"].can_use_divine_arts` and
  `RACE_REGISTRY["beastfolk"].can_use_divine_arts` are both `False`

#### Scenario: An elf can cast divine_sexual_arts at no MP/SP cost
- **WHEN** an elf entity owning `divine_sexual_arts` casts it at a valid target whose resist contest
  resolves `resisted=False`
- **THEN** the cast is not rejected for insufficient MP or SP (the skill's `cost` is empty), and it
  resolves via the `sexual_event_target:` effect handler against the surviving target

#### Scenario: The integrated act's gate order is race first, then resist
- **WHEN** a non-divine-capable actor owning `divine_sexual_arts` casts it at a valid target
- **THEN** `_step1_divine_arts_gate` rejects the cast before any resist contest runs, exactly as for
  the `divine.py` acts
