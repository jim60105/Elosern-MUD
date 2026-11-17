# Elven village goods review

This is the human-read record for the eight local goods added by the
`elven-village-local-goods` change. No test asserts the wording here or in the
registry; the review below is the evidence that each name and summary was read
against the world sources before the change is archived.

Sources read:

- `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md`, 精靈族
  section: 斐歐恩族 (Fionnen, forest elf, light magic and archery, 翠綠森林村),
  伊歐拉斯族 (Eolas, all-element magic and divine secrets, 幽月谷村).
- `docs/lore/settlement-locations.md`, 聚落差異深論: 幽月谷村 grows tubers,
  beans and herbs, keeps spiders for silk, fires pottery and glass in a shared
  kiln, and practises magic at the 試煉場; 翠綠森林村 keeps bees, farms, does
  woodwork, boils 花蕊蜜園 honey with petals, and trains archery at the 靶道
  among the giant trees.
- `docs/lore/items.md` for the presentation contract (one Traditional Chinese
  line, at most 128 characters, no ASCII digit, no markup, no URL, no emoji)
  and the price-band vocabulary.

Every line below records that the item's name and summary were read against
those two sources and the village passages, and what the reader checked.

| key | name | summary | what the reader checked |
| --- | --- | --- | --- |
| `eolas_kiln_flatbread` | 幽月窯烤豆餅 | 幽月谷村共用窯烤出的豆餅，配著谷裡自種的香草一起吃。 | The shared kiln, the beans and the herbs are all village facts; the name says the food is baked, not bought. |
| `eolas_herb_tonic` | 幽月香草藥露 | 以幽月谷村梯田香草浸漬的藥露，飲下能恢復體力。 | Steeped herbs match the village's terrace herb growing; the summary names stamina only, never a number, and the effect itself lives in the rulebook. |
| `eolas_glass_pendant` | 幽月琉璃墜 | 幽月谷村共用窯燒成的琉璃墜，配戴時讓施法更沉穩。 | Glass from the shared kiln is village-made, and "steadies casting" describes the wearer's experience rather than the numeric adjustment. |
| `eolas_proving_wand` | 幽月練習短杖 | 伊歐拉斯族削來在試煉場練法術的短杖，導引魔力格外順手。 | A carved practice wand fits the Eolas magic study and the 試煉場 named in the village passage; no combat claim is made in prose. |
| `fionnen_wildflower_honey` | 森林百花蜜 | 翠綠森林村花蕊蜜園的蜂群釀成的百花蜜。 | The hives and the 花蕊蜜園 are village facts; the name avoids implying the candied petal product the same garden also makes. |
| `fionnen_beeswax_salve` | 森林蜂蠟膏 | 以蜂蠟與林間藥草熬成的敷膏，塗上能讓傷口收斂。 | Beeswax comes from the village hives and the forest supplies the herbs; the wound effect is a salve, and the amount lives in the rulebook. |
| `fionnen_archer_bracer` | 森林射手護腕 | 斐歐恩族弓手綁在持弓手臂上的木雕護腕，拉弓時更穩。 | Archery is the Fionnen specialty and woodwork is village work; the summary describes the worn object, not the agility bonus. |
| `fionnen_leafweave_garb` | 森林葉織獵衣 | 為在巨木之間穿行而織的輕獵衣，身手幾乎不受牽絆。 | The two-level village among the giant trees grounds the light hunting dress; the summary avoids armour numbers and names only freedom of movement. |

All eight names carry the village of origin in the lore table, every summary
is a single Traditional Chinese line with no ASCII digit, and every row's
effect wording agrees with `world/rules/rulebook/equipment_effects.yaml` and
`world/rules/rulebook/item_effects.yaml`.
