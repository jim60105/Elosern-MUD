## 1. Investigate existing magnitude pipeline

- [ ] 1.1 Read `world/rules/combat.py`'s `damage` handler and its magnitude computation end to end
- [ ] 1.2 Determine whether magnitude computation is cleanly factorable into a shared
      caster-stat-driven helper usable by both `damage` and `heal` with a substituted coefficient; if
      not, implement a parallel but equally-tested `heal`-specific magnitude function

## 2. Typed effects

- [ ] 2.1 Add `HealEffect(shape: Literal["single", "area"])` and `SelfHealEffect()` to
      `world/skills/effects.py`'s dispatch table (depends on `skill-effects-typed-model` landing first)

## 3. Handlers

- [ ] 3.1 Implement `_handle_heal` in `world/rules/combat.py`, staging one `PendingEffect` per target
      that clamps `hp.value` to `hp.max`
- [ ] 3.2 Register it via `register_effect_handler("heal", _handle_heal, ...)` in `action.py`, mirroring
      `damage`'s registration
- [ ] 3.3 Implement `_handle_self_heal`, staging a `PendingEffect` against `actor` (not the skill's
      resolved `targets`), mirroring `_handle_self_buff_apply`'s actor-binding pattern; register via
      `register_effect_handler("self_heal", _handle_self_heal, ...)`
- [ ] 3.4 Confirm neither handler special-cases or bypasses an `hp <= 0` target — both rely entirely on
      the existing targeting pipeline's alive-only validation running before the handler is ever reached

## 4. Tests

- [ ] 4.1 Boundary test: healing a target already at max HP
- [ ] 4.2 Boundary test: healing a near-death (but alive) target
- [ ] 4.3 Area-heal independence test across multiple targets at different HP percentages
- [ ] 4.4 `self_heal` restores the caster's HP when the same skill's `damage` effect targets an enemy
- [ ] 4.5 Attempting to target a knocked-out ally with a `heal:single` skill is rejected before the
      handler runs (`target_dead`)
