# Proposal: custom-kit-worn-at-activation

## Why

Custom-mode creation grants the chosen subrace's basic starting kit but deliberately leaves it
unequipped: `world/rules/character_creation.py:645-646` sets `starting_equipment = ()` under a
"preset-starting-equipment non-goal" comment, and `openspec/specs/player-character-creation/spec.md:235-236`
records that "custom-mode subrace kits are granted entirely unequipped". The approved design
(`docs/superpowers/specs/2026-09-12-human-subrace-lineage-rework-design.md` §2, §5) reverses that
explicit decision: kit items are worn at activation, so a newly created character wakes dressed in
its lineage's gear with equipment modifiers, attached buffs, and gauge ceilings applied from the
first moment. Because this REVERSES a specified behavior, the spec delta is the heart of this change.

## What Changes

- **BREAKING (balance)**: custom-mode activation derives `starting_equipment` from the resolved
  subrace starting kit instead of `()` — every kit item is worn at activation. Equipment modifiers,
  attached buffs, and gauge ceilings now apply from activation, so custom characters become
  measurably stronger at creation than before. This is the intended effect and applies to **all 15
  subraces**, not only the human five — a balance change, not UX polish (design §5.6).
- Preset activation behavior is unchanged: the existing toggle loop
  (`world/rules/character_creation.py:733`) is untouched, so preset and custom activation share one
  implementation of wearing, buff attachment, and gauge-ceiling recomputation through
  `world/rules/equipment.py::toggle_equipment` — the sole equipment writer — inside the same
  all-or-nothing activation transaction.
- Validator hardening (design §5.4): the singleton-slot-collision and accessory-cap rules MOVE from
  `_validate_preset_starting_equipment` (`world/lore/player_presets.py`) into
  `_validate_starting_kit` (`world/lore/starting_kits.py`), so a colliding kit fails at registry
  load, never in front of a player. This was harmless while kits went unworn; once worn, a
  colliding kit turns an authoring typo into a failed activation. The rules move as a shared
  wearable-set helper both validators call (design D3): `_validate_starting_kit` gains duplicate,
  collision, and accessory-cap enforcement, while the preset validator keeps its observable
  five-rule contract (subset, equipment, duplicates, collision, cap) via the same helper — the
  preset rules stay pinned by the unchanged preset spec scenario.
- Spec modifications in `player-character-creation` (both Requirement heading names stay unchanged,
  so no `@covers_requirement` churn — design §5.5):
  - "Preset activation grants the preset's declared starting inventory": drop the
    custom-kits-granted-unequipped clause.
  - "Custom activation grants the chosen subrace's basic starting kit": the wake scenario changes
    from unequipped to each kit item occupying its resolved slot; a new scenario covers a kit with
    a singleton-slot collision failing at registry load.
- Documentation sweep: any game/development doc stating that custom characters start unequipped is
  updated to match the new contract.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `player-character-creation`: two Requirement bodies change — the preset starting-inventory
  requirement drops the custom-unequipped clause, and the custom starting-kit requirement now
  specifies that every kit item is worn in its resolved slot at activation, with a new load-time
  scenario for singleton-slot collisions and accessory-cap overflow in a kit.

## Impact

- **Code**: `world/rules/character_creation.py` (custom branch derives `starting_equipment` from the
  resolved kit at line ~646); `world/lore/starting_kits.py::_validate_starting_kit` (gains the
  singleton-slot-collision and accessory-cap rules via the shared wearable-set helper);
  `world/lore/player_presets.py::_validate_preset_starting_equipment` (keeps the malformed-entry
  guards and the subset-of-`starting_items` rule; delegates duplicates/not-equipment/collision/cap
  to the same helper, so preset behavior is observably unchanged).
- **Tests**: `world/rules/tests/` custom-activation coverage (whole kit worn, every item in its
  resolved slot, buffs and gauge ceilings applied) and `world/lore/tests/test_starting_kits.py`
  (a deliberately colliding kit raises at registry load). Canonical runner is Evennia's, not bare
  pytest (design §8).
- **Balance**: all 15 subraces' custom activations get stronger at creation — the reason this is its
  own change rather than part of the lineage rework.
- **Prerequisite ordering**: this is Change 3 of 3 — `human-subrace-lineage-rework` →
  `subrace-specialty-localization` → `custom-kit-worn-at-activation`. See Batch below. No code
  coupling to Change 2.

## Batch:

depends-on: human-subrace-lineage-rework
depends-on: subrace-specialty-localization

Ordering rationale: the §5.2 feasibility audit (all 15 shipped kits are singleton-slot-clean and
accessory-cap-respecting) was checked **including** Change 1's three new human commoner kits
(濱海民/平原民/山地民), so Change 1 must land before this change's "every kit item is worn" rule is
safe to ship. Change 2 (`subrace-specialty-localization`) has no causal relationship to this one;
it is listed only to fix queue position behind it.

Code-conflict notes:
- Proposal stage: no shared files with either sibling change.
- Implementation stage: Change 1 touches `world/lore/starting_kits.py` (kit data, lines 32-36) and
  `world/lore/tests/test_starting_kits.py`; this change touches `_validate_starting_kit` in the
  same module and the same test file (new validator tests appended). Textual overlap risk is at the
  registry-literal vs. validator-function boundary — sequential application (Change 1 first) makes
  this mechanical. Change 1 also rewrites three kits to three-item COMMON sets; this change's
  validator must be validated against the post-Change-1 kit data.
- This change's code edits (`world/rules/character_creation.py`, validator relocation) are disjoint
  from Change 1's `world/lore/races.py` / `world/lore/player_presets.py` data edits.
