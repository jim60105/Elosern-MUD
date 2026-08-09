## MODIFIED Requirements

### Requirement: Anti-hallucination: the proposal never chooses mechanical numbers, stats, or class lineage
SceneBuilder SHALL accept from a stage's registered requirements only registry keys — archetype in
`SCENE_ARCHETYPE_REGISTRY`, NPC tier in `NPC_TIER_REGISTRY`, monster tier in `MONSTER_TIER_REGISTRY`,
anchor in `ANCHOR_PLACEMENT_REGISTRY`, and a layer — and SHALL derive every stored numeric stat
deterministically from the immutable lore tables (`world.rules.traits.build_initial_traits` for NPC
role tiers and `build_initial_traits_for_monster_tier` for monster tiers). Every occupant SHALL be
spawned through a prototype whose parent is selected only from the module's
`SCENE_OCCUPANT_PROTOTYPE_WHITELIST`. A requirement that fails to resolve, or any payload that
attempts to supply a numeric stat, a typeclass path, or a prototype parent outside the whitelist,
SHALL be rejected with a named `SceneBuilderError` before any room or entity is created. The
number ban SHALL cover mechanical and balance values — numeric stats, rewards, and bands. The
validated characterization fields (`display_name`, paired `age`/`apparent_age` bounded by the
adult floor and the race lifespan, and the portrait `stable_key`) are authored content like
speech and SHALL NOT be treated as mechanical numbers; they never feed stored stats, which remain
derived deterministically from the lore tables.

#### Scenario: An unknown key is rejected before any spawn
- **WHEN** a stage's requirement names an archetype or tier absent from the lore registries
- **THEN** `materialize_stage` raises a named `SceneBuilderError` and no room, exit, or occupant is
  created

#### Scenario: A numeric stat in a payload is rejected
- **WHEN** a stage's requirement payload attempts to supply a numeric stat (for example an HP or
  attack value)
- **THEN** it is rejected with a named `SceneBuilderError` before any entity is created

#### Scenario: A validated characterization age is not a mechanical number
- **WHEN** a stage's requirement carries the validated `age`/`apparent_age` fields
- **THEN** the requirement resolves normally, the ages never enter any stored trait, and all stored
  stats still come from the lore tables
