# Editorial review: 地標儀式文本（landmark-rite-content）

## 1. 審查結論與範疇

本文件記錄 `world/lore/rites/content/landmark_rites.yaml` 全數十個場景的逐項審查，審查日期為 2026-11-14。範圍涵蓋本次交運的五個原型（`spring`、`statue`、`megalith`、`tower`、`tree`）、每個原型兩個選項的 `self` 場景，以及一百二十個行政區的原型指派。

本審查為人工判斷的紀錄。聲調、用字、敘事節拍與情節品質由人閱讀判定，專案內沒有任何測試斷言這些內容；`world.lore.tests.test_rite_content_document` 只證明本文件能通過嚴格載入器，`world.lore.tests.test_rite_content` 只證明載入與安裝機制。場景行號以各場景 `lines` 序列的第一行起算。

審查同時確認了本次交運刻意留給後續變更的部分。每個選項的 `watch` 皆為 `null`（`landmark-rite-watch-perspectives` 另行撰寫）、每個原型只有兩個選項（第三選項屬 `landmark-rite-third-option`），且未觸及任何機制、規則或介面程式碼。

## 2. 權威參考來源對照

- `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §6.1、§6.2：文件形狀與欄位界線，`self` 場景一至三十二行、至少一行旁白、說話者限 `actor` 與 `host`。
- 同文件 §6.3：十個原型的代表地標與儀式調性；本次只交運表中前五列。
- 同文件 §11：成人內容與撰寫規則第一至第八條，本文件逐條核對。
- `tmp/story_settings/world_info.md`：世界觀。伊洛瑟恩為日式劍與魔法奇幻，基調輕鬆冒險；光明教會以肉體交融為崇神之禮，聖所以性服務為修道之途；精靈族對性與裸露沒有羞恥概念，其他種族出於敬畏視而不見。
- `content/maps/districts.yaml`：行政區與地標名稱的唯一來源，每個行政區皆帶 `district_name_zh` 與 `landmark_name_zh`。
- `world/lore/sexual_vocab.py` 與既有對話文本：私處、花蒂、乳房、腰腹、大腿、頸項、臀部等身體部位用語沿用既有詞彙表與已審查文本，不另造新詞。

## 3. 原型、監護者與選項數值

監護者一律為女性、非人存在或無性別的力量，沒有男性或男性形體的角色出現，也沒有男性伴侶參與儀式。

| 原型 | 監護者（`guardian_name_zh`） | 形體（`guardian_form_zh`） |
| --- | --- | --- |
| `spring` | 泉之聲 | 石底滲出的水聲，只在有人俯身時聚成一句話。 |
| `statue` | 白石守望者 | 石像胸口滲出的女聲，只在掌心貼上時應答。 |
| `megalith` | 石陣的低鳴 | 石縫間共鳴的低音，沒有形體，只在石頭被觸碰時應答。 |
| `tower` | 塔頂的風 | 繞塔而行的風聲，只在最高一層的窗口凝成說話的形狀。 |
| `tree` | 樹心的低語 | 從年輪深處傳出的女聲，只在樹皮被貼住時呼吸。 |

| 原型 | 選項 | `label_zh` | `seconds` | `shame` | `exposure` |
| --- | --- | --- | --- | --- | --- |
| `spring` | `drink` | 俯身飲下 | 180 | 1 | 0 |
| `spring` | `wade` | 踏入泉心 | 240 | 2 | 1 |
| `statue` | `touch` | 伸手撫過 | 300 | 2 | 0 |
| `statue` | `kneel` | 跪在石前 | 360 | 2 | 1 |
| `megalith` | `trace` | 沿著刻紋走 | 240 | 1 | 1 |
| `megalith` | `circle` | 繞行石環 | 300 | 0 | 1 |
| `tower` | `climb` | 登上塔頂 | 360 | 2 | 2 |
| `tower` | `bell` | 敲響風鐘 | 240 | 1 | 1 |
| `tree` | `embrace` | 抱住樹身 | 300 | 0 | 0 |
| `tree` | `rest` | 靠在根上 | 180 | 0 | 1 |

數值彼此一致。身處石龕、石階與樹身等閉鎖空間的選項 `exposure` 為 0；敞向天空、海面或荒原者較高，`tower.climb` 的窗口毫無遮蔽，`exposure` 定為 2。建立在被注視之上的 `statue` 兩個選項、建立在被水吞沒之上的 `spring.wade`，以及把身體交給風與高度的 `tower.climb`，`shame` 皆為 2；以觸碰、共振與根系為主的選項維持 0 或 1。

## 4. 逐原型審查（每個選項一列）

「資訊節拍」為角色取得情報的那幾行，「高潮節拍」為身體反應與物件回應同時完成的那一行，「§11」欄逐條標示第一至第八條的通過情形。每個選項的場景以動作、聲響、物件回應與身體反應呈現取得情報、與地標物件互動、抵達高潮三拍，沒有「你得知了」「你感到」一類直述。

### `spring`（泉之聲）

場景 `rite.spring.drink.self` 以石龕水面為物件，飲下泉水是互動，泉底的手托住身體並在顫抖時浮出一句地名。場景 `rite.spring.wade.self` 則走進泉心讓水沒過身體，水底亮點排成路線，另一道暖流把人留在水裡。兩者是不同的故事，一個以口唇承接，一個以體重交換。

| 選項 | 物件互動 | 資訊節拍（行） | 高潮節拍（行） | §11 |
| --- | --- | --- | --- | --- |
| `drink` | 俯身貼上水面飲下，水底的手扣住下巴、分開私處 | 3、7（問句換來地名與繞行方向） | 6（水聲停了半拍，水面浮起一句話） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |
| `wade` | 踏入泉心，水由腳背升到腰腹，水底的手托起臀部 | 4、7（亮點排成往北的線） | 6（亮點在顫抖的一瞬閃過，路線刻進眼裡） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |

### `statue`（白石守望者）

場景 `rite.statue.touch.self` 中，掌心貼上石像腰腹，石面回溫，眼窩映出塌橋的路，石縫裡的指節貼上私處。場景 `rite.statue.kneel.self` 中，跪在石階讓石像看見背部，掌心積的砂水沿背脊流下並推進身體，痕跡排出一個名字。前者以觸碰換取記憶，後者以被觀看換取地名，兩者的物件互動完全不同。

| 選項 | 物件互動 | 資訊節拍（行） | 高潮節拍（行） | §11 |
| --- | --- | --- | --- | --- |
| `touch` | 站上石階、掌心貼住石像腰腹，石縫滲出看不見的指節 | 5、7（眼窩映出塌橋，繞東邊淺灘） | 6（膝蓋撞在石階，石像胸口的句子落下） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |
| `kneel` | 跪在石階、裙襬滑到腰後，石像掌心傾斜讓砂水流下 | 6、7（砂水痕跡排出一個名字） | 6（額頭抵著石階，熱潮擴到整條脊背） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |

### `megalith`（石陣的低鳴）

場景 `rite.megalith.trace.self` 中，指尖沿刻紋走到最後一格，低鳴轉成貼著皮膚的震動，石環亮起一道光照出崩塌的路。場景 `rite.megalith.circle.self` 中，繞行石環七圈，共鳴在第六圈卡住身體，躺上中央石板後低鳴連成長音，調子留在嘴裡。前者由指節帶路，後者由腳步累積，節拍與物件互不重複。

| 選項 | 物件互動 | 資訊節拍（行） | 高潮節拍（行） | §11 |
| --- | --- | --- | --- | --- |
| `trace` | 指尖嵌進刻紋走完石環，石面壓上私處並磨過花蒂 | 3、6、7（最後一格亮起的光指出北邊的路） | 6（震動在最後一格停住，熱意從腿根炸開） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |
| `circle` | 沿淺痕繞行七圈，振動卡在花蒂上，最後倒在中央石板 | 6、7（調子換來守林人的放行） | 6（腰腹跟著抽搐，熱潮濕了石板） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |

### `tower`（塔頂的風）

場景 `rite.tower.climb.self` 中，登上無窗扇的塔頂，裙子被風掀到腰上，氣流把人抵在窗框，顫抖時煙柱被吹成直線指向斷橋。場景 `rite.tower.bell.self` 中，背貼鏽死的石鐘讓風搖響它，震動順背脊下行，鐘聲回來時帶著方向。前者把身體交給高度與風，後者把背交給鐘腔的共鳴。

| 選項 | 物件互動 | 資訊節拍（行） | 高潮節拍（行） | §11 |
| --- | --- | --- | --- | --- |
| `climb` | 爬上塔頂、抓住窗框，風從背後鑽進裙底抵住私處 | 6、7（煙柱直線落在斷橋位置，那不是炊煙） | 6（腳尖離地，熱意衝上頸項） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |
| `bell` | 背貼鐘口讓風穿過鐘腔，整座塔震動 | 6、7（餘音滾回時帶著一段方向） | 6（叫出聲時鐘響了） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |

### `tree`（樹心的低語）

場景 `rite.tree.embrace.self` 中，環抱樹身，樹皮貼住胸口，根部纏上大腿，細枝沿私處滑動，樹脂流成一條指著西邊的細線。場景 `rite.tree.rest.self` 中，躺進落葉凹地，根鬚把人按在地面，樹冠讓開一道縫露出乾河床。前者以站立擁抱換取一句話，後者以躺下交出身體換取一條河床，兩者的物件互動與資訊來源都不同。

| 選項 | 物件互動 | 資訊節拍（行） | 高潮節拍（行） | §11 |
| --- | --- | --- | --- | --- |
| `embrace` | 環住樹身、樹皮貼住乳房與腰腹，根部纏上大腿與臀部 | 6、7（樹脂流成指著西邊的細線） | 6（樹枝托離地面，熱潮落在根上） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |
| `rest` | 躺進落葉凹地，根鬚繞住大腿與腰腹，細根繞住花蒂 | 6、7（樹冠讓開，露出通往西邊的乾河床） | 6（背在落葉裡拱起，樹根跟著收緊） | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ |

## 5. §11 逐條檢核

1. **監護者不是男性。** 五個原型分別為水聲、石像滲出的女聲、無形體的低音、風聲與樹心的女聲，全部符合。
2. **沒有與男性或男性形體者交合。** 十個場景的互動對象只有地標物件、地標顯化的力量與自己的身體，沒有第二個人類或獸人角色出現。
3. **三拍皆有世界觀內的理由。** 每個選項都是監護者以一句問答換取觸碰，物件在被使用時才回答，高潮即地標收下或記下的東西；取得情報以動作與物件回應呈現，沒有直述「你得知」。
4. **展示而非告知。** 全篇沒有「你得知了」「你感到非常興奮」一類句子，情報由水面浮出的話、眼窩映出的路、砂水排出的名字、光照出的路、樹脂流成的線與鐘聲帶回的方向呈現。
5. **`self` 場景為第二人稱並預設女性身體。** 全部場景以「你」敘述，身體描寫為乳房、腰腹、臀部、大腿內側、私處、花蒂；每個選項 `watch` 為 `null`，本次不交運第三人稱場景，也不出現 `{name}` 佔位。
6. **正體中文、全形標點、日式劍與魔法語彙。** 全篇未出現江湖、客官、過招、劍招、招式、祕技、拜師、功夫、掌門一類中式武俠詞彙，也沒有指令、系統、選單、按鈕、熟練度等出戲用語。
7. **場景識別碼與修訂號。** 十個場景識別碼為 `rite.<原型>.<選項>.self`，修訂號皆為 `r1`；本文件為首次交運，尚無需遞增。
8. **情報節拍不寫入圖鑑。** 場景只產生文字與身體反應，未提及、也未觸發任何圖鑑或探索紀錄的寫入；本變更不含程式碼。

## 6. 語言與風格檢核

- 初稿審查時改寫了兩類問題。重複量詞（「一下一下」「一粒一粒」「一圈一圈」）改為單一動作描述；任何落在「，」或「。」前的句末「的」皆改寫為名詞收尾。
- 全篇使用全形標點；中文字與英數字之間沒有混排，場景內沒有半形逗號、冒號、括號或反引號。
- 沒有敬稱「您」，也沒有第一人稱複數；敘述一律為第二人稱。
- 沒有破折號、沒有對比式句型、沒有排比堆疊；資訊以動作與物件回應交代。
- 世界觀檢核方面，場景沿用世界觀的輕鬆冒險基調，未加入黑暗或沉重劇情；地標、地名與行政區名稱全部取自 `content/maps/districts.yaml`，場景內沒有自創地名、組織、物品或職稱。監護者台詞提到的「守林的人」與「巡守的人」是通用指稱，不是專有名詞，也未建立新的組織或職位。

## 7. 行政區指派

指派依設計 D3 的三級規則完成。二十五個 §6.3 前五列代表地標取其所在列的原型；十九個依「地標是什麼」直接歸類（泉、井、雕像與雕琢形體、立石與石柱與巨石、塔、樹）；其餘七十六個行政區的地標屬於尚未交運的家族（墓、礦、門、崖、廣場）或僅能依儀式調性就近安置，全部置於 `# provisional: reassigned by landmark-rite-content-completion` 註解行之後，交由 `landmark-rite-content-completion` 重新指派。

