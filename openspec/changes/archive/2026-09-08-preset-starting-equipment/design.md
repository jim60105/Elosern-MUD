## Context

`activate_player_character` runs one `transaction.atomic()` block and protects
itself with three snapshots taken before it: `character.key`,
`snapshot_traits(character)`, and `snapshot_attributes(character,
_CREATION_ATTRIBUTE_KEYS)`. On any exception the `except` branch restores all
three and re-raises.

Equipping through the sole writer widens what that block touches.
`toggle_equipment` (`world/rules/equipment.py:531`) opens its own
`transaction.atomic()` — a savepoint when nested — and inside it writes
`entity.db.equipment`, calls `sync_equipment_gauge_limits(entity)` (which
rewrites gauge ceilings on the trait handler), and adds or removes attached
buff instances on `entity.db.buffs`. It snapshots and restores those three
surfaces itself, but only for its own failure path; an outer rollback is not
its concern.

The idmapper attribute cache is not transaction-aware. A rolled-back
`db.<attr>` assignment still reads back post-write in-process — the same hazard
`world/rules/party.py::restore_membership_surfaces` and
`world/rules/affinity.py::restore_relations_surfaces` already exist to handle.

## Goals / Non-Goals

**Goals:**

- A preset can declare which of its starting items are worn at activation.
- Worn state, gauge ceilings, and attached buffs are produced by the existing
  sole writer, never by a parallel implementation.
- An authoring mistake fails at registry load, not silently at activation.
- A failed activation leaves no readable equipment, buff, or trait residue.

**Non-Goals:**

- Custom-mode equipment. Subrace basic kits stay unequipped; the player equips
  through the ordinary surface.
- Any change to `toggle_equipment`, the equipment rulebook, or the equipment
  command/panel surface.
- Declaring equipment the character does not carry. `starting_equipment` is a
  subset of `starting_items`, so the pack remains the single source of what the
  character owns.

## Decisions

**D1 — Reuse `toggle_equipment` rather than writing `db.equipment` directly.**
Writing the final map directly would be shorter but would skip
`sync_equipment_gauge_limits` and the attached-buff diff, producing a character
whose ceilings and buffs disagree with its worn set. The equipment capability
declares a single writer; a second one in the creation path would be a
contract violation, not a shortcut. Alternative considered: a new
`equip_initial_loadout()` bulk helper in `world/rules/equipment.py`. Rejected
for this change — one loop over the existing public function is enough, and a
bulk helper can be extracted later if a second caller appears.

**D2 — Order: traits → inventory → toggles.** The toggle preflight rejects an
item absent from `db.inventory` (`ITEM_NOT_HELD`), so inventory must land
first. `sync_equipment_gauge_limits` rewrites ceilings on the already-applied
trait config, so `_apply_trait_config` must land first too. The toggles
therefore run last among the mechanical writes, still inside the same atomic
block and before the portrait finalization.

**D3 — A rejected toggle is a hard activation failure.**
`toggle_equipment` returns `EquipmentToggleResult(outcome="rejected", reason=...)`
instead of raising. Activation SHALL raise `CharacterCreationError` naming the
item key and the stable reason. Treating a rejection as a skip would ship a
character that silently contradicts its own card, and the registry validators
are specifically designed so a rejection can only mean a genuine bug.

**D4 — Load-time validation covers the toggle's silent behaviors.**
`toggle_equipment` is a *toggle*: a duplicate key would equip then unequip. A
second key in the same singleton slot silently replaces the first. A sixth
accessory is rejected at runtime. All three are authoring mistakes with no
useful runtime meaning, so the validator rejects them at registry load — the
same fail-closed stance the skill-kit and starting-item validators already
take. This is why the validator needs `EquipmentSlot` and
`ACCESSORY_MAX_SLOTS` from `world/skills/equipment.py`; `world/lore/` already
depends on `world/skills/`, so no layering rule is bent.

**D5 — `_CREATION_ATTRIBUTE_KEYS` gains `buffs` only.** `equipment` is already
a member. Traits are covered by the existing `snapshot_traits`/`restore_traits`
pair, which `sync_equipment_gauge_limits` writes through. `buffs` is the one
surface the toggle touches that the activation snapshot does not yet cover.

## Risks / Trade-offs

- **A rolled-back activation leaves readable buff or gauge state** → covered by
  D5 plus a dedicated test that injects a failure *after* the toggles and
  asserts `equipment`, `buffs`, and the gauge ceilings are all back to their
  pre-activation values.
- **A future preset declares equipment whose buffs interact with the starting
  trait config in an unexpected way** → the toggles run after
  `_apply_trait_config`, so the ceilings are always computed from the final
  trait values; a test pins the ceiling of a shipped preset that declares
  gauge-affecting equipment.
- **Nested-atomic behavior differs under `--keepdb` or a non-default backend** →
  the toggle already runs nested inside other rules transactions in production
  (the equipment command inside an action commit), so this is exercised
  behavior, not a new pattern.
- **Trade-off: activation gets slower by one savepoint per declared item.**
  Bounded by the four singleton slots plus five accessories; acceptable for a
  once-per-character operation.

## Open Questions

None. The eight shipped cards keep `starting_equipment=()` in this change, so
the observable starting state is unchanged until an author fills the field.
