## 1. light_sword_style

- [ ] 1.1 Change `light_sword_style`'s `effects` from `["weapon_style:light_sword"]` to
      `["damage:light:physical"]` in `world/skills/registry.py`
- [ ] 1.2 Test: casting it resolves successfully and deals damage, matching the pattern of existing
      `damage`-based skill tests

## 2. dual_wield_style equipment investigation

- [ ] 2.1 Read `world/rules/equipment.py` (or the actual module backing the `equipment-inventory`
      capability) to determine whether "two weapons equipped" is a queryable fact
- [ ] 2.2 If not, add the minimal query needed (e.g. `entity.equipment.is_dual_wielding`) rather than
      falling back to bare-ownership silently

## 3. dual_wield_style rule row

- [ ] 3.1 Add a `skill_owned` row for `dual_wield_style` to `combat_modifiers.yaml`, conditioned per
      task 2's finding
- [ ] 3.2 Pick and document the adjustment field (to-hit and/or damage) and magnitude

## 4. Tests

- [ ] 4.1 Owning + dual-wielding (or bare ownership, per 2's finding) grants the adjustment
- [ ] 4.2 Not owning never grants it
- [ ] 4.3 Add the mandatory `test_rule_dual_wield_style` function per `combat-modifier-table`'s existing
      hard requirement that every rule ID have exactly one corresponding test function
