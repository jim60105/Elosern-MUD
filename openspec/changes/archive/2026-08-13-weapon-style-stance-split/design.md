## Context

Both `light_sword_style` and `dual_wield_style` currently declare `weapon_style:*` effects, a prefix
with zero consumers. They are narratively and mechanically different: one deals damage on cast, the
other is a standing posture. Design doc §3.3 splits them rather than building one handler that tries
to serve both shapes.

## Goals / Non-Goals

**Goals:**
- `light_sword_style` becomes castable and deals light-elemental physical damage.
- `dual_wield_style` grants a real, ownership-triggered combat adjustment while equipped appropriately.

**Non-Goals:**
- Does not add new weapon-style skills beyond the two that already exist (the reworked `dual_wield_style`
  and a separate higher-tier `dual_blade_mastery` skill are handled by `skill-content-completion`, not
  here).
- Does not build a general "stance system" — this is one rule-table row for one skill, not a new
  first-class stance mechanic.

## Decisions

- **`light_sword_style` reuses `damage:light:physical` rather than inventing a `weapon_style`
  cast-handler.** A weapon-style cast-time handler that only ever serves one skill is not a reusable
  abstraction — reusing the already-tested `damage` handler is strictly simpler and gets identical
  player-facing behavior to any other attack skill.
- **`dual_wield_style`'s bonus is conditioned on actual dual-wielding if `equipment-inventory`'s data
  model exposes "two weapons equipped" as a queryable fact; otherwise it falls back to bare
  ownership.** Investigate `world/rules/equipment.py` (or wherever `entity-inventory`/
  `equipment-inventory` lives) before deciding — this is a task-list investigation step, not a
  pre-decided architecture choice, because the actual data model wasn't inspected as part of the
  design-doc approval pass.
- **The rule-table condition reads the equipment fact from stored state, never through the
  `entity.equipment` handler.** `evaluate_condition()` is a pure context-value matcher, so the
  combat-modifier context builders (`build_no_create_condition_context`, `_build_context`, and the
  WebClient status context) supply a boolean `dual_wielding` fact computed by
  `world/skills/equipment.py::dual_wielding_from_storage` from `entity.db.equipment` alone. This
  keeps the no-create preview and status paths free of lazy-handler materialization, and malformed
  storage fails closed to `False`. The handler-level `EquipmentHandler.is_dual_wielding` property
  exists as the general query API for code that already materializes the handler.

## Risks / Trade-offs

- [Risk] If the equipment system has no clean "two weapons equipped" query, the fallback (bare
  ownership) makes `dual_wield_style` grant its bonus even single-wielding, which is narratively odd.
  → Mitigation: task list requires checking equipment data first; if no clean query exists, add the
  minimal one needed (a `is_dual_wielding` property) rather than accepting the narratively-odd
  fallback silently.

## Migration Plan

No data migration. Lands after `skill-effects-typed-model` and `skill-owned-rule-condition`.

## Open Questions

None — resolved by the investigation task in tasks.md.
