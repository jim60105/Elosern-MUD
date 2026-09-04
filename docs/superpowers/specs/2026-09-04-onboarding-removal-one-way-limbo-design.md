# 移除 onboarding 與虛境單向通道設計（Onboarding Removal & One-Way Limbo Design）

日期：2026-09-04
狀態：已核准（待實作）

## 1. 問題陳述

現有新手教學（onboarding）把新角色搬到聖潔王都南門，由南門守衛（tag
`onboarding_guard`）以腳本對話引導玩家走訪城市、註冊公會，最後以完成公會
任務 `introductory_hunt` 作為教學結尾（`set_onboarded`）。整套系統橫跨
`world/rules/onboarding.py`、`world/onboarding/` 套件、角色持久欄位、startup
同步步驟、指令與 webclient 管線、以及 `onboarding-guide` 主規格。

未來的規劃是依種族從不同起始城市開始遊戲（人類自聖潔王都、精靈自精靈村落
等，其他城市屬稍後才準備的遊戲資料）。若新手教學必須在每一座起始城市各做
一份，成本不可接受。因此決策為：**徹底移除 onboarding 子系統**。新手教學
的語意縮減為「虛境內的操作教學」——玩家在虛境閱讀作者預備的石板／石碑／
筆記本等可閱讀物（屬未來遊戲資料工作，不在本設計範圍），完成操作認識後
離開虛境；離開虛境即進入正式遊戲，不再有系統性的教學狀態。

同時定義虛境的通道語意：**虛境是單向通道**。玩家從虛境經閘門前往城市，
無法回頭；目前只有聖潔王都一城，但機制必須預留未來多城市閘門的彈性。
南門守衛失去教學職責後連同子系統一併刪除（未來重設計遊戲資料時，它以
一般泛用 NPC 的身分、帶著作者供給的姓名＋稱號再回來）。

本設計同時了結 NPC 稱號系列遺留的 D7a 豁免：南門守衛是世界上的最後一個
無作者身分生產 NPC，它的死亡讓「每一隻生產 NPC 都帶姓名＋稱號」不變式
自動閉環。

## 2. 決策摘要

| 決策 | 選擇 | 理由 |
|---|---|---|
| onboarding 子系統 | 整體刪除（髒切、零遷移） | 未發布、零使用者；AGENTS.md 禁止相容層。子系統是死抽象，不留 feature flag |
| 角色出生點 | 留在虛境（刪掉 relocate 呼叫即可） | Evennia 首建角色預設出生點本來就是虛境；「不搬家」就是新流程 |
| 虛境單向性 | 只建去程 Exit，冪等清除回程殘留；雙重保證＝虛境房間 `at_pre_object_receive` 硬閘 | Evennia 的 Exit 是獨立 DB 物件，沒有自動反向；單向＝不建反向即可。房間硬閘已存在（拒絕任何 character 進入虛境），讓單向性不依賴出口缺席 |
| 多城市彈性 | `world/maps/city_gates.py` 凍結 registry 驅動閘門同步 | 與 `WILDERNESS_ENTRY_REGISTRY` 同構但獨立；加城市＝加一列；Evennia 原生 Exit 承擔全部語意，零新框架 |
| 南門→荒野閘門 | 不做，留給遊戲資料重設計 | 屬會被重設計取代的測試資料；南門移除回程後仍可通城市內部，不會關死玩家 |
| 石板／石碑教學內容 | 不做，留給遊戲資料重設計 | 純遊戲資料工作，與本次移除正交 |
| `introductory_hunt` 任務 | 保留為普通公會任務，只拆「完成→`set_onboarded`＋歡迎訊息」鉤子 | 任務資料本身正常；教學語意只存在於鉤子 |
| 「南門新客」異名 | 保留；取得時機從公會註冊改掛為「回報第一個公會任務」，flavor 改成不依附守衛目送的敘述 | 舊掛點（公會註冊）是教學語意的殘留；新語意＝「完成第一次回報的新面孔」。授予仍走稱號系統正規寫者 `bank_epithet` |
| HelpOverlay | 保留元件，內容來源改前端靜態 `lib/controls-reference.js`；後端 guide 內容推送退役 | 其本質是操作教學／按鍵說明，正是新的教學語意；不砍玩家的說明入口 |
| `guild_staff` 對話 | 對話表迁入 `world/rules/dialogue.py` 唯讀 runtime | 「回報」關鍵字掛的是可回報任務清單（公會功能，非教學功能）；runtime 文件本來就宣稱擁有該例外語意 |
| 種族→城市選擇 | 不實作，只釘 registry 縫合點 | 其他城市尚不存在；出生固定虛境，YAGNI |

