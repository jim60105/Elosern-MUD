## REMOVED Requirements

### Requirement: effective_growth_multiplier combines race, self, and conferred multipliers
**Reason**: use-driven progression (D3) removes every XP writer that consumed this query; the conferred multiplier query itself survives in `buff-handler-integration` and is re-consumed by `use-driven-skill-lineage`'s practice-XP formula.
**Migration**: See `buff-handler-integration` (query) and `use-driven-skill-lineage` (consumer).

### Requirement: accrue_magic_study grants magic XP only for SKIP-sourced elapsed time
**Reason**: ambient study XP contradicts use-only growth; declared practice replaces it.
**Migration**: None — growth for elapsed time is removed from the game.

### Requirement: grant_combat_kill_xp awards magic XP scaled by monster tier and the entity's growth multiplier
**Reason**: kills grant no XP (D3); quest credit and defeat EventLogs keep their attribution.
**Migration**: None — kill XP is removed from the game.

### Requirement: magic_level never exceeds the entity's race-driven cap regardless of XP surplus
**Reason**: the trait is static after `magic-power-static-rename`; no XP write can move it.
**Migration**: Static initialization rules live in `entity-trait-scales`.

### Requirement: World-clock and combat integration use the progression seams exactly once
**Reason**: both seams are deleted; the world-clock stage slot survives as the `practice_settlement` placeholder under `settlement-stage-order`.
**Migration**: `settlement-stage-order` (placeholder stage) and `declared-practice-skip` (future writer).

### Requirement: Magic-growth values are finite and non-negative
**Reason**: there is no growth accumulation left to validate.
**Migration**: Per-skill practice clamps live in the future `skill-lineage` capability.
