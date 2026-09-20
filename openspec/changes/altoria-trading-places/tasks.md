Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Places

- [ ] 1.1 Add 聖潔王都鍛造鋪 to `world/lore/settlements/places_altoria.py`: interior name and
  description, exterior (0,2), doorway naming, host 維爾登·黑潭 / `聖潔王都鍛造鋪鐵匠` /
  human / human_plains / male, merchant profession, and the weapons assortment.
- [ ] 1.2 Add 聖潔王都餐館 the same way at exterior (2,1), host 西格瑪·庫柏 /
  `聖潔王都餐館老闆` / male, selling the food assortment.
- [ ] 1.3 Add 聖潔王都裁縫坊 at exterior (2,3), host 妮絲塔·狐溪 / `聖潔王都裁縫坊坊主` /
  female, selling the armour assortment.
- [ ] 1.4 Narrow 阿爾托利亞雜貨商店's assortment reference to sundries alone. Verify the union of
  goods across all five capital places equals the pre-split offered set with no key in two places.

## 2. Hours

- [ ] 2.1 Add the three shop rows to `world/rules/rulebook/commerce.yaml` with opening, closing and
  restock hours, at par scale and with no overrides. Verify the catalog loads.

## 3. Lore text

- [ ] 3.1 Replace 霍布·熔爐 (line 170) and 柯爾特·暖爐 (line 265) in
  `docs/lore/settlement-locations.md` with the authored names, and add the 裁縫坊 host name
  alongside the existing 艾莉諾·針影 example if that line also names a placeholder.

## 4. Handoff

- [ ] 4.1 Verify all five interiors and their doorways appear after synchronization and that a
  repeated run duplicates nothing, with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy`.
- [ ] 4.2 Verify each shop's stock listing names its own place and that a purchase settles at each,
  with
  `uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_guild_economy_commands`.
- [ ] 4.3 Run `uv run --locked python -m tools.test_data_lint check` and
  `openspec validate altoria-trading-places --strict`.
