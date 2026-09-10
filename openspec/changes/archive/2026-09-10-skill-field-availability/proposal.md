## Why

`SkillDef.usable_out_of_combat` defaults to `False`, and almost nothing ever
overrode it. Of the whole catalog — 42 hand-written `_skill()` definitions, 75
elemental-spell rows, the generated passive tiers, and the sexual-act
catalog — exactly ten registry entries plus the sexual acts declare `True`.
Every damage-carrying definition is `False`.

That distribution was never a decision. It is the default nobody revisited,
and it has one visible consequence: the `cast` command cannot fire a single
attack spell outside a fight, so `field-combat-initiation` would have nothing
to open combat with. The owner's direction is to stop treating the field as an
accident — review every skill on the merits, mark `False` only where casting
with no fight in progress is genuinely wrong, and keep the field meaningful for
the skills still to be authored, since the game's content is not finalized.

This change is safe to make only because `out-of-combat-damage-gate` already
refuses any `DamageEffect` skill without a battlefield. Widening the flag
before that gate exists would let a player kill an NPC in the open world
through `settle_out_of_combat_cast`.

## What Changes

- Every entry of `SKILL_REGISTRY` gets a deliberate `usable_out_of_combat`
  value, applied at its own construction site in `world/skills/registry.py`
  (and, for the generated families, at the builder that produces them).
- The governing policy is written down rather than inferred: an `ACTIVE` skill
  declares `True` unless casting it with no fight in progress is meaningless or
  would bypass a subsystem. The exceptions are enumerated, not left implicit.
- `flee` stays `False` (`world/rules/disengage.py`): there is nothing to
  disengage from outside combat, and it already has a dedicated action.
- `basic_attack` becomes `True`. **BREAKING** for one archived requirement's
  wording: `universal-action-ownership` currently states `basic_attack` is
  "unusable outside combat". Its only out-of-combat use is opening a fight, and
  until `field-combat-initiation` routes that, the damage gate refuses it —
  so the amended clause says "selectable from exploration only as a
  field-combat initiation", and the skill still cannot resolve without a
  battlefield.
- Damage-carrying skills become `True` for the same reason and under the same
  confinement.
- A frozen-inventory test pins the exact set of keys declaring `False`. Because
  the dataclass default is `False`, a newly authored skill lands outside that
  set and fails the test until its author makes a decision. That is the point:
  the field becomes a forcing function instead of a default.

No backward compatibility and no migration: the project has no released users,
and no persisted data records this flag.

## Capabilities

### New Capabilities

None. This change adds a requirement to one existing capability and modifies a
requirement in another.

### Modified Capabilities

- `skill-registry`: adds the field-availability policy — what
  `usable_out_of_combat` means, the rule every skill is judged by, the
  enumerated exceptions, and the frozen-inventory contract that makes an
  undecided new skill a test failure.
- `universal-action-ownership`: modifies the `INNATE_SKILL_KEYS` requirement so
  `basic_attack`'s "unusable outside combat" clause becomes "selectable from
  exploration only as a field-combat initiation", with the damaging-action gate
  named as what still prevents it resolving without a battlefield.

## Impact

- `world/skills/registry.py` — `usable_out_of_combat` on `basic_attack`, the
  elemental-spell builder rows, the hand-written definitions, and the generated
  passive families.
- `world/skills/sexual_acts/_builder.py` — reviewed; expected to stay `True`.
- `world/rules/disengage.py` — reviewed; `flee` stays `False`.
- `world/skills/tests/` — the frozen-inventory test and the policy assertions.
- Unaffected: every resolver, preview, session, command, and webclient code
  path. This change moves data and adds one test; it adds no branch.
- Behaviourally inert until `field-combat-initiation` lands, because
  `out-of-combat-damage-gate` refuses every newly permitted damage skill
  without a battlefield.
