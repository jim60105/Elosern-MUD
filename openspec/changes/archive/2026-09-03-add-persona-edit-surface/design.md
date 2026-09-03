# add-persona-edit-surface — Design

## Context

`world/rules/persona_edit.py` 現行只提供 `update_background(character, text)`：單鍵白名單的確定性寫入服務，是 `creation-persona-persistence`「後台可自由更新 background」要求的實作。`web/webclient/presentation/character.py` 的 character panel 以恰 `{background}` 渲染 persona 區塊（code 常數已是 `CHARACTER_SCHEMA_VERSION = 6`，主規格文字仍寫 version-5——本變更把自己的 delta 對齊 code 現值並以 v7 落版，v5/v6 落差屬 title-system 變更未同步的既有文書債，不在本變更範圍）。Telnet 側 `commands/background.py` 的 `CmdBackground`（`設定背景`／`背景`）三段式：無參顯示現值與用法、有參設定、空白清除。

建立期（change A）已把 persona 三欄交給玩家在建立表單編輯；啟動後角色面板只露 background，人格／生平／習慣無處可見。本變更依設計 §5 統一為四鍵可編輯面。

約束：四鍵（含 `background`）共用 `MAX_PERSONA_FIELD_LENGTH` 600 上限與 import-card record 形狀；unknown keys must survive；`world/ai/` 永不寫入；action adapter 三參 ABI；無相容層義務。

## Goals / Non-Goals

**Goals:**

- 單一確定性寫入服務覆蓋四鍵敘事文字，既有呼叫者零改動。
- WebClient action 與 Telnet 命令對稱共用該服務。
- character panel 四段顯示；空值 null 化。

**Non-Goals:**

- `identity / appearance / social_connection` 的編輯或顯示（§10 排除；C 只做注入）。
- 建立期表單（A 的範圍）。
- 結構化欄位（三鍵巢狀形狀）的單文字欄編輯模型。

## Decisions

### D1: `update_persona_field` 為唯一寫入者，`update_background` 降為薄包裝

簽名 `update_persona_field(character, field, text)`；白名單常數 `PERSONA_EDITABLE_FIELDS = frozenset({"background","personality","life_story","habit"})`。驗證順序：欄位屬白名單 → trim → 空值→移除鍵（no-op success）→ 非空超 600 拒 `PersonaEditError` → 無 record 時以 import-card 六鍵建 record → 僅動該鍵。`update_background(character, text)` 實作為 `update_persona_field(character, "background", text)`，docstring 標注薄包裝。模組單寫者宣言改述為四鍵白名單。

- 替代方案（四個獨立函式）：複製驗證邏輯四份、白名單漂移。否。

### D2: `character.persona.update` payload 恰 `{field, text}`

`field` 恰屬四鍵白名單；`text` 為 string（trim 後 1..600）或 null（＝清除）。adapter 走標準所有權解析（本人 puppet、非 creation-pending），直呼 `update_persona_field`，成功回 confirmed success（code `persona_updated`）＋繁中訊息＋affected `character` panel；非白名單欄位或超界走穩定拒絕碼。registry 恰鍵清單＋1，`ActionRegistry` 測試同步。

- 替代方案（每鍵一個 action id）：四個 validator 漂移、registry 膨脹。恰 `{field,text}` 讓白名單只活在伺服端常數與 validator 兩處。

### D3: persona 區塊四鍵、逐鍵可 null

`persona` 從恰 `{background}` 擴為恰 `{background, personality, life_story, habit}`；presenter 沿用既有清洗（非字串→None、純空白→None、超界 fail-closed）。schema v7（自 code 現值 6 +1），presenter／`protocol.js` 鏡像同步。Drawer 四段顯示，空值「未設定」佔位。編輯入口：drawer 每段附編輯鈕，提交發 `character.persona.update`。

### D4: 三新命令逐字複製 `CmdBackground` 三段式

切法：`commands/background.py` 抽出並匯出基底類別 `CmdPersonaFieldBase`（三段式：無參顯示現值＋用法、有參設定、空白清除；經 `update_persona_field`；欄位鍵為類別屬性），`CmdBackground` 改為該基底類別的 `background` 子類別別且行為、鍵、別名完全不變；新模組 `commands/persona.py` 定義 `設定個性`（`個性`）、`設定生平`（`生平`、`背景故事`）、`設定習慣`（`習慣`）三個子類別別；`commands/default_cmdsets.py` 的 `CharacterCmdSet.at_cmdset_creation` 保留既有 `self.add(CmdBackground)` 並新增三條 add。命令文件條目由 drift contract 驗證。

## Risks / Trade-offs

- [spec v5 vs code v6 落差] → 本 delta 直接鎖定 v7 並在 delta 頭注明「v6 為既有未同步版本」；archive 追溯歸 title-system 變更。
- [玩家把 600 字上限當硬界線在 UI 攔截，伺服端卻以 trim 後計] → 雙端以同一「trim 後 1..600 code points」規則鏡像，Vitest＋Node 鏡像案各鎖一條。
- [四段 drawer 區塊撐爆 drawer 滾動] → 純 CSS 摺疊展示，非協定面；Vitest 斷言四段 DOM 存在即可。
- [unknown persona keys 被編輯路徑抹除] → D1 保留其餘鍵不變為顯式 scenario，含未知鍵的 record 編輯後仍含該鍵。