拒絕的替代方案：

- **出口宣告塞進 xyzgrid 城市地圖資料**：虛境不是 xyzgrid 房間，跨系統橋接
  會讓 xyzgrid 同步器背一個它不該懂的例外，改動面反而大。
- **套用荒野 `WildernessGateExit` provider 協定**：該協定為荒野動態 cell
  生成設計；城市入口只需要靜態單向 Exit，複用是過度工程。
- **保留 onboarding 骨架、關掉開關**：骨架（狀態機、腳本表、sync 步驟）
  的唯一存在理由是服務守衛教學；留骨架等於留死碼。
- **為南門守衛補 registry 作者身分**：註定刪除的 NPC 造 registry 列是死
  抽象（NPC 稱號系列 D7a 的原始判斷，本次由刪除兌現）。

## 3. 刪除範圍（髒切清單）

整體刪除（不留別名、不留 deprecated 路徑）：

- `world/rules/onboarding.py`（`GUARD_NPC_KEY`／`GUARD_NPC_TAG`／
  `sync_guard_npc`／`relocate_to_starting_location`／`maybe_play_arrival`／
  `observe_room_entry`／`run_scripted_talk`／`set_onboarded`／狀態機）。
- `world/onboarding/` 整個套件（`guide.py`、`guide_dialogue.py`、
  `scenes.py`、`tests/test_onboarding_data.py`）。守衛 NPC 由 sync 建立，
  sync 步驟移除後不再重生；開發資料庫中的既有殘留依重置處理，不寫清理
  shim（唯一例外見 §4 的回程出口清除，那是同步器的職責而非遷移）。
- `typeclasses/characters.py` 四個 AttributeProperty：`onboarded`、
  `guide_progress`、`onboarding_beat`、`first_arrival_seen`。
- startup：`server/conf/at_server_startstop.py` 的 `sync_guard_npc` 步驟與
  `STARTUP_STEP_ORDER` 條目。
- 呼叫點修剪：
  - `commands/character_creation.py`：建立後 relocate＋arrival 刪除。
  - `typeclasses/accounts.py`：`maybe_play_arrival`。
  - `typeclasses/characters.py`：`advance_beat`。
  - `typeclasses/exits.py`：`observe_room_entry`。
  - `world/rules/guild.py`：結尾鉤子（任務保留）。
  - `world/rules/movement_settlement.py`：`first_arrival_seen` 快照欄位。
  - `commands/talk.py`：guide-prompt 分支與 `run_scripted_talk` 導入，改走
    `world/rules/dialogue.py` 唯讀解析（見 §5）。
  - `web/webclient/actions/exploration_actions.py`、
    `creation_actions.py`、`presentation/affordances.py`：同語意修剪。
  - `web/webclient/actions/service_actions.py`：`onboarding_completed`
    歡迎訊息分支。
- 測試：`world/rules/tests/test_onboarding.py`、
  `test_onboarding_journey.py`、`world/onboarding/tests/`；
  承載 onboarding requirement 的 webclient／browser 測試連同其
  `covers_requirement` 錨點一併退役。
- `.github/evennia-shards.json`：`world.rules.tests.test_onboarding`、
  `world.rules.tests.test_onboarding_journey`、`world.onboarding` 條目，
  以及 shard 名 `quests-skills-art-ai-onboarding-lore` 的 onboarding 用字；
  `browser-shards.json` 的 onboarding beat 條目。
- 規格：主規格 `openspec/specs/onboarding-guide/spec.md` 退役；其餘主規格
  （movement、wilderness-gateway、title-system、persona-store、
  scripted-dialogue、affinity-system、localized-appearance、map-knowledge、
  displayed-stats-view、action-options-trigger-hooks、webclient 系列）內
  引用 onboarding hook 的措辭逐條修剪，走 OpenSpec change 流程 sync。
- `docs/game/commands.md` 與 `docs/game/command-reference.md`：查證無
  onboarding 條目，無需改動；`tests/test_command_docs.py` 照常保持綠燈。

保留並改造：

