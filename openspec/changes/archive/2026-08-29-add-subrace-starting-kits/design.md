# Design: add-subrace-starting-kits

## Context

`world/rules/character_creation.activate_player_character` writes `inventory` from `PLAYER_PRESET_REGISTRY[preset_key].inventory_list()` for preset mode and `[]` for custom mode. The preset path is guarded by `_validate_preset_starting_items` at `world/lore/player_presets.py` load time (every item key must exist in `ITEM_REGISTRY`, positive integer quantity, no duplicate key per preset). `SUBRACE_REGISTRY` holds 15 subraces across human (5), elf (3), and beastfolk (7). `ITEM_REGISTRY` already carries a broad basic catalog (`plain_sword`, `iron_dagger`, `hunters_longbow`, `leather_armor`, `chainmail`, `mage_robe`, `apprentice_focus_staff`, accessories, etc.). Custom-created characters start with an empty inventory and no identity-flavored gear.

Constraints (AGENTS.md / design doc): lore registries are the source of truth with frozen dataclasses and keyed registries; the deterministic core is the sole state writer — a lore registry only declares data and the activation service applies it; activation stays all-or-nothing; item presentation metadata is closed-vocabulary and registry-owned; the project is unreleased, so no compatibility shims.

## Goals / Non-Goals

**Goals:**

- Every registered subrace has a basic starting kit of registered EQUIPMENT items (every kit key declares an `equipment_slot`) whose flavor matches the subrace (heavy weapons for 熊人, daggers for 貓人, staff/robes for 伊歐拉斯, etc.), so every registered race likewise has fitting starting gear through its subraces.
- Custom activation hands the chosen subrace's kit into `inventory` inside the existing activation transaction; failure before commit is impossible by construction (load-time validation).
- Kits may freely share item keys; basic gear is a common pool, not per-subrace bespoke items.
- The spec states only the invariant and the activation behavior; the concrete per-subrace contents stay out of the spec and out of data-specific tests.

**Non-Goals:**

