# bump-creation-panel-proposal-v3 — Design

## Context

提案送達線路（retool-concept-transient-fill D1）：`_creation_concept_adapter` → `_store_proposal` 寫 `session.ndb.concept_proposal`（plain-data dict，含 `owner_actor_id` + 單調 `revision`）→ `build_presentation_context`（全發布路徑唯一的 context 工廠）深拷貝為 `ProposalSnapshot` → creation presenter 渲染 optional 頂層 `proposal` 鍵（panel v2）。五個新欄位在 `extend-concept-proposal-fields` 落地後已存在於 `CharacterProposal`；本變更把槽、快照、presenter、JS 鏡像逐段接上，讓值到得了 wire。

約束：panel payload 走 exact-field 驗證與 65536 canonical-JSON envelope 上限；槽為 plain data、永不持 live object；缺席鍵必須以「鍵不存在」表達（repo 慣例——null 與缺席語義不同：缺席＝消費端維持本地預設）；`protocol.js` 鏡像驗證器與 Python 驗證器逐鍵對稱（parity 測試強制）。

## Goals / Non-Goals

**Goals:**

- session 槽、`ProposalSnapshot`、panel `proposal` 槽、兩個 JS 鏡像同步承載五個 optional 鍵：`display_name`、`age`、`apparent_age`、`background`、`affinity_elements`。
- `CREATION_SCHEMA_VERSION` 2 → 3；鏡像常量同步；worst-case envelope 重鎖。

**Non-Goals:**

- Vue 表單消費新鍵（owned by `retool-concept-fill-navigation`）；Telnet 預設值（owned by `prefill-telnet-concept-from-proposal`）。
- draft／`creation.custom` payload 的任何變動（表單送出契約不動）。
- 前端 loading 態／導航（owned by `retool-concept-fill-navigation`）。

## Decisions

### D1: 缺席＝鍵不存在，null 非法

槽 dict、snapshot、wire 物件三層一致：正規化後缺席（`None`）的欄位不寫鍵。驗證器把五鍵列為 optional；存在時精確校驗：`display_name` 1..64 code points、`age`/`apparent_age` 整數 18..10000（提案已被生成層夾取，驗證器只收成年區間——雙層防線，越界值屬 bug 級結構拒絕）、`background` 1..600、`affinity_elements` 為 ≤8 個已註冊元素鍵的無重複清單（種族上限由生成層把關；驗證器只收結構上界 8）。

- 替代方案（缺席送 null）：被否——與 persona 塊的「null＝明確清空」語義混淆；暫態填入的缺席是「LLM 沒給」，不是「清空玩家輸入」。

### D2: schema v3 是硬切

鏡像驗證器拒絕 v2 payload（`unsupported creation schema_version` 路徑既有）；無相容層（未發布）。`creation_menu.js`（legacy 面板驗證鏡像）同步 v3 常量與 proposal 槽鍵集合，但其 form state 不讀新鍵——新鍵的第一個消費者是 `CreationOverlay.vue`（下一變更）。`CreationOverlay.applyProposal` 只讀既有鍵，v3 加鍵對現行 Vue 為純鍵增加、不破壞。

### D3: worst-case envelope 重鎖

persona 3×600 + background 600 + name 64 + 兩 int + 8 元素鍵（含鍵名與 JSON 開銷）約 6.8 KB，對 65536 餘裕充足；以既有 worst-case 測試模式擴案鎖定，防止未來欄位膨脹無聲越界。
