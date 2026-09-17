## 1. Orphan sweep and removal procedure

- [x] 1.1 List every `ITEM_REGISTRY` key that no codex item table catalogues, and record the result in the change notes. The expected result is an empty set; if it is not, every key found is deleted in this change together with its references per 1.2.
- [x] 1.2 Write down the reference surfaces a deletion must sweep, confirmed by inspection: `world/lore/shops.py` offered keys, `guild_economy.yaml` offers, `EquipmentModifierKey` and `equipment_effects.yaml`, `item_effects.yaml`, `world/lore/starting_kits.py`, `world/lore/player_presets.py`, and the quest definition and compile validators. Verify each one names item keys by grepping for a known key.
- [x] 1.3 Using a synthetic item key removed from a synthetic registry while a synthetic shop still offers it, assert the catalog load raises naming the key and builds no partial merchant. Annotate with `covers_requirement` for the dangling-reference requirement. Verify with `world.rules.tests.test_guild_config`.
- [x] 1.4 Same for an equipment-effect entry and a modifier binding naming an undefined key: assert the rulebook load raises naming the key rather than leaving an orphan. Verify with `world.rules.tests.test_equipment_effect_rulebook`.
- [x] 1.5 Same for an item-effect profile naming an undefined key: assert the two-sided close raises naming the key. Verify with `world.rules.tests.test_item_effects_rulebook`.
- [x] 1.6 Same for a starting kit, a character preset, and a quest objective or reward naming an undefined key: assert each validator rejects that record naming the key rather than granting nothing. Verify with `world.lore.tests.test_starting_kits`, `world.lore.tests.test_player_presets`, and the quest definition test label.
- [x] 1.7 Assert the completed-retirement case: a synthetic key removed together with every reference leaves startup succeeding and every loader closing with no unbound key and no orphan. Verify with the same labels.
- [x] 1.8 Add all of these to existing test modules so `.github/evennia-shards.json` needs no edit, confirm the annotation IDs against `uv run --locked python -m tools.spec_traceability list`, and verify with `uv run --locked python -m tools.spec_traceability check`.

## 2. Retire the obsolete race names

- [x] 2.1 Replace the summary of `ashen_scimitar` (基亞蘭族 → 精靈), `prism_charm` (伊歐拉斯族 → 精靈), `great_axe` (熊人 → 獸人), and `steel_fang_dagger` (貓科獵手 → 獸人獵手) with the codex text plus the registry's trailing 。. Verify the registry imports, which runs summary validation.
- [x] 2.2 Grep the registry for any remaining occurrence of 基亞蘭, 伊歐拉斯, 熊人, and 貓科 in player-visible text, and confirm none survives.

## 3. Replace the remaining divergent summaries

- [x] 3.1 Replace the summaries of the four elven village goods — `dark_elf_kimono`, `dark_elf_ninja_garb`, `elven_traditional_robe`, `crescent_earring` — with the codex text plus 。. Verify the registry imports.
- [x] 3.2 Replace the summaries of the two Church vestments `sister_vestments` and `saintess_vestments` with the codex text plus 。, and verify both stay inside the 128-code-point bound at import (109 and 103 including the period).
- [x] 3.3 Replace the summaries of the four royal and guild relics — `rose_crest_rapier`, `royal_signet_ring`, `royal_heirloom_pendant`, `silver_feather_earring`, `guild_recruit_badge` — with the codex text plus 。. Verify the registry imports.
- [x] 3.4 Replace the summaries of `baptismal_holy_water` and `black_maid_dress` with the codex text plus 。. Verify the registry imports.
- [x] 3.5 Confirm the 39 summaries differing only by the trailing 。 are left untouched, so the diff contains exactly 17 summary changes.

## 4. Display names

- [x] 4.1 Rename `dark_elf_kimono` to 精靈短袍傳統服飾 and `dark_elf_ninja_garb` to 精靈戰鬥服飾, keeping both keys. Verify the registry imports.
- [x] 4.2 Rename `rose_crest_rapier` to 薇歐蕾特親刻薔薇輕劍, `royal_signet_ring` to 薇歐蕾特的誕生細金戒, and `silver_feather_earring` to 十二歲的銀羽. Verify the registry imports.
- [x] 4.3 Update the display-name assertion in `world/lore/tests/test_items.py` and any other test naming a renamed item. Verify with `world.lore.tests.test_items`.
- [x] 4.4 Correct the prose line in `docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md` that still names two items by their old titles.

## 5. Rarity and the numbers it unlocks

- [x] 5.1 Change `sister_vestments` from `uncommon` to `rare`, then set its `equipment_effects.yaml` entry to the codex adjustments — `defense: -4`, `pleasure_gain: "+20%"`, `heal_gain: "+10%"`, top-level `exposure_bias: 1`. Verify the rulebook load accepts it, and verify the same numbers are refused if the rarity is reverted, confirming the rarity was the blocker.
- [x] 5.2 Change `saintess_vestments` from `epic` to `legendary`, then set its entry to `defense: -5`, `pleasure_gain: "+30%"`, `heal_gain: "+25%"`, top-level `exposure_bias: 2`. Verify the rulebook load accepts it.
- [x] 5.3 Verify the Church-of-Light doctrine coverage still passes for both: non-negative exposure bias, non-negative pleasure gain, a healing value present, and no suppression. Verify with the doctrine test label in `world.rules.tests.test_equipment_effect_rulebook`.
- [x] 5.4 Leave `silver_feather_earring`'s exposure bias as authored — the codex accessory table has no bias column and is silent rather than contradicting.

## 6. Shop price

- [x] 6.1 Correct `sister_vestments`'s offer in `guild_economy.yaml` to the codex reference of 3000/1500, and verify it lies inside the `armor` band and that the sell price does not exceed the buy price. Verify with `world.rules.tests.test_guild_config`.

## 7. Gate

- [x] 7.1 Run `uv run --locked python -m tools.test_data_lint check` and verify the gate passes with no new ledger entry.
- [x] 7.2 Run the focused labels touched by this change — `world.lore.tests.test_items`, `world.rules.tests.test_equipment_effect_rulebook`, `world.rules.tests.test_item_effects_rulebook`, `world.rules.tests.test_guild_config`, `world.lore.tests.test_starting_kits`, `world.lore.tests.test_player_presets` — plus `uv run --locked python -m tools.spec_traceability check`. Do not run the full suite.
- [x] 7.3 Run `openspec validate replace-temp-item-data --strict` and verify it reports the change as valid.
