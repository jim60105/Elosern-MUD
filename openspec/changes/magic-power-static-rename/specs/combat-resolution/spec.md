## MODIFIED Requirements

### Requirement: effective_power combines four effective stats multiplied by max hp
`world/rules/combat.py` SHALL provide `effective_power(entity) -> float`, computed as the sum of
`SkillHandler.effective_value()` for `atk_phys`, `agility`, `defense`, and `magic_power`, multiplied by
`max(entity.traits.hp.max, 0)` — the entity's race/tier hp ceiling, never its current, depletable hp
value. This function SHALL NOT write to any entity attribute.

#### Scenario: effective_power reads every stat through effective_value, never raw traits
- **WHEN** an entity has an active stat-multiplier skill (e.g. 身體強化) affecting `atk_phys`
- **THEN** `effective_power()`'s result reflects the multiplied value, not `entity.traits.atk_phys.value`

#### Scenario: An elf's effective_power vastly exceeds a human elite's, driven by max hp
- **WHEN** `effective_power()` is computed for an elf reference character (e.g. stats matching Yuka,
  88/92/90, max hp 10000) and a human-elite reference character (e.g. stats matching Lidzia, 8/9/7, max
  hp 120)
- **THEN** the ratio of the elf's `effective_power()` to the human's is at least 100 — large enough
  that a downstream overwhelm check (change 10) could treat this matchup as overwhelming, unlike a
  stat-only ratio which would understate the gap to roughly 10

#### Scenario: A mid-tier monster's effective_power exceeds a human elite's without becoming overwhelming
- **WHEN** `effective_power()` is computed for a mid-tier monster (`MonsterTier["mid"]`'s band, e.g.
  16/16/16, max hp 300) and a human elite (Lidzia-equivalent, max hp 120)
- **THEN** the ratio of the monster's `effective_power()` to the human's is greater than 1 but well
  below 100, reflecting a fight that requires a party rather than one that is mathematically decided

#### Scenario: effective_power is unaffected by current-hp attrition within a fight
- **WHEN** `effective_power()` is computed for the same entity at full current hp and again after its
  `entity.traits.hp.value` (not `.max`) has been reduced by combat damage, with no change to its
  `effective_value()` outputs
- **THEN** both computations return the identical value — attrition is represented by the turn loop's
  own death check and the hp gauge itself, not by this function

#### Scenario: effective_power changes when a true effective stat changes mid-fight
- **WHEN** `effective_power()` is computed for the same entity before and after a stat-multiplier
  skill (e.g. 身體強化) becomes active
- **THEN** the second computation differs from the first; `disguised_stats` is never read because it
  is display-only under architectural decision D2

#### Scenario: A current-hp-driven ratio would misrepresent a saturated matchup — the case that ruled it
out
- **WHEN** `effective_power()` is computed for an elf reduced to a small fraction of current hp against
  a full-current-hp human elite, using **max** hp as specified above
- **THEN** the ratio still favors the elf by roughly the same margin as the full-hp case (≈677, per
  D-4's worked table) — it does NOT flip to favor the human, even though the human's own current-hp
  advantage is large, because current hp plays no role in this function; a `damage-effect-handlers`- or
  `combat-resolution`-level to-hit check on this same matchup independently confirms the human's hit
  rate remains 0% (saturated) regardless of either combatant's current hp, so no consumer of either
  signal is misled by hp attrition
