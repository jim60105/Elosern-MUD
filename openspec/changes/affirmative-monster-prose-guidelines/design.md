# Design

## Context

`docs/lore/monster-creation-guidelines.md` (156 lines at `1b1be7b8`) is Traditional Chinese with English technical subsections ("Test authoring boundaries", "Documenting a species"). Line 5 records the 2026-10-05 approval and says high-tier and calamity species are outside the first batch. Section 「魔物資源技能與套組配置（2026-10-09 起陸續生效）」 enumerates three species with kits and item 2 says the remaining six variants declare none; the registry now declares a kit for all twelve shipped variants.

## Goals / Non-Goals

**Goals:** add the affirmative rule, the new approval scope, and roster-free kit wording.

**Non-Goals:** rewriting any species prose, the bestiary or the ledger; adding any test, lint or prose check; editing the earlier approval history.

## Decisions

### D1. Approval paragraph (after line 5)

Keep line 5 verbatim as the historical first-batch record. Add a new paragraph directly after it:

> **第三批核准（2026-11-03）：**[魔物內容擴充設計](/superpowers/specs/2026-11-03-monster-content-expansion-design) 另行核准三種低階物種（泥膜史萊姆、膠掌小鬼、蠟囊鼠）、吞潮鱷的高階強化變體蓄潮型，以及高階物種焙鬃野豬。每個物種只出現在明確宣告的棲地、據點或遭遇中；災厄級物種與新的文明種族仍不在核准範圍內。

### D2. New section 「8．公開敘述以肯定句描寫」 after section 7

Content (Traditional Chinese, full-width punctuation):

- 公開敘述（物種描述、外觀、生態、變體方向、委託背景）直接寫出可觀察的身體特徵、行為、能力作用範圍、所需材料與代價，讓讀者從牠做了什麼認識牠。
- 技術上的排除條件與實作限制寫在作者私有欄位、設計文件或開發文件，不寫進公開敘述；公開敘述不列出牠不具備的能力，也不與其他能力比較。
- 公開敘述描寫身體與行為，不引用指令名稱、介面元素、增益識別碼或資源欄位名稱。
- 既有物種的現行段落在改寫時套用本原則；未改寫的段落維持原樣。
- 肯定句是編輯審查的判斷，記錄在 [魔物圖鑑編輯審查紀錄](/development/bestiary-editorial-review)，不由測試或字串比對判定。

### D3. Kit section rewrite

Replace the paragraph's sentence 「吞潮鱷、穗鳴雀、潮燈蟹各有兩個變體實作專屬資源技能套組；」 with 「每個變體是否具備專屬資源技能套組，完全由該變體列自己的宣告決定；」 and keep the rest of that paragraph. In item 1 replace the three named examples with 「每個主動技能皆於固有普通攻擊（`basic_attack`）與逃跑（`flee`）之前選用」 while keeping the ownership sentence. Replace item 2 with: 「**未宣告套組的變體**：未宣告技能或行為設定檔的變體只使用純物理普通攻擊，資源池不得從敘述推導，也不建立造假技能或捏造前置。」 Item 3 stays.

### D4. "Documenting a species" addition

Append one English sentence to the first paragraph: "Public prose describes bodies and observed behaviour in affirmative sentences; it never names command keys, UI elements, buff identifiers or resource-field names, and its exclusions belong in author-private fields."

## Risks / Trade-offs

- [Guide wording drifts from the approved design] → D1 links the design document instead of copying its tables or values.

## Verification

Docs-only. Check that the Docsify links resolve by path (`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md`, `docs/development/bestiary-editorial-review.md` exist) and that `openspec validate affirmative-monster-prose-guidelines --strict` passes. Run `uv run --locked python -m tools.contract_gate` to confirm no docs contract regresses.