- `world/lore/titles.py` 的 `STARTER_EPITHET`「南門新客」：稱號保留，
  `origin_basis` flavor 改成不依附守衛目送的敘述；授予鉤子遷移見 §6。
- `introductory_hunt` 任務：留在公會任務目錄，作為普通任務。

保留原樣：

- `docs/superpowers/specs/2026-08-02-player-onboarding-design.md`（有日期的
  歷史設計，由本文件取代其現行地位）。
- `南門守衛` 作為字面 NPC 名散見於 party／titles／npc_identity／imports 等
  測試 fixtures——那是測試資料字串，與子系統無關。
- 虛境房間文案 `LIMBO_DESC`：現文案無教學指涉，維持原樣。

## 4. 虛境單向城市閘門

Evennia 事實：`Exit` 是獨立持久物件，`create_object(Exit, ...)` 只建你給的
那一條；没有任何「自動成對反向」機制（`@dig` 是建檔wizard指令的便利行為，
與程式端無關）。因此單向通道＝只建去程。第二層保證目前是**缺口而非現況**：
查證 master 的 `typeclasses/rooms.py`，`Room`（虛境房間的 typeclass）是裸
`pass` 類別，並無任何入口閘——上游 Evennia 文件中的 Limbo 範例行為不存在於
本倉庫。本設計因此要求把硬閘**補成真實作**：虛境同步（`sync_limbo()`）對
虛境房間宣告式收斂一道入口閘（Evennia 的房間入口權限語意＝目的地 "get"
lock 檢查；實作位置以安裝的 Evennia 6.1.0 源碼為準，在 `at_pre_object_receive`
與 lock 兩者中選確定性較高者），拒絕任何 character 進入虛境，拒絕文案走
zh-tw 本地化框。單向性由「去程只從虛境側建立＋虛境入口硬閘」兩層共同保證。

新增 `world/maps/city_gates.py`：

```python
@dataclass(frozen=True, slots=True)
class CityGateDef:
    """One immutable city-gate row (map id, gate-room xyz, exit key, aliases)."""
    map_id: str
    gate_xyz: tuple[int, int, str]
    exit_key: str
    exit_aliases: tuple[str, ...]

CITY_GATE_REGISTRY: MappingProxyType = MappingProxyType({
    "capital_altoria": CityGateDef(
        map_id="capital_altoria",
        gate_xyz=(2, 0, "capital_altoria"),
        exit_key="南門",
        exit_aliases=("王都", "城門"),
    ),
})
```

`world/maps/bootstrap.py` 變更：

- `sync_grid()` 對 `CITY_GATE_REGISTRY` 每一列 `_ensure_exit(虛境→閘房)`，
  冪等收斂語意不變（既有出口改寫 key／aliases）。
- 刪除 `EXIT_TO_LIMBO` 常數與其 `_ensure_exit` 呼叫。
- 新增冪等清除：每次同步刪除「位於城市側房間、destination 為虛境」方向的
  既有 Exit 物件（把舊 `離開王都`／`回虛境` 當髒資料清掉）。這是同步器對
  自己所管出口的宣告式收敛，與 `_ensure_exit` 對稱，不是向後相容 shim。
- registry 列的閘房不存在時 `log_warn`＋skip（現行 bootstrap 模式）。

未來加城市＝registry 加一列（虛境同時挂多條單向出口）。種族→出口的出生
導流不在本設計範圍（其他城市尚不存在）。

## 5. guild_staff 對話遷移

`DIALOGUE_TABLE` 兩條目：`south_gate_guard`（守衛教學，隨子系統死）與
`guild_staff`（公會職員；關鍵字「回報」解析唯讀可回報任務清單——公會功能
而非教學功能）。`world/rules/dialogue.py`（通用唯讀 dialogue runtime，存活
模組）目前 import 自 `world/onboarding/guide_dialogue`：

- `GUILD_STAFF_DIALOGUE_KEY`、`GUILD_STAFF_TURNIN_KEYWORD`、
  `GUILD_STAFF_RESPONSES` 與其 `DialogueDefinition` 整段迁入
  `world/rules/dialogue.py`（該模块 docstring 早已宣稱擁有 guild_staff 回報
  例外語意），刪除跨包 import。
- `OnboardingGuide` component 從 `resolve_dialogue_component` 移除，只留
  `ScriptedDialogue`。
