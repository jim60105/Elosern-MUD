Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Settlement and goods

- [x] 1.1 Add the `village_ciaran` row to `SETTLEMENT_REGISTRY` with the elven-village archetype
  and the village's zcoord, at par price scale.
- [x] 1.2 Add four elven-craft assortments — blades, garments, fare, sundries — to
  `world/lore/settlements/assortments.py` and their offer rules to
  `world/rules/rulebook/commerce.yaml`, at everyday village prices. Verify each resolves inside its
  items' price bands, which for the craft goods requires the masterwork band.

## 2. The four homes

- [x] 2.1 Add `world/lore/settlements/places_ciaran.py` with 海莉爾的家 off 練刀場, host
  海莉爾·斯塔爾法爾 / `暗影谷村鑄刃者` / elf / ciaran / female, selling the blades assortment.
- [x] 2.2 Add 拉瑞內斯的家 off 溪畔小徑 (拉瑞內斯·妮特布倫 / `暗影谷村花饌好手`, fare),
  瓦爾溫的家 off 村北古樹下 (瓦爾溫·斯蒂爾瓦特爾 / `暗影谷村蒐羅者`, sundries), and
  維特希爾的家 off 織房坡 (維特希爾·威爾德布瑞亞爾 / `暗影谷村織衣者`, garments) — all
  elf / ciaran / female.
- [x] 2.3 Write interior names and descriptions that read as dwellings: no counter, sign, shopfront
  or trade vocabulary anywhere in the text, and no 老闆/店主 in any title.
- [x] 2.4 Add the four shop rows with hours to `commerce.yaml` and verify all four interiors, their
  doorways and their hosts appear after synchronization with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`.

## 3. One good, two prices

- [x] 3.1 Add `elven_spider_silk` to the village collector's sundries assortment at an everyday
  village price. Do NOT touch the capital: it has offered this key since before this work began
  (`guild_economy.yaml:261`, 60,000 copper), so `commerce-assortment-registry` already carries it
  in the capital's sundries assortment. No override, addition or exclusion is involved.
- [x] 3.2 Confirm the capital references no elven assortment, and verify both offers resolve to
  one item key and one item definition with resolved prices three orders of magnitude apart, both
  passing band validation (`material` has no ceiling).

## 4. The no-special-case guarantee

- [x] 4.1 Verify a purchase from a village host settles wallet, inventory, stock, acquisition
  progress and affinity exactly as a capital purchase does, and that a displaced village host
  produces the same fixed anchoring refusal, with
  `uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_guild_economy_commands`.
- [x] 4.2 Verify the trade and shop-command paths contain no settlement-archetype branch or village
  special case.

## 5. Handoff

- [x] 5.1 Run `uv run --locked python -m tools.test_data_lint check`, register any new test module
  in `.github/evennia-shards.json`, and run
  `openspec validate ciaran-village-commerce --strict`.
