# Design: custom kit worn at activation

## Context

See `proposal.md` (Why) and the delta spec for the normative contract. The mechanical
situation:

- `world/rules/character_creation.py:645-646` sets `starting_equipment: tuple[str, ...] = ()`
  in the custom branch under a "preset-starting-equipment non-goal" comment; the preset
  branch (~line 638) reads `preset.starting_equipment`. One shared toggle loop
  (`character_creation.py:733`) then wears whatever `starting_equipment` is non-empty,
  inside the same all-or-nothing activation transaction, after trait config and the
  `inventory` write.
- `world/lore/equipment` machinery: `world/rules/equipment.py::toggle_equipment` is the
  sole equipment writer; it toggles rather than equips, silently replaces a singleton
  occupant, and rejects a sixth accessory at runtime. This is why both lore validators
  exist.
- `world/lore/starting_kits.py::_validate_starting_kit` enforces equipment-only + no
  duplicates (plus shape/unknown-key/quantity rules) but NOT singleton-slot collisions or
  the accessory cap; `world/lore/player_presets.py::_validate_preset_starting_equipment`
  (line 1030) enforces five rules on presets: subset of `starting_items`, no duplicates,
  every key is equipment, no singleton-slot collision, no accessory overflow past
  `ACCESSORY_MAX_SLOTS`.

## Goals / Non-Goals

**Goals:**
- Custom activation wears the whole resolved subrace kit through the existing toggle loop.
- Kit load-time validation rejects any kit that cannot be fully worn (singleton collision,
  accessory overflow), preserving the project stance that authoring errors fail at import.
- One implementation of wearing/buff-attachment/gauge-ceiling recomputation shared by both
  modes (the toggle loop and `toggle_equipment` stay untouched).

**Non-Goals:**
- Preset-mode behavior (already worn; its validator keeps all five declared rules).
- Kit content redesign — no shipped kit needs changing (audit below).
- `sync_all` pruning (design §7 non-goal), save-data compatibility (design §7), the
  `Origin` refactor (design §6, rejected).
- Any command/UI surface change — equipment is written by activation, not by a new surface.

## Decisions

### D1 — Feasibility: every shipped kit is wear-safe (verified)

All 15 shipped kits hold at most one `weapon_main`, one `weapon_off`, one `armor`, and at
most one `accessory` item (cap `ACCESSORY_MAX_SLOTS` = 5), so "wear every kit item" is
collision-clean for the whole registry today. The audit was re-run including Change 1's
(`human-subrace-lineage-rework`) three new human commoner kits against
`world/lore/items.py`: `iron_dagger` (鐵短刀) and `hunting_throwing_axe` (狩獵擲斧) are both
`EquipmentSlot.WEAPON_OFF`, `silver_hairpin` (銀髮簪) is `EquipmentSlot.ACCESSORY`, and the
shared `plain_sword` (WEAPON_MAIN) / `leather_armor` (ARMOR) pair — so each of 濱海民/平原民/
山地民 occupies ≤1 key per singleton slot with one accessory. No kit needs redesigning.
This is why Change 3 must land after Change 1: the audit statement is only true against the
post-Change-1 kit data.

### D2 — Implementation shape: derive `starting_equipment` from the kit

`character_creation.py:646` is replaced by a derivation `starting_equipment = tuple(key for
key, _ in kit.items)` placed directly after the guarded `kit =
SUBRACE_STARTING_KIT_REGISTRY.get(...)` lookup (the `kit is None` guard at :651-653 fires
first, so the derivation only sees a resolved kit; both still precede every write). The rule
is **every kit item is worn** — safe without a
wearable-subset rule because `_validate_starting_kit` already restricts kits to
equipment-only items, so every kit key has a resolved `equipment_slot`. The existing toggle
loop (~line 733) is UNCHANGED, so preset and custom activation share one implementation of
wearing, buff attachment, and `sync_equipment_gauge_limits` recomputation; the
`write_observer("starting_equipment")` stage fires for custom activations too, which the
write-position failure test relies on. Rejected alternative: a custom-only second wearing
path — a parallel implementation of exactly the machinery the spec forbids duplicating.

Toggle idempotence is a first-for-custom concern: `toggle_equipment` toggles, and preset
activations exercised buff attachment on preset loadouts, never subrace kits — the §8 extra
(a) test must assert buffs are attached exactly once per item for a multi-item kit (task 3.1).
Snapshot-set completeness is verified, not assumed: `_CREATION_ATTRIBUTE_KEYS`
(`character_creation.py:30-48`) already names `equipment` and `buffs` (and the gauge ceilings
are traits, covered by `snapshot_traits`), so the custom rollback path gets the identical
residue guarantee through the same code path.

Consequence (design §5.6, stated plainly in the proposal): custom characters become
measurably stronger at creation — equipment modifiers, attached buffs, and gauge ceilings
apply from the first moment — for all 15 subraces. Intended balance change, not UX polish.

### D3 — Validator factoring: shared wearable-set helper, both validators call it

The singleton-collision and accessory-cap rules must apply to kits. They cannot simply be
*removed* from `_validate_preset_starting_equipment`: presets declare their own
`starting_equipment` independent of any kit, and the unchanged
`Preset activation grants the preset's declared starting inventory` requirement (plus its
"An invalid starting-equipment declaration is rejected at load" scenario) still pins all
five preset rules at import. Chosen factoring:

