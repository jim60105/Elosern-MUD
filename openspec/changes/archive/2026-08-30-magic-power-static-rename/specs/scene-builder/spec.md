## MODIFIED Requirements

### Requirement: NPC role tiers resolve deterministic physical stats through the lore registries
SceneBuilder SHALL derive an NPC occupant's stored traits from its `NPCTier` entry's `race_key` and
`static_tier_key` via `world.rules.traits.build_initial_traits(race_key, tier=static_tier_key)`,
which reads the tier's `magic_band` floor into `magic_power` (the deleted race-level
`starting_magic_level` has no successor constant); it SHALL read these values from the
immutable registries and SHALL NOT duplicate balance constants anywhere in `world/quests/`.

#### Scenario: Two NPCs of one tier store identical lore-derived stats
- **WHEN** two occupants are spawned from the same `npc_req` tier
- **THEN** both store identical stats equal to the race/static-tier-derived values

#### Scenario: The derivation is fully registry-backed
- **WHEN** the scene-builder tests inspect the derivation inputs
- **THEN** every race key and static tier key resolves in `RACE_REGISTRY` and
  `STATIC_TIER_REGISTRY`, with the static tier belonging to the declared race
