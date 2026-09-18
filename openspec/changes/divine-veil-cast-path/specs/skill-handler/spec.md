## MODIFIED Requirements

### Requirement: The 狀態偽裝 skill's effect resolution can only ever touch disguised_stats, never entity.traits
`world/rules/skill_effects.py` SHALL define `apply_disguise_effect(entity, overrides)` as the
deterministic-core write for the `status_disguise` `SkillDef`, and this function SHALL contain no
reference to `entity.traits` anywhere in its definition. No module under `world/skills/` SHALL write
persistent state.

The values the veil writes SHALL be DERIVED deterministically from the race registry's mundane bands
and SHALL NOT be supplied through `event_context`: each of the displayed combat five is rendered at the
ceiling of the corresponding mundane band the registry already declares, so no balance constant is
duplicated in code. Derivation SHALL live beside the write rather than inside it, so the write keeps
its narrow single-writer contract. The write SHALL also record the veil's PROVENANCE as
divine. A veil cast at an entity OTHER than the actor SHALL apply the veil to that entity. A veil cast
at the actor SHALL toggle against a DIVINE veil ONLY: it SHALL clear the layer when the actor already
carries a divine veil, and SHALL apply the derived veil when the actor carries none or carries a veil
of mundane provenance. A veil the verb did not place SHALL never be lifted by casting the verb.

#### Scenario: apply_disguise_effect only changes disguised_stats
- **WHEN** `apply_disguise_effect(entity, {"atk_phys": 60})` is called on an entity whose true
  `atk_phys` base is `88`
- **THEN** `entity.db.disguised_stats["atk_phys"]` equals `60`, and `entity.traits.atk_phys.value`
  still equals `88`

#### Scenario: The function's source contains no reference to entity.traits
- **WHEN** `apply_disguise_effect`'s source code is inspected
- **THEN** it contains no reference to `entity.traits`, `get_display_value`, or any other trait-reading
  or trait-writing expression — the function's only side effect is assigning
  `entity.db.disguised_stats`

#### Scenario: Casting the veil with no supplied context veils the caster
- **WHEN** an unveiled entity casts the veil at itself with no `disguise` key in `event_context`
- **THEN** its displayed combat five all read the mundane ceilings the race registry declares, while
  every true trait value is unchanged

#### Scenario: The derived values carry no literal
- **WHEN** the mundane band values in the race registry are changed
- **THEN** the values a fresh veil writes change with them, because the recipe reads the registry

#### Scenario: Casting the veil at another entity veils that entity
- **WHEN** an entity casts the veil at a different entity
- **THEN** the target's displayed combat five read the derived values and the caster's own display is
  unchanged

#### Scenario: Casting the veil at a divinely-veiled self lifts it
- **WHEN** an entity carrying a veil of divine provenance casts the veil at itself again
- **THEN** its disguise layer and provenance record are cleared and `get_display_value` returns true
  values for every key

#### Scenario: Casting the veil over an authored veil refreshes rather than lifts
- **WHEN** an entity that started the game wearing an authored (mundane) disguise declaration casts the
  veil at itself
- **THEN** it is veiled at the derived values with divine provenance, and its display is NOT reverted
  to true values

#### Scenario: Casting the veil at an already-veiled other refreshes rather than lifts
- **WHEN** an entity casts the veil at a different entity that already carries a veil
- **THEN** the target stays veiled at the derived values, because only a self-cast toggles
