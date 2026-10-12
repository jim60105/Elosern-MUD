# 魔物戰鬥 AI 調校與決策模式

本文件記錄 `monster-ai-variant-tuning` 已實作的授權與執行期契約，涵蓋魔物戰鬥 AI 的調校來源、智慧（intelligence）與決策模式的解析方式，以及工作階段層級的記錄壽命。攻擊選擇器本身由後續的 `monster-ai-attack-selection` 交付，因此目前的正式內容全部停留在 `legacy` 模式。

## 調校來源

唯一的 AI 調校來源是 `world/rules/rulebook/monster_behaviour.yaml`，由 `world/rules/monster_behaviour.py` 於啟動時載入並驗證。頂層欄位固定為下列五項，缺一或出現未知欄位都會讓啟動失敗。

- `tier_default_archetype`：每個 `MonsterTier` 登錄鍵恰好一筆，值必須是 `archetypes` 中的鍵。
- `archetypes`：每個原型必須宣告四個既有欄位 `target_strategy`、`skill_choice`、`prefer_area_when_multiple_enemies`、`flee_hp_fraction`，並可選填 `decision_mode` 與 `utility_weights`。
- `candidate_budget`：整數 1 至 4096，為單次決策可檢視的提案上限。
- `variant_intelligence`：變體鍵到智慧值的對應。
- `variant_decision_mode`：變體鍵到決策模式的對應。

驗證相當嚴格。未知欄位、無法辨識的模式、以布林冒充數字、權重缺漏或名稱不符、負數或非有限權重、超出範圍的整數、非對應的容器型別，以及非註冊變體或物種關係不成立的鍵，全都以 `MonsterBehaviourConfigError` 拒絕。`utility_weights` 一旦出現就必須完整宣告 `damage`、`kill`、`heal`、`control`、`focus`、`cost`、`waste`、`preference` 八個名稱。

## 智慧

智慧是**每一個已註冊變體各自明示**的整數，範圍 0 至 100。物種、威脅階級、危險等級、普通或強化分類、戰鬥數值與行為原型都不提供智慧，也不構成任何範圍或排序限制；同一物種的兩個變體可以有不同智慧，數值較強的變體也可以是較不聰明的一個。

`legacy` 變體不需要智慧值就能繼續運作；一旦某個變體的有效模式是 `utility`，啟動驗證就要求它必須有已驗證的智慧值。所有已供給的智慧值都會被驗證，即使該變體目前仍停在 `legacy`。智慧只改變決策評估，不會改動基礎數值、資源、已擁有的技能、熟練度或戰鬥公式。

## 決策模式與執行期解析

有效模式依序取用變體的 `variant_decision_mode` 覆寫、實際解析出的行為原型的 `decision_mode`，原型未宣告模式時即為 `legacy`。解析一律讀取實體**實際儲存**的 `behaviour_tree` 與已驗證的物種／變體配對，因此修復工具改動過的綁定會立即生效，而單獨一個變體字串永遠不足以決定模式。

無法產生可用決策時會得到帶型別的無效狀態，由呼叫端診斷，原因如下。

| 原因 | 意義 |
| --- | --- |
| `invalid_binding` | 實際儲存的綁定不指向本行程已知的原型，因而無法確立任何模式 |
| `invalid_identity` | 要求 `utility`，但沒有可解析的註冊物種／變體配對 |
| `missing_intelligence` | 要求 `utility`，配對可解析，但該變體沒有已授權的智慧值 |

沒有 `threat_tier` 的實體不是魔物決策目標，交由既有的委派政策處理。

## 工作階段壽命與指紋

啟動設定在行程啟動時驗證一次，**沒有熱重載**，行程中的決策一律使用啟動當下載入的調校，磁碟上的編輯要等到重新啟動才會生效。每個工作階段會以工作階段識別碼與穩定的行動者識別碼，在行程內記錄該魔物的解析結果，並附上設定指紋。這份記錄本身不可變，也不寫入任何持久狀態，沒有 AI 相關的 ORM 欄位、沒有 `Monster` 屬性，也沒有複製到實體上的智慧屬性。

重新啟動會依建構方式清空整個記錄，既有工作階段則以新行程驗證過的啟動調校重建。指紋涵蓋決策演算法版本、候選預算、階級預設對應、每個原型的模式與權重與行為葉節點、變體智慧、變體模式覆寫，以及被調校對應引用的變體綁定；顯示名稱與物件位址都不參與。

## 目前狀態

正式內容目前全部為 `legacy`，`variant_intelligence` 與 `variant_decision_mode` 皆為空對應，因此 `monster_behaviour_policy` 產生的行動與本變更之前完全相同。要啟用 `utility`，仍需要後續變更交付的選擇器。

變更紀錄：建立嚴格的變體智慧與決策模式授權、執行期帶型別解析，以及含指紋的工作階段調校記錄；所有正式變體維持在 `legacy`，舊行動決策不變，玩家指令與瀏覽器動作都沒有變更。
