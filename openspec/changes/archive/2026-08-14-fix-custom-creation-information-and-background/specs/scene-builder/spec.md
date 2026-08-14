## ADDED Requirements

### Requirement: NPC characterization carries an optional authored persona block for look flavor
The SceneBuilder's occupant characterization seam SHALL accept an optional bounded `background`
text (and, when present, the optional import-card persona block with the prose fields
`personality`, `life_story`, and `habit`) on a `StageSpawnRequirement`'s per-occupant
characterization, validated by the shared `world.quests.characterization` helper against the
persona field bound, and applied by `_apply_characterization` into the spawned NPC's
`entity.db.persona` inside the same atomic materialization. The authored text is flavor content —
it never feeds stored stats, and the anti-hallucination number ban is unchanged. The scenario
director's `npc_req` guardrail SHALL validate the same fields through the shared helper so an AI-
generated NPC can carry authored flavor text from spawn; an administrator-created NPC supplies the
same persona record through the existing import loader (which writes the opaque persona verbatim).

#### Scenario: A characterized NPC carries authored flavor text at spawn
- **WHEN** a stage's `npc_req` characterization declares a bounded `background` and optional prose
  fields
- **THEN** the spawned NPC's `entity.db.persona` carries exactly those authored fields (alongside the
  identity/portrait fields), the look appearance path renders them, and no stored stat was influenced

#### Scenario: An NPC without a persona block carries none
- **WHEN** a stage's `npc_req` characterization declares no persona or background fields
- **THEN** the spawned NPC has no persona record (or an unchanged one) and look output is unchanged

#### Scenario: An over-bound or non-text persona field is rejected
- **WHEN** a stage's `npc_req` characterization declares a `background` beyond the persona field
  bound or a non-text persona prose value
- **THEN** the scenario-director guardrail and the compile boundary reject the requirement with a
  named error before any spawn