- Extract the wearable-set arithmetic — duplicate keys, `equipment_slot is None`, two keys
  claiming one singleton slot, more accessories than `ACCESSORY_MAX_SLOTS` — into one
  module-level helper in `world/lore/starting_kits.py` (e.g.
  `validate_wearable_loadout(item_keys, *, owner)` taking an owner label for stable error
  messages), reading `ACCESSORY_MAX_SLOTS`/`EquipmentSlot` from `world/skills/equipment.py`
  exactly as the preset validator does today (lore→skills is an existing dependency; never
  `world.rules`).
- `_validate_starting_kit` keeps its entry-shape / unknown-key / quantity checks and the
  equipment-only check inside its entry loop, and delegates duplicates, collision, and
  accessory-cap to the helper (its inline `seen` duplicate check folds into the helper).
- `_validate_preset_starting_equipment` keeps its per-key malformed-entry guards and the
  subset-of-`starting_items` rule as the first loop (today's code checks subset *before*
  duplicates and equipment per key, and the helper call after that loop preserves the
  observable error precedence — a bad key absent from `starting_items` still raises the
  subset error) and delegates the rest to the helper. The helper must reproduce the existing
  stable message shapes with the owner label substituted, and the existing
  `test_starting_equipment_validation_rejects_the_five_invalid_declarations` must pass with
  no edits — observable preset behavior is unchanged (all five rules still raise at import).

Rejected alternatives: duplicating ~20 lines in both validators (drift risk — the cap and
singleton semantics must not diverge); moving the whole preset validator into
`starting_kits.py` (the subset rule is preset-specific; the spec text there stays put).

Why load-time and not activation-time: harmless while kits went unworn; once worn, a
colliding kit flips from benign authoring typo to failed player activation — `toggle_equipment`
silently replaces a singleton occupant (worse: silent corruption) and rejects the sixth
accessory (activation rollback in front of a player). Import-time failure preserves the
project stance.

### D4 — Spec delta stays inside two existing requirements

Both `### Requirement:` heading names stay byte-identical (`Preset activation grants the
preset's declared starting inventory`, `Custom activation grants the chosen subrace's basic
starting kit`), so every `@covers_requirement` slug stays valid and no decorator or
`tools.spec_traceability` ID work is needed. Changes to bodies/scenarios:
- `:205` body: drop the clause "custom-mode subrace kits are granted entirely unequipped"
  from the unequipped-items paragraph (preset undeclared items keep theirs). In the
  `Custom activation starts with its subrace kit` scenario, the trailing "and every
  equipment slot is empty" clause contradicts the reversal and is dropped — it pins exactly
  the behavior being reversed (deliberate exception to verbatim carry-over, matching the
  body-clause drop).
- `:308` body: adds the wear-every-kit-item paragraph (shared machinery, resolved slots,
  load-time failure for unwearable kits). `A custom character wakes with its subrace kit`
  changes from unequipped to each item occupying its resolved slot (plus buffs/ceilings).
  The new collision/accessory-overflow load-failure scenario lives under `:308` (the
  requirement whose contract breaks if a kit can't be worn); no new requirement is added.

### D5 — Tests land in already-registered modules

No new test modules → no `.github/evennia-shards.json` change.
- `world/rules/tests/test_character_creation.py` (registered `world.rules` shard): the
  existing `test_custom_activation_leaves_every_equipment_slot_empty` (~line 793) pins the
  reversed behavior and MUST be replaced — the §8 extra (a): a custom activation wears its
  whole kit, every item in its resolved slot, with equipment modifiers, attached buffs, and
  gauge ceilings applied. The existing `test_custom_activation_grants_each_subrace_starting_kit`
  (~line 617) keeps its inventory assertions (still true; worn items remain in inventory).
- `world/lore/tests/test_starting_kits.py` (registered `world.lore` shard): the §8 extra (b)
  — a deliberately colliding kit (two `weapon_main` keys) and a sixth-accessory kit raise
  from `_validate_starting_kit` at registry load.
- Scenario coverage rides existing slugs (scenario-under-existing-requirement):
  `player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit`
  for the wake-with-worn-kit and kit-load-collision tests,
  `player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory`
  for preset-validator regression; canonical IDs via
  `uv run --locked python -m tools.spec_traceability list` — no new IDs (no new
  requirement).

## Risks / Trade-offs

- [Balance shift for all 15 subraces at creation] → Intended and owner-approved (design
  §5.6); stated in the proposal as BREAKING (balance) so reviewers weigh it explicitly.
- [A future kit becomes unwearable only at runtime if the helper is bypassed] → Helper is
  called from both registry-load validators; the new load-failure scenario pins it.
- [Toggle-loop residue semantics] → Custom activations now exercise the existing
  rollback/residue guarantees (`buffs` snapshot, `write_observer("starting_equipment")`);
  the existing failure-injection tests cover the loop generically; the replaced custom-slot
  test asserts the worn state instead of emptiness.
- [Import-order coupling if the helper moves] → Helper lives in `world/lore/starting_kits.py`
  (lore-internal); `player_presets.py` gains one lore→lore import; no cycle (starting_kits
  imports only `world.lore.items`, `world.lore.races`, `world.skills.equipment`).

## Migration Plan

Clean break (design §7): no save-data compatibility, DB rebuilt. Rollback = revert the
commits; no data steps.
