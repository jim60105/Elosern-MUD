## Why

The targeting model is more restrictive than the design intends (audit finding F25): every damage skill is `FactionConstraint.ENEMY`, so players cannot target companions at all — the friendly-fire penalty and auto-leave contracts are unreachable. The intended design is free target selection: skills choose their targets freely among enemies and allies, and the combat menu's "select all enemies"-style options are convenience UI, not permission boundaries.

## What Changes

- All skills — attack and recovery alike — accept any battlefield participant as a target (enemy or ally). Only skills whose effect is inherently self-only restrict their target to the actor (`SELF_ONLY`); no skill is restricted to enemies.
- The faction-constraint check in targeting is reduced to the self-only rule; `ENEMY`/`ALLY`-only constraints are removed from the skill registry.
- Combat-menu shorthands (`all-enemies`, `all-allies`, `all`) remain convenience expansions that the player may use instead of explicit targets; they never grant or deny targeting permission beyond the skill's own scope.
- The existing friendly-fire contract now becomes reachable: damaging a companion applies the per-hit affinity penalty and the auto-leave recheck. Healing a foe is a permitted player choice with no penalty (no contract applies).

## Capabilities

### Modified Capabilities

- `skill-registry`: all skills are freely targetable; only self-only skills carry a target restriction.
- `targeting-validation`: the faction check enforces only the self-only rule; shorthands are convenience UI.
- `affinity-friendly-fire`: reachable through shipped content; healing allies/foes carries no penalty.
- `webclient-combat-menu`: shorthand options are convenience UI, not permission boundaries.

## Impact

- `world/skills/registry.py` (constraint values), `world/rules/targeting.py` (faction check semantics), `world/rules/combat_session.py` (friendly-fire scan placement within the round transaction — depends on `fix-combat-settlement-recovery`), tests, player command docs (menu wording clarification only).