- No change to preset catalogs or preset activation (a preset's declared kit already wins; subrace kits are the custom-mode floor, not a preset override).
- No new mechanics: kit items are existing `ItemDefinition` shapes with an `equipment_slot` (the equipment-only kit rule is validator-enforced); no use-mechanics, ammo, stat, or price-schema additions.
- No change to the character-import path: the import loader keeps record-owned `inventory` and never calls `activate_player_character`, so imported characters are structurally outside the kit contract.
- No currency grant (wallet stays 0), no DB sync of the kit registry, no shop changes, no player-command changes.
- No per-subrace data tests asserting which specific item each subrace receives.

## Decisions

### D1: New module `world/lore/starting_kits.py`, not a field on `Subrace`

`SubraceStartingKit` is a frozen dataclass (`subrace_key`, `items: tuple[tuple[str, int], ...]`, plus an `inventory_list()` helper mirroring `PlayerPreset.inventory_list()`), and `SUBRACE_STARTING_KIT_REGISTRY: dict[str, SubraceStartingKit]` is keyed by subrace key (the same module-level mapping idiom as every other lore registry). A module-load validator rejects: a subrace in `SUBRACE_REGISTRY` with no kit entry, a kit entry for an unknown subrace, an empty kit, an item key absent from `ITEM_REGISTRY`, an item key whose definition carries no `equipment_slot` (kits are equipment-only — consumables and inspect-only items can never compose one), a duplicate item key within one kit, or a non-positive/non-boolean-integer quantity.

Why not add `starting_items` to the `Subrace` dataclass: `Subrace` is species/branch identity mirrored into the lore DB (`sync.py` serializes it via `asdict`), while starting gear is a game-starting-state concern; the closest precedent `PLAYER_PRESET_REGISTRY` carries starting items as its own module-level registry and is not DB-mirrored. A separate registry keeps the DB mirror payload unchanged and keeps the validator precedent (D-shape of `_validate_preset_starting_items`) directly reusable. Alternative considered and rejected: putting the map inside `world/rules/` — rejected because it is static world data (lore registry = source of truth), and the rules layer only reads and applies it.

### D2: Activation resolves the kit like the preset path resolves the preset

In `activate_player_character`, `inventory_value` becomes: preset mode → `PLAYER_PRESET_REGISTRY[preset_key].inventory_list()` (unchanged); custom mode → `SUBRACE_STARTING_KIT_REGISTRY[subrace].inventory_list()` (flattened repeated-key list, identical storage shape). The lookup happens where the other attribute values are computed, before the transaction opens; an unknown custom subrace can never reach the write because preflight already requires registry membership, and a missing kit is impossible because load-time validation guarantees total coverage — but the lookup still raises `CharacterCreationError` (not a raw `KeyError`) so even a future registry-loading bug fails pre-persistence like every other activation error.

### D3: Kit contents live in design/tasks data, and reuse shared catalog items

Reuse of existing items is the default (basic gear is shareable: e.g. `leather_armor`, `iron_dagger`, `plain_sword` appear in several kits). Only where no existing item fits the archetype does the change add a registry entry. Planned additions (all reusing existing `PRICE_TABLE` keys, closed presentation vocabularies, common/uncommon rarity, sellable equipment):

| item key | display (zh) | slot | price table | flavor |
|---|---|---|---|---|
| `wooden_club` | 木製棍棒 | weapon_main | mundane_weapon | human_laborer starter weapon |
| `gilded_saber` | 鍍金軍刀 | weapon_main | mundane_weapon | human_royal |
| `great_axe` | 双手巨斧 | weapon_main | mundane_weapon | bearkin heavy fighter |
| `ashen_scimitar` | 灰燼彎刀 | weapon_main | mundane_weapon | ciaran blade tradition |
| `steel_fang_dagger` | 鋼牙短刀 | weapon_main | mundane_weapon | catkin/tigerkin shared main-hand dagger |
| `prism_charm` | 三稜晶符 | accessory | magic_accessory | eolas magical aptitude |

Planned kit loadouts (quantity 1 unless noted; all keys otherwise existing catalog entries):

| subrace | kit |
|---|---|
| human_royal | gilded_saber, chainmail, silver_hairpin |
| human_noble | knight_blade, leather_armor, silver_hairpin |
| human_wealthy | knight_blade, chainmail, silver_hairpin |
| human_commoner | plain_sword, leather_armor |
| human_laborer | wooden_club, leather_armor |
| fionnen | hunters_longbow, leather_armor |
| ciaran | ashen_scimitar, leather_armor |
| eolas | apprentice_focus_staff, mage_robe, prism_charm |
| wolfkin | plain_sword, iron_dagger, leather_armor, wolf_fang_necklace |
| catkin | steel_fang_dagger, iron_dagger, leather_armor |
| bearkin | great_axe, chainmail |
| rabbitkin | hunters_longbow, leather_armor |
| bovinekin | plain_sword, iron_shield, chainmail |
| tigerkin | steel_fang_dagger, hunting_throwing_axe, leather_armor |
| foxkin | apprentice_focus_staff, mage_robe, pilgrim_medallion |

Guidance (not validator-enforced, review-time convention): kits use only basic/common-to-uncommon sellable gear — never relic/epic/legendary keepsakes (this is why `protective_ring`, an EPIC magic-accessory, is excluded even though its price band is a registry `magic_accessory`). Every new and reused kit key carries an `equipment_slot`, so the equipment-only validator rule (D1) holds for the whole table. `world/lore/tests/test_items.py::test_every_registered_item_resolves_complete_metadata` is an EXISTING closed-catalog contract test of `item-presentation-metadata`; updating its expected key set with the six new keys is maintenance of that pre-existing contract, not a new data-specific test — no other per-item test for the new gear is authored (the user constraint forbids authoring data tests, not keeping the existing suite green).

### D4: Spec records the invariant; tests verify mechanism, not data

The delta spec (in `player-character-creation`) states: (1) every registered subrace SHALL have a non-empty basic starting kit of equipment items (every kit key carries an `equipment_slot`) whose keys exist in `ITEM_REGISTRY`, validated at load, and (2) custom activation SHALL grant that kit as the starting inventory atomically with the rest of activation, while preset activation SHALL keep granting only its declared inventory. Tests: a registry-coverage test (kit keys exactly cover `SUBRACE_REGISTRY`; every kit is non-empty; every kit item resolves in `ITEM_REGISTRY` with a non-null `equipment_slot`; validator rejects broken kits via the same construction-based pattern used for presets), and an activation behavior test iterating all subraces with `subTest` asserting `db.inventory == kit.inventory_list()` (data-agnostic: it follows the registry, so kit retuning never breaks tests). No test hard-codes a specific subrace→item mapping.

Traceability ordering (per `docs/development/spec-test-traceability.md`): `tools.spec_traceability` indexes only main specs under `openspec/specs/`, and an annotation with a not-yet-synced ID is reported as `unknown-requirement-id`. During apply these behavior tests therefore ship WITHOUT `covers_requirement` annotations for the two new requirements; the delta must first be synced into the main spec (archive/sync workflow), the exact IDs taken from `uv run --locked python -m tools.spec_traceability list`, and only then are the literal-ID annotations added to the tests whose assertions establish the requirements, with `check` run green afterwards. The behavior tests exist from apply time so the annotations can land the moment the main IDs do.

## Risks / Trade-offs

- Existing test `test_activation_persists_identity_traits_and_empty_mechanical_state` asserts custom activation leaves `inventory == []` → updated in this change to expect the `human_commoner` kit's flat list via the registry (not a hard-coded item list).
- Closed-catalog test in `world/lore/tests/test_items.py` pins the exact `ITEM_REGISTRY` key set → updated in the same change with the six new keys; forgetting it is a loud test failure, not silent drift.
- Kit balance: basic gear could unbalance early economy → kits reuse the same common items presets already ship with and only sellable mundane gear; any retune is a one-line registry-data edit with zero test churn (D4).
- Elf kits include a magic-accessory (`prism_charm`) whose price band is high (10k–100k copper) → it is sellable and rare-ish by price table only; rarity remains uncommon; acceptable because starting gear is never sold for full value at creation and no economy rule reads kits.
- `storage_pouch`-style convenience items deliberately excluded → kits stay combat/identity gear; adding utility gear later is pure data.

## Migration Plan

Unreleased project: no migrations. Existing pending shells simply receive their kit at activation; already-activated characters are untouched (the change only governs activation time). Rollback = revert commits.

## Open Questions

None blocking: the exact kit table is reviewable data that can be retuned without spec or test changes.
