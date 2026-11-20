# Spec Delta

## Purpose

三座精靈村內的常駐「居民」NPC：只對話聊天、不承載任何交易或接待服務，具完整人物設定、自己的家、以及往來家中與村內公共空間的作息。

## ADDED Requirements

### Requirement: Resident construction is persistent and chat-capable
居民同步 SHALL 依作者登錄的居民身分，以 find-or-create 建立一具持續存在的 `LLMNPC`，並寫入完整的七欄人物卡、canonical 年齡與字面基礎數值；居民 SHALL NOT 掛載任何受管服務能力（merchant、guild_staff、guild_exam_reception、quest_issuer、church_host）。

#### Scenario: First sync creates a complete resident
- **WHEN** 伺服器同步居民登錄表，且某居民的 canonical 身分尚未存在
- **THEN** 建立一具 `LLMNPC`，其人物卡七欄齊全、`age`／`apparent_age` 為設定檔作者值、數值為登錄表字面值、性別為其種族允許的性別，且不具任何受管服務元件

#### Scenario: Re-sync reuses the existing resident
- **WHEN** 伺服器再次同步同一份居民登錄表
- **THEN** 不建立第二具同名居民，既有居民的身分、位置與玩家編輯過的人物卡均被保留

### Requirement: Residents live in their home and move on a schedule
每位居民 SHALL 在建立時被放進作者指定的家（內室 room），並 SHALL 依登錄表指派的作息，經既有排程結算路徑在家與村內公共空間之間移動。

#### Scenario: New resident starts at home
- **WHEN** 一名居民於同步中被建立
- **THEN** 其身處的房間是其登錄表指定的家

#### Scenario: Schedule relocates a resident to a public room and back
- **WHEN** 世界時鐘推進到該居民作息中「前往公共空間」與「返回」的時刻
- **THEN** 居民經真實 Exit 移動到目標公共空間，並在返回時刻回到其家

### Requirement: Residents converse without hosting a service
居民 SHALL 以既有生成式對話（`LLMNPC`）與條件式劇本話題回應玩家，且 SHALL NOT 提供任何店主／公會／教會／委託服務入口。

#### Scenario: Conditional scripted topic qualifies by state
- **WHEN** 玩家改變了使某條件式話題成立的狀態後再與該居民交談
- **THEN** 該話題依其 `requires`／`variants` 之既定規則出現或解鎖，未達條件時不洩漏標籤或內文

#### Scenario: No service component is exposed
- **WHEN** 玩家對一名居民使用的交互介面
- **THEN** 不出現任何交易、公會、教會或委託服務項目

### Requirement: Residents participate in source-inventory and roster integrity
居民 SHALL 被列於出貨來源名冊，並納入啟動名冊門禁：孤立的人物卡／對話表／設定檔、重複的 canonical 居民身分，SHALL 在寫入前整批具名拒絕。

#### Scenario: Duplicate canonical identity rejects before any write
- **WHEN** 居民登錄表或既有 NPC 以相同 canonical 身分重複聲明同一居民
- **THEN** 同步整批拒收並點名該身分，不建立或改寫任何居民

#### Scenario: Missing referenced dialogue table fails startup validation
- **WHEN** 一份居民對話鍵沒有對應的登錄對話表，或居民設定檔被登錄表引用卻未註冊
- **THEN** 啟動名冊門禁列出具名缺失並中止啟動