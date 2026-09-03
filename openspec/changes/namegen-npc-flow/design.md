# namegen-npc-flow — Design

## Context

設計源頭 `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §6。前置鏈：`npc-namegen-lore-registry` 已在 `world/lore/names.py` import 時凍結 `NAME_PACK_REGISTRY`／`NAME_PACK_BY_RACE`；`npc-namegen-rules-roller` 交付 `world/rules/namegen.py` 的純函式 `roll_name_for_race(race_key, sex, rng)`（規則層 D1：rng 一律由呼叫端注入、本層絕不構造 `Random`；未知包 `KeyError`、空池退回、產生器絕不死掉）。本 change 接兩個消費端：

1. **Prompt 階段**：現況 `world/ai/scenario_director.py::build_scenario_prompt(context)` 回 `(system, user)`；system 為 `render_prompt("scenario_director.system")`（零佔位符），user 為 `_bounded_context(context)`（固定五鍵、stable sorted JSON、`MAX_CONTEXT_FIELD_LENGTH=200`／`MAX_TOTAL_SIZE=12000`）。既有契約：同輸入必得位元組相同 prompt。輸出 schema（`SCENARIO_DIRECTOR_OUTPUT_SCHEMA`）與 16 個語意驗證器（`_VALIDATORS`）為守欄資產。
2. **Spawn 階段**：`world/quests/scene_builder.py` 的 `_materialize_instance` → `_spawn_occupants` → `_spawn_npc` → `_apply_characterization(npc, requirement, position)`。`_spawn_npc` 先以 `NPC_TIER_REGISTRY[tier_key].race_key` 設 `npc.race`（原型落地順序保證 race 先於 characterization）；`_apply_characterization` 在 `characterization.display_name is not None` 時寫 `npc.db.display_name`，且 characterization 為 `None`（generic 佔用者）或 `position` 越界時直接 early-return——現況下 generic 佔用者完全無名。`LivingEntity.sex` 為 `AttributeProperty(default=DEFAULT_SEX)`（`"other"`）、`race` 預設 `None`。

離線模板池 `world/ai/director_templates.py` 第一條帶 `display_name="黑鬍"`，該 authored 名走既有 characterization 應用路徑。

## Goals / Non-Goals

**Goals:**
- LLM 生成藍圖時看到確定性「僅供靈感」建議名與「建議填寫 `display_name`」指引，語料風格錨定與敘事自由共存。
- 任何場景 NPC（含 generic role-based 佔用者）落地後必然有名：無 authored 名時以 `Random(crc32(f"{definition.key}:{stage_index}:{role}"))` 確定性補名，同藍圖重放必得同名。
- 補名處發 `world.observability` facade info 事件（context 帶 quest／stage／role）。
- schema 必填性、validator、`_bounded_context` 鍵集、「黑鬍」模板路徑全部不動。

**Non-Goals:**
- prompt 注入多候選名綁 archetype／依 stage 需求逐槽位擲名（設計 §10 範圍外；本 design D1 的靈感名庫是折衷形態，見風險）。
- 玩家替 NPC 提名、staff 收藏匣命令、`meaning_zh` 展示。
- 改 `world/lore/names.py`、`world/rules/namegen.py`、`world/ai/director_templates.py`。

## Decisions

### D1：prompt 側以「脈絡種子靈感名庫」實現靈感注入；逐槽位原式種子留給 spawn 側

設計 §6.1 寫的 prompt 側種子 `crc32(f"{definition_key}:{stage}:{role}")` 在請求時點**不可計算**：`build_scenario_prompt(context)` 的輸入只有請求脈絡（requested_type／allowed_rank／issuer_branch／anchor／note），該時點 LLM 尚未輸出、blueprint 不存在，`definition_key` 更是 `compile_quest_blueprint` 之後才存在的內容摘要（sha256 over canonical fields）。可選解法：

- **two-pass（拒絕）**：先叫 LLM 產結構、再逐槽位擲名回填、再叫 LLM 補敘事——雙倍 transport 成本、改動 guardrail 管線形態，且違反「schema／validator 不動」。
- **改需求為 spawn-only（拒絕）**：丟掉 prompt 階段的風格錨定，設計 §2 已核定「方案 A＋靈感化 B」雙管。
- **脈絡種子靈感名庫（採用）**：對 `_bounded_context(context)` 的序列化文字算 `zlib.crc32` 作種子，`roll_name_for_race(None, "", Random(seed))` 擲固定 N 個（N=6）名字，組成一段文字注入 system 訊息。性質：同 context 必得同名庫（守住「同輸入位元組相同 prompt」契約——`_bounded_context` 本身確定，注入源也確定）；不同 context 自然換名庫。靈感定位（僅供靈感、可依性別／背景改寫、建議填寫 `display_name`）由 YAML 文字承載，LLM 有權改寫——用戶核定決策。

spawn 側仍用設計原式 `crc32(f"{definition.key}:{stage_index}:{role}")`：該時點三要素俱在，同藍圖重建必得同名的重放契約完整保留。兩側種子不同源是**刻意**的：prompt 名只是靈感（LLM 常會改寫），spawn 名是最終落地名（必須逐槽位穩定）。

### D2：注入走 prompt 庫佔位符；`PromptUnavailableError` 語意不變

`world/prompts/registry.py` 的 `scenario_director.system` 由零佔位符改為 allowlist `("name_inspiration",)`，`prompts/scenario_director.yaml` 文字承載命名指引與 `{name_inspiration}` token；`build_scenario_prompt` 改呼叫 `render_prompt("scenario_director.system", name_inspiration=庫文字)`。理由：prompt 庫是「所有 LLM prompt 文字的唯一真相」（prompt-library spec 第一條），命名指引句不得寫成 Python 常數；佔位符渲染由 loader 驗證 allowlist，打錯 token 在載入期就炸。既有 `try: build_scenario_prompt except PromptUnavailableError: _draw_template` 的降級路徑不動；擲名在 `roll_name_for_race` 契約下絕不死（空池退回），不會引入新的降級 trigger。名字庫固定 6 個、總長 < 200 字元，注入後 system 文字仍遠低於渲染界。

### D3：兜底補名錨點在 `_spawn_npc` 落地尾端，以 `npc.db.display_name is None` 觸發

characterization 為 `None` 時 `_apply_characterization` 現行 early-return，補名若塞進該函式內部第一分支會被 early-return 吃掉、或逼出雙寫點。決定：`_spawn_npc` 在 `_apply_characterization(npc, requirement, position)` 之後檢查 `npc.db.display_name is None`，成立時呼叫 `roll_name_for_race(npc.race or None, npc.sex or None, Random(zlib.crc32(f"{definition_key}:{stage_index}:{role}".encode())))` 寫 `npc.db.display_name` 並發事件。如此：

- authored 名（LLM 或「黑鬍」模板）已由 `_apply_characterization` 寫入 → 非 `None` → 永不覆寫；
- generic 佔用者／characterization 越界者 → `None` → 補名；
- `race_key`／`sex` 從原型（`npc.race`／`npc.sex` AttributeProperty 現值）取，取不到或空字串傳 `None`：`race=None` 走規則層隨機包兜底（D4 of rules：sorted 候選、dwarf／halfling 不參與），`sex=None` 走隨機池；`npc.sex` 現預設 `DEFAULT_SEX="other"` → u 池優先，與表單側同語意。

種子座標 `definition_key`／`stage_index` 由 `_materialize_instance` 沿 `_spawn_occupants`→`_spawn_npc` 顯式傳參（參數尾端加 `definition_key: str, stage_index: int`），不在深層用 `requirement` 反推（`StageSpawnRequirement` 不帶 definition key）。`_spawn_monster` 不受影響（魔物不走 namegen）。

### D4：觀察性事件 `npc_name_fallback`，facade named import

`scene_builder.py` 已有 `from world.observability import log_warn`；改為同列 `log_info, log_warn`。補名成功後以 `transaction.on_commit(lambda: log_info("npc_name_fallback", context={...}))` 排程事件，context 五鍵 `{"quest": quest_id, "definition_key": definition_key, "stage": stage_index, "role": role, "name": name}`（snake_case event id、context dict、依 facade 規範的 `action_commit` 級 info 事件）。採 commit 後排程（rubber-duck M1）：與 `world/rules/clock.py::WorldClock.advance` 的 `clock_advance` 同一慣例——boundary info 只在最外層提交後落地，回滾的 materialization 不留下宣稱不存在 NPC 的假陽性 trace。測試以 `captureOnCommitCallbacks(execute=True)` 斷言提交路徑恰一條事件、回滾路徑零事件。

### D5：schema、validator、脈絡鍵零變動

`SCENARIO_DIRECTOR_OUTPUT_SCHEMA` 的 `display_name` 維持 `{"type": ["string", "null"]}` 選填；`_VALIDATORS` 十六條不動；`_CONTEXT_KEYS`／`_CONTEXT_DROP_ORDER` 不動（靈感庫不進 user 脈絡、不佔 `MAX_TOTAL_SIZE`，只進 system 訊息）。指引文字明文「建議填寫 display_name、風格可參考建議名、依敘事需要調整」，不新增任何驗證規則——LLM 回超長／非法字元走既有 `MAX_NAME_LENGTH`／validator 路徑（設計 §8）。

### D6：`world.rules.namegen` 入 `READ_ONLY_RULE_MODULES` 放行；單寫者邊界論證

`tests/test_ai_transport_contract.py` 的 `test_no_ai_module_imports_a_state_writer` 以 `STATE_WRITER_MODULES`（含 `world.rules`）掃描 `world/ai/` 的 import。本 change 讓 `scenario_director.py` import `world.rules.namegen`——必須與 `world.quests.characterization` 同列放行於 `READ_ONLY_RULE_MODULES`。論證：單寫者邊界的實質是「`world/ai/` 永不**落地**狀態」；`namegen.py` 是無 DB、無 Evennia import、不寫狀態的純函式（rules-roller D1／D5 明文），prompt 組合器讀它與讀 `world.lore` 諸 registry 同性質，且已有 `world.quests.characterization` 同型先例。反方向（deterministic-path ban 掃 `world/rules/` 等是否 import `world.ai`）不受影響——放行表只在 AI→state-writer 一個方向生效。放行寫在測試常數並附註釋，註明「純讀取、無狀態寫入的規則模組」。

### D7：測試全落既有 test module，shards manifest 零改動

實查 `.github/evennia-shards.json`：shard 4（`quests-skills-art-ai-onboarding-lore`）labels 含 package label `world.quests` 與 `world.ai`，shard 5 含 `world.prompts`——package label 遞迴涵蓋（`tests/test_evennia_test_optimization_contract.py::_resolve_evennia_label` 走 `rglob("test*.py")`）。本 change 的測試全部擴充既有 module（`world/quests/tests/test_scene_builder.py` 系列、`world/ai/tests/test_scenario_director_prompts.py`、`world/prompts/tests/test_loader.py` 等），不新增 test module，owns-every-module 契約測試天然通過。若實作者新開 top-level `test_*.py`，必須落在被 label 遞迴涵蓋的 package 內或顯式入 manifest。

## Risks / Trade-offs

- [靈感名庫與 spawn 兜底名不同源，prompt inject 的「逐槽位對位」語意弱化為「風格樣本池」] → 設計 §6.1 的原式在請求時點不可計算（D1），這是可達成的最貼近實現；槽位級最終名仍由 spawn 原式種子保證重放。未來若要多候選綁 archetype（§10 範圍外項），本 D1 的 bank 形態可直接擴充而不改種子策略。
- [脈絡種子對 `_bounded_context` 文字雜湊，note 一字之差即換名庫] → 可接受：靈感庫非承諾名字，只需確定性；同 context 重放同庫由 spec scenario 釘死。
- [`READ_ONLY_RULE_MODULES` 放行被未來瀨用（放行表變胖）] → 放行清單逐條附註釋與來源 change 名；新增條目本身就是評審點。
- [事件改 `transaction.on_commit` 排程後回滾零殘留 trace] → 副作用是測試必須用 `captureOnCommitCallbacks(execute=True)` 或置於已提交外層，沿用 portrait pipeline 測既有形態。
- [`npc.sex` 預設 `"other"` 使 generic 佔用者偏向 u 池] → 與規則層 sex 語意一致（other→u 池優先），u 池為中性名池，正是要的行為。

## Open Questions

（無。種子來源、注入機制、補名錨點、事件形態、放行與 shard 落點均已核定。）
