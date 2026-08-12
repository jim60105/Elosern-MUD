## 1. Typed effect

- [ ] 1.1 Add `MovementEffect(mode: Literal["flight", "flash_step"])` to `world/skills/effects.py`'s
      dispatch table

## 2. Reclassify

- [ ] 2.1 Change `flight` and `flash_step` from `kind=SkillKind.ACTIVE` to `kind=SkillKind.PASSIVE` in
      `world/skills/registry.py`
- [ ] 2.2 Grep tests/webclient surfaces for these two keys assuming castability; fix any that do

## 3. Wilderness waiver

- [ ] 3.1 Add the `flight`-owns-waives-`wilderness_move` check to `charge_movement()` in
      `world/rules/movement.py`
- [ ] 3.2 Test: flight owner pays nothing for `wilderness_move`; non-owner pays normally; the waiver
      does not leak into other `cost_key`s

## 4. Flight-required exit flag

- [ ] 4.1 Add `requires_flight: bool = False` to `MovementCostMixin` (or the appropriate exit base) in
      `typeclasses/exits.py`
- [ ] 4.2 Wire the flag into the exit's existing access-lock check so a non-flight/flash_step owner is
      denied traversal
- [ ] 4.3 Test: denial for a non-owner, success for a `flight` or `flash_step` owner, and confirm no
      shipped exit sets the flag by default

## 5. Verify

- [ ] 5.1 Run the full existing `movement-cost-charging` scenario suite; confirm no regression to
      unrelated cost keys or non-PlayerCharacter traversers