七十六個暫定指派按「地標本來屬於哪個家族，或為何只能就近安置」分組如下，供後續變更逐項重新指派。

| 分組 | 理由 | 本次指派 | 行政區 |
| --- | --- | --- | --- |
| 墓與死者 | `grave` 家族尚未交運，依設計 D3 的「墓→`statue`」安置 | `statue` | `bell_vale`、`old_battlefield`、`pearl_bay_coast`、`bison_plateau`、`ancestor_cairn_hills` |
| 洞窟、礦坑、窯與磨坊 | `mine` 家族尚未交運，依「洞窟或礦坑→`megalith`」安置 | `megalith` | `amethyst_mine_vale`、`mill_reach`、`limestone_terrace`、`tidesong_dunes`、`mithril_foothills`、`shaman_cave_woods`、`grizzly_vale`、`starfall_plain` |
| 門、橋、閘、渡與道標 | `gate` 家族尚未交運，依「門或橋→`megalith`」安置 | `megalith` | `north_road_uplands`、`westpass_uplands`、`silverbrook_vale`、`red_earth_hills`、`white_sand_coast`、`whalebone_heath`、`echo_canyon`、`imperial_capital_plain`、`canal_plain`、`imperial_river_reach`、`flax_plain`、`south_pass_east_slopes`、`east_branch_ford`、`estuary_flats`、`imperial_wheatlands`、`south_pass_west_slopes`、`spice_road_plain`、`imperial_delta`、`salt_road_hills`、`forest_rim_heath`、`great_pass_east` |
| 崖、瀑布、峰與岩壁 | `cliff` 家族尚未交運，依「瀑布或斷崖→`spring` 或 `tower`」安置 | `spring` 或 `tower` | `maple_vale`、`icespring_gorge`（`spring`）；`eyrie_cliffs`、`salt_cliff_coast`、`rift_scarp_plateau`、`thunder_peak_range`、`obsidian_ridge`、`honey_vale`、`iron_vein_highlands`（`tower`） |
| 城市廣場 | `plaza` 家族尚未交運，依「廣場→`statue`」安置 | `statue` | `royal_river_valley` |
| 其餘地標 | 不屬於後續五個家族，或家族歸屬未定；依儀式調性就近安置 | `spring`、`statue`、`tree` 或 `tower` | `vineyard_slopes`、`white_ram_foothills`、`east_river_fields`、`olive_slopes`、`anvil_vale`、`north_pass_east_slopes`、`sunken_bell_lake`、`spruce_foothills`、`sunrise_downs`、`black_soil_plain`、`hawkwing_heath`、`rose_plain`、`tide_wind_downs`、`stormrock_heath`、`emerald_lake_plain`、`eastern_pasture`、`river_isle_flats`、`herbal_plain`、`griffin_plateau`、`bluewave_downs`、`cloudsea_foothills`、`giants_stair_highlands`、`imperial_south_shore`、`sea_serpent_slopes`、`bear_claw_woods`、`north_pass_west_slopes`、`war_drum_highlands`、`pine_hunting_grounds`、`giant_rockfall_slopes`、`falcon_rise`、`blood_moon_vale`、`rivers_watch_woods` |

本次文件共指派 **120** 個行政區，其中 **44** 個依規則一與規則二直接歸類，**76** 個為暫定指派。