- `commands/talk.py` 刪除 guide-prompt 分支；scripted talk 一律經
  `dialogue.py` 唯讀解析。webclient `exploration_actions.py` 的
  `run_scripted_talk` 呼叫改接同一 seam。

## 6. 「南門新客」異名授予鉤子遷移

現況查證：異名的授予本來就走稱號系統的正規機制——`grant_starter_pair`
（`world/rules/titles.py:657`）在公會註冊事務（`register_adventurer`，
`world/rules/guild.py:227` 呼叫）內同時發 F 階稱號（`grant_rank_title`）
與異名（`bank_epithet`，dedupe＋自動裝備＋通知行）。它**不在** onboarding
子系統裡；onboarding 掛的只有獨立的 `set_onboarded` 旗標（見 §3）。

新語意：異名是「回報第一個公會任務」的記述，不是「註冊」的記述。遷移：

- 拆散 `grant_starter_pair`：公會註冊只發 F 階稱號（`grant_rank_title`
  留在原位）；函數退役。
- 新增 `grant_first_quest_epithet(actor)`（同模組、同 `bank_epithet`
  正規寫者），由公會任務**回報（reward claim）事務**呼叫；觸發條件＝
  claim 前 `guild_reward_claims` 為空（第一次回報）。`bank_epithet` 的
  dedupe 為第二重保證（重複回報／重登不重發）。通知行併入 claim 回應
  （「獲得異名：南門新客」）。
- `STARTER_EPITHET.origin_basis` 改寫為第一次回報的新面孔敘述，去除守衛
  目送與「目送」世界觀。
- 效果：註冊後全銜只有「F級冒險者」；首次回報後補齊
  「F級冒險者　南門新客」。
- 本遷移屬 title-system 主規格的行為變動，以同一 OpenSpec change 的
  delta 呈現並 sync。

## 7. HelpOverlay 改靜態

- 前端：`HelpOverlay.vue` 內容來源改為既有 `lib/controls-reference.js`
  靜態資料；stories／fixtures／測試跟著改吃靜態輸入。
- 後端：guide 內容 OOB 推送管線退役。
- Storybook showcase 覆蓋清單（frozen required-set manifest）若引用
  onboarding 來源，在同批更新。

## 8. 錯誤處理

- 出口不存在：Evennia 原生 "You can't go that way" 路徑，不新增訊息。
- 企圖進入虛境：`at_pre_object_receive` 既有拒絕文案保留。
- sync 時閘房缺失：`log_warn`（事件 `bootstrap_grid_gate_missing`，
  context 帶 `map_id`／`xyz`／`action`）＋skip，該列跳過、其他列繼續。
- 觀測事件目錄：`sync_guard_npc` 相關 startup step 事件退役；新增事件依
  observability facade 慣例（`world.observability`、snake_case event、
  context dict）。

## 9. 驗證計畫

- Focused 測試：maps bootstrap（單向閘門＋回程清除）、
  character_creation（出生留虛境）、talk／dialogue（guild_staff 遷移後
  「回報」仍解析任務清單）、guild（無 `set_onboarded` 仍能完成
  `introductory_hunt`）、titles（註冊不發異名、首次回報發異名、重複回報
  不重發）、webclient exploration／creation、help overlay。
- 全量非瀏覽器 Evennia suite 一次（`--parallel 16 --noinput`）。
- `uv run --locked python -m tools.spec_traceability check`：0 uncovered／
  0 errors——onboarding-guide 規格退役後其 requirement 退出索引；修剪後
  仍存活的規格若失去承載測試，連同修剪後的規格文字改由存活測試承載。
- `uv run --locked python -m tools.observability_lint check`：違反數只減不增。
- `openspec validate --all --strict`。
- npm 端：`npm test`、`npm run build-storybook`、`npm run showcase-coverage`。
- 實作走 OpenSpec change（建議名 `remove-onboarding-tutorial`），依既有
  worktree→rubber-duck→merge 慣例。

## 10. 範圍邊界（明確不做）

- 南門→荒野閘門（留給遊戲資料重設計）。
- 虛境石板／石碑／筆記本教學內容（純遊戲資料工作）。
- 種族→起始城市選擇邏輯（其他城市尚不存在）。
- 玩家稱號系統（`world/rules/titles.py`）機器本體——不動
  `bank_epithet`／`bank_fixed`／dedupe／裝備槽機制；僅改
  `STARTER_EPITHET` 的 flavor 文字與授予鉤子掛點（§6）。
