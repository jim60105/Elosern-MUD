## Context

`SKILL_REGISTRY` (`world/skills/registry.py:169-282`) declares every damage skill `FactionConstraint.ENEMY`; `targeting._validate_faction` (`world/rules/targeting.py:106-109`) and AREA filtering (`:196-208`) drop ALLY candidates, so `_scan_friendly_fire` (`world/rules/combat_session.py:604-676`) never observes a player-vs-companion damage event. The affinity-friendly-fire spec already requires per-hit penalties, per-round membership snapshots, atomicity with the round, and auto-leave.

## Goals / Non-Goals

**Goals:**
- Free target selection for all skills (enemy or ally); only self-only effects are restricted.
- Friendly-fire penalties reachable through shipped content; the contract's atomicity requirement satisfiable.
- Menu shorthands remain conveniences.

**Non-Goals:**
- Changing penalty values, membership snapshot semantics, or auto-leave logic.
- Introducing a formal aggro/alignment system — relation is still computed per battle context.
- A healing-foe penalty (none exists; none added).

## Decisions

**D1 — `FactionConstraint` shrinks to `ANY`/`SELF_ONLY`.** All shipped skills — attack and recovery — become `ANY` (default); `ENEMY` and `ALLY` enum values are removed from the registry (the enum itself may keep the values for legacy test data, but no skill declares them; the validation code only enforces `SELF_ONLY`). Whether any self-only skill exists is content-driven: currently none is required, and none is added.

**D2 — Faction check becomes a self-only rule.** `_validate_faction` passes every relation for `ANY`; rejects non-SELF for `SELF_ONLY`. No other faction filtering exists; AREA filtering keeps presence/alive/range semantics and no longer drops allies.

**D3 — Friendly-fire consequence unchanged.** The existing per-hit penalty, per-round snapshot, auto-leave, and notification-after-commit contract applies to companion damage; the scan moves inside the outer round transaction of `fix-combat-settlement-recovery` (declared dependency).

**D4 — Menu shorthands stay as-is.** `all-enemies`/`all-allies`/`all` remain convenience expansions validated like explicit lists; no permission change.

## Risks / Trade-offs

- **Intentional companion hits**: the affinity penalty is the design's balancing mechanism (per-hit −1, auto-leave below 70); free targeting plus penalty is the stated design intent.
- **Healing enemies**: permitted by design (free choice); no mechanical consequence is specified.
- **Dependency on the outer transaction**: the scan relocation lands after `fix-combat-settlement-recovery` (declared in tasks).
