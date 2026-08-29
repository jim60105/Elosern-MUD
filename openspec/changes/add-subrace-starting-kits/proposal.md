# Proposal: add-subrace-starting-kits

## Why

Custom-created characters (non-template creation) currently activate with a completely empty inventory — every newly made adventurer starts with nothing, while preset activation already grants a declared starting kit. A character's subrace should shape their opening kit: a 熊人 heavy-weapon fighter, a 貓人 agile dagger user, and a 王族 human should not all wake up identically empty. The player-character-creation contract already governs preset-declared starting inventory, so the symmetric subrace-driven contract belongs there.

## What Changes

- Custom-mode activation now grants a deterministic subrace basic starting kit (a set of registry item keys written into the character's `inventory` through the existing atomic activation transaction) instead of an empty inventory. This modifies the existing `player-character-creation` requirement "Preset activation grants the preset's declared starting inventory", which today normatively pins custom mode to an empty inventory.
- A new lore registry maps every registered subrace to its basic starting kit; kits are equipment-only (every kit item is a registered item that declares an `equipment_slot`) and the mapping is validated at registry load time so a subrace without a kit, or a kit naming an unknown or non-equipment item, fails at import rather than mid-activation.
- Kits are built from shared `ITEM_REGISTRY` entries — the same basic item (for example a mundane knife or leather armor) may appear in several subrace kits — plus a small set of newly added basic equipment items where no existing registry item fits a subrace archetype.
- The spec records only the invariant "every subrace has a fitting, non-empty basic starting equipment kit whose items exist and are equipment in the item registry, and custom activation hands it out" (race coverage follows from subrace coverage); per-subrace kit contents are implementation data, deliberately kept out of the spec, and are not the subject of newly authored data tests.
- Preset activation is unchanged in substance: a preset keeps its own declared starting inventory and is not overridden by the subrace kit. Imported characters keep their record-owned inventory — the kit contract governs player-shell activation only.

## Capabilities

### New Capabilities

(None — the contract belongs to the existing character-creation capability.)

### Modified Capabilities

- `player-character-creation`: MODIFIES "Preset activation grants the preset's declared starting inventory" (custom mode no longer starts empty; preset inventory is not kit-overridden) and ADDS two requirements: (1) every registered subrace has a validated, non-empty, equipment-only basic starting kit in the item catalog (load-time enforcement, items shareable across kits), and (2) custom activation grants the chosen subrace's kit as the starting inventory, atomically with the rest of activation, applying only to player-shell activation (imports unaffected) while preset activation keeps granting only its declared inventory.

## Impact

- `world/lore/`: new subrace-starting-kit registry module with load-time validation (covers every `SUBRACE_REGISTRY` key, item keys exist in `ITEM_REGISTRY`, positive quantities, no duplicate keys), mirroring the `player_presets` starting-item validation precedent.
- `world/lore/items.py`: a few new basic equipment item definitions (weapons/armor/accessories reusing existing `PRICE_TABLE` keys such as `mundane_weapon`, `armor`, `jewelry`).
- `world/rules/character_creation.py`: custom-mode `activate_player_character` resolves the subrace kit (preflight before any write; all-or-nothing transaction unchanged).
- Tests: update the existing custom-activation expectation of an empty inventory; add a coverage test (every subrace has a non-empty kit of resolvable equipment items; validator rejects broken kits) and a behavior test (custom activation grants the kit per subrace; presets unaffected; imports unaffected). No newly authored per-subrace data assertions. `covers_requirement` annotations for the two new requirements land only after the delta is synced into the main spec (the traceability tool indexes main specs only; see the design's D4 ordering).
- Not affected: preset catalogs, equipment handler, shop/economy prices (existing price table keys reused), lore startup DB sync (item/preset registries are already module-only, not DB-mirrored), command surface (no player command changes, so `docs/game/commands.md` is untouched).
- No backward-compatibility or migration work: the project is unreleased with zero users.
