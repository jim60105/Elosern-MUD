# NPC 人物設定全名冊審閱紀錄

本文件記錄 Elosern 出貨 NPC 人物設定名冊的全面審閱結果。依據設計規範（`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §5.2、§11.2 與 OpenSpec 變更 D4），全名冊涵蓋 63 處出貨來源，分屬 9 個內容切片。本審閱檢視各切片的資料結構、角色卡契約、跨切片同職業對話表現，並記錄自動化驗證與模型審閱狀態。

---

## 1. 出貨來源與人物設定總表

出貨名冊包含 25 處地點服務主人、25 張劇本對話表、7 名公會考核官、4 組預設同行夥伴宣告、1 處離線任務模板佔位者，以及 1 份出貨匯入範例，共計 63 處出貨來源。

| 來源類型（Kind） | 來源識別碼（Key） | 對應設定檔或預設卡（Profile / Preset） | 所屬切片（Owner） | 審閱狀態 |
|---|---|---|---|---|
| `place_host` | `altoria_eatery_owner` | `altoria_eatery_owner` | `altoria_lower` | 通過 |
| `place_host` | `altoria_tavern_keeper` | `altoria_tavern_keeper` | `altoria_lower` | 通過 |
| `place_host` | `altoria_innkeeper` | `altoria_innkeeper` | `altoria_lower` | 通過 |
| `place_host` | `altoria_bathhouse_keeper` | `altoria_bathhouse_keeper` | `altoria_lower` | 通過 |
| `place_host` | `altoria_guard_captain` | `altoria_guard_captain` | `altoria_lower` | 通過 |
| `dialogue_table` | `altoria_eatery` | `altoria_eatery_owner` | `altoria_lower` | 通過 |
| `dialogue_table` | `altoria_tavern` | `altoria_tavern_keeper` | `altoria_lower` | 通過 |
| `dialogue_table` | `altoria_lodging` | `altoria_innkeeper` | `altoria_lower` | 通過 |
| `dialogue_table` | `altoria_bathhouse` | `altoria_bathhouse_keeper` | `altoria_lower` | 通過 |
| `dialogue_table` | `altoria_guardhouse` | `altoria_guard_captain` | `altoria_lower` | 通過 |
| `place_host` | `altoria_merchant` | `altoria_merchant` | `altoria_trade` | 通過 |
| `place_host` | `altoria_blacksmith` | `altoria_blacksmith` | `altoria_trade` | 通過 |
| `place_host` | `altoria_tailor` | `altoria_tailor` | `altoria_trade` | 通過 |
| `place_host` | `altoria_jeweller` | `altoria_jeweller` | `altoria_trade` | 通過 |
| `place_host` | `altoria_alchemist` | `altoria_alchemist` | `altoria_trade` | 通過 |
| `place_host` | `altoria_merchant_master` | `altoria_merchant_master` | `altoria_trade` | 通過 |
| `dialogue_table` | `altoria_general_store` | `altoria_merchant` | `altoria_trade` | 通過 |
| `dialogue_table` | `altoria_forge` | `altoria_blacksmith` | `altoria_trade` | 通過 |
| `dialogue_table` | `altoria_tailor` | `altoria_tailor` | `altoria_trade` | 通過 |
| `dialogue_table` | `altoria_jeweller` | `altoria_jeweller` | `altoria_trade` | 通過 |
| `dialogue_table` | `altoria_alchemist` | `altoria_alchemist` | `altoria_trade` | 通過 |
| `dialogue_table` | `altoria_merchant_hall` | `altoria_merchant_master` | `altoria_trade` | 通過 |
| `place_host` | `altoria_guild_master` | `altoria_guild_master` | `altoria_guild` | 通過 |
| `dialogue_table` | `guild_staff` | `altoria_guild_master` | `altoria_guild` | 通過 |
| `guild_examiner` | `F` | `guild_examiner_f` | `altoria_guild` | 通過 |
| `guild_examiner` | `E` | `guild_examiner_e` | `altoria_guild` | 通過 |
| `guild_examiner` | `D` | `guild_examiner_d` | `altoria_guild` | 通過 |
| `guild_examiner` | `C` | `guild_examiner_c` | `altoria_guild` | 通過 |
| `guild_examiner` | `B` | `guild_examiner_b` | `altoria_guild` | 通過 |
| `guild_examiner` | `A` | `guild_examiner_a` | `altoria_guild` | 通過 |
| `guild_examiner` | `S` | `guild_examiner_s` | `altoria_guild` | 通過 |
| `place_host` | `altoria_high_priestess` | `altoria_high_priestess` | `altoria_upper` | 通過 |
| `place_host` | `altoria_sanctum_deacon` | `altoria_sanctum_deacon` | `altoria_upper` | 通過 |
| `place_host` | `altoria_noble_watch_captain` | `altoria_noble_watch_captain` | `altoria_upper` | 通過 |
| `place_host` | `altoria_drill_instructor` | `altoria_drill_instructor` | `altoria_upper` | 通過 |
| `place_host` | `altoria_academy_dean` | `altoria_academy_dean` | `altoria_upper` | 通過 |
| `dialogue_table` | `altoria_temple` | `altoria_high_priestess` | `altoria_upper` | 通過 |
| `dialogue_table` | `altoria_sanctum` | `altoria_sanctum_deacon` | `altoria_upper` | 通過 |
| `dialogue_table` | `altoria_noble_watch` | `altoria_noble_watch_captain` | `altoria_upper` | 通過 |
| `dialogue_table` | `altoria_drill_yard` | `altoria_drill_instructor` | `altoria_upper` | 通過 |
| `dialogue_table` | `altoria_academy` | `altoria_academy_dean` | `altoria_upper` | 通過 |
| `place_host` | `ciaran_elenis` | `ciaran_elenis` | `ciaran_homes_a` | 通過 |
| `place_host` | `ciaran_gwenaera` | `ciaran_gwenaera` | `ciaran_homes_a` | 通過 |
| `place_host` | `ciaran_hailiel` | `ciaran_hailiel` | `ciaran_homes_a` | 通過 |
| `place_host` | `ciaran_lareneth` | `ciaran_lareneth` | `ciaran_homes_a` | 通過 |
| `dialogue_table` | `ciaran_elenis_home` | `ciaran_elenis` | `ciaran_homes_a` | 通過 |
| `dialogue_table` | `ciaran_gwenaera_home` | `ciaran_gwenaera` | `ciaran_homes_a` | 通過 |
| `dialogue_table` | `ciaran_hailiel_home` | `ciaran_hailiel` | `ciaran_homes_a` | 通過 |
| `dialogue_table` | `ciaran_lareneth_home` | `ciaran_lareneth` | `ciaran_homes_a` | 通過 |
| `place_host` | `ciaran_nireth` | `ciaran_nireth` | `ciaran_homes_b` | 通過 |
| `place_host` | `ciaran_teliel` | `ciaran_teliel` | `ciaran_homes_b` | 通過 |
| `place_host` | `ciaran_valwyn` | `ciaran_valwyn` | `ciaran_homes_b` | 通過 |
| `place_host` | `ciaran_vethiel` | `ciaran_vethiel` | `ciaran_homes_b` | 通過 |
| `dialogue_table` | `ciaran_nireth_home` | `ciaran_nireth` | `ciaran_homes_b` | 通過 |
| `dialogue_table` | `ciaran_teliel_home` | `ciaran_teliel` | `ciaran_homes_b` | 通過 |
| `dialogue_table` | `ciaran_valwyn_home` | `ciaran_valwyn` | `ciaran_homes_b` | 通過 |
| `dialogue_table` | `ciaran_vethiel_home` | `ciaran_vethiel` | `ciaran_homes_b` | 通過 |
| `starting_companion` | `violet_altoria:lidzia_rosenthal` | `lidzia_rosenthal` | `companions` | 通過 |
| `starting_companion` | `lidzia_rosenthal:violet_altoria` | `violet_altoria` | `companions` | 通過 |
| `starting_companion` | `yuka_darknight:yuna_darknight` | `yuna_darknight` | `companions` | 通過 |
| `starting_companion` | `yuna_darknight:yuka_darknight` | `yuka_darknight` | `companions` | 通過 |
| `quest_template_occupant` | `討伐林間盜匪:0:0` | `template_card` | `generated_quest_cards` | 通過 |
| `import_example` | `example_character` | `import_card` | `import_cards` | 通過 |

---

## 2. 跨切片同職業對話比較

我比對各個切片內扮演相同或相近社會職能的 NPC 對話風格，確認人物台詞具備各自獨立的世界觀與語氣，未出現單一職業模板通篇套用的情況。

### 商人職能比對（All Merchants）

王都下層、中層、上層與席亞蘭精靈村落皆設有具備交易功能的商人主人：

- **王都下層雜貨商人與餐館老闆**：下層商人如西格瑪‧庫柏面對冒險者時口吻親切直接，重視飽腹與生活實務，不談高深商律。
- **王都中層商業街專業匠人**：中層鐵匠戈爾德語氣粗獷硬朗，裁縫艾蕾娜講求衣著細節與布料工藝，煉金術士莫爾甘沉浸於藥劑實驗，商會會長貝爾納則展現管理商業契約的精明條理。中層商人對話反映王都法規、商會憑證與同行競爭，用語專業。
- **王都上層聖所執事**：聖所執事塞希莉亞身處純白聖所，言語克制柔和，專注於儀式用品與聖水供給，未出現市集叫賣氣息。
- **席亞蘭村落住家工匠**：格溫艾拉（刀刃製作）、席拉蓮（草藥採集）、妮瑞斯（毛皮獵戶）與薇希爾（布匹編織）皆在家中進行物品交易。她們的問候與回答皆以精靈聚落同胞或尋訪訪客為對象，說明自身手藝與山林產物，不使用「歡迎光臨」「公道價錢」等人類城鎮商販詞彙。

### 管事職能比對（All Attendants）

服務型 NPC 提供交談、休息或指引服務，不直接出售貨物：

- **旅店與澡堂掌管者**：爐火旅店老闆娘溫弗蕾德維持店內安寧，對深夜喧嘩者態度嚴格；澡堂掌管者伊莎貝爾重視隱私界線，維持泉水清潔與秩序。
- **守備隊長**：南門衛兵駐所隊長托瓦德長年駐守外門，對初到王都者提供公會方向指引；貴族區守備隊長羅德里克出身騎士階層，盤查嚴謹且自持階級尊嚴。
- **校場教官**：瓦爾特教官以軍隊操演口吻講話，要求訓練者專注於每一次揮劍與冥想。

### 長老與院長比對（Elder vs Dean）

席亞蘭村長伊蓮妮絲與王立魔法學院院長梅麗珊德皆居於聚落頂層指導者地位，呈現鮮明對比：

- **席亞蘭村長伊蓮妮絲（Elenis）**：活過悠長歲月的精靈長老，言談節奏緩慢平靜，寄語村落日常與林木平衡，給予後輩溫暖守望，未表現任何官僚權威。
- **王立學院院長梅麗珊德（Melisande）**：執掌王國最高魔法研究機構，說話精確權威，強調魔法理論體系與研究紀錄，要求問學者提出合乎邏輯的論述。

### 公會考核官隊列（Guild Examiners F–S）

公會考核官雷加（F 級）至奧古斯丁（S 級）專職於冒險者位階審查：

- 7 位考核官的人物卡皆符合精簡卡契約規範，清楚描繪各自退役經歷、戰鬥特徵與考核標準。
- 考核官無對話能力，其設定檔內的 `greeting` 與 `misunderstood` 欄位皆設定為 `None`，不包含任何對話台詞，符合其身為戰鬥對手的單一機制角色。

---

## 3. 審閱過程發現之問題與修正

在整合與比對各切片人物設定資料時，記錄下列設計問題與修正紀錄：

1. **劇本對話與指令詞解耦**：早期對話曾直接引用遊戲指令（如 `rest`、`sleep`、`train`），修正後改由角色於世界觀語境內說明床位、溫泉或練習場用途，完全移除介面指令名稱。
2. **問候語所有權唯一定義**：確認地點主人對話表的首句問候語為單一來源，地點主人設定檔內的 `voice.greeting` 強制維持 `None`，僅允許撰寫 `voice.misunderstood`（理解失敗回覆），消除問候語雙頭維護之風險。
3. **同伴人物設定單一真實來源**：依據設計修正案第 13a 條，起初始同伴直接自夥伴預設卡（`PlayerPreset`）的 `speech_style` 與 `greeting` 擴充欄位推導，不再維護重複的同伴人物設定切片。

---

## 4. 模型審閱狀態聲明

依據設計文件第 11.2 節規範，自動化測試驗證資料覆蓋度與確定性渲染，無法替代對角色性格獨特性的主觀閱讀體驗。

在此誠實聲明：

本階段完成全名冊 63 處來源的靜態語法檢查、精簡角色卡契約正規化、雙向名冊比對、對話映射檢查與啟動驗證測試。受限於本測試環境未掛載獲准的外部生成服務 API 金鑰，全名冊對話與提示詞未執行大規模模型自由對話測試。相關文案品質由作者與審閱團隊逐檔閱讀確認。
