# 提示詞資料庫

所有由應用程式擁有的 LLM 提示詞（旁白、NPC 對話、任務企劃、思考回饋、美術描述）都存放在儲存庫根目錄的 `prompts/` 資料夾，作為唯一來源。調整提示詞不需要改 Python 程式碼或重建映像：編輯 YAML 檔案、驗證、然後重新啟動（或 reload）伺服器即可套用。

## 檔案位置

- 儲存庫：`prompts/`（本機裸機執行）
- 容器映像：`/app/prompts`（映像內建同一個資料夾，僅映像執行也可用）
- 容器執行期：`compose.yaml` 以唯讀 bind mount 掛載 `${PROMPTS_DIR:-./prompts}:/app/prompts:ro`，主機上的編輯在重新啟動或 reload 後生效

```
prompts/
├── narrator.yaml           旁白系統提示詞
├── npc_dialogue.yaml       NPC 對話系統提示詞範本
├── scenario_director.yaml  任務企劃（ScenarioDirector）系統提示詞
├── npc.yaml                NPC 思考回饋範本
├── art.yaml                美術描述範本與風格片段
└── character_creation.yaml 創角提示詞（前瞻註冊，尚未有消費者）
```

## YAML 格式

每個檔案宣告 `schema_version: 1` 與一個 `prompts:` 對應表：

```yaml
schema_version: 1
prompts:
  narrator.system: |-
    你是《伊洛瑟恩大陸》的旁白敘述者。……
```

每個鍵只能出現在它自己檔案中；註冊表定義了鍵與檔案的對應關係。文字區塊可以是多行（使用 `|-` 避免結尾換行）或單行字串。

## 鍵與占位符

| 鍵 | 檔案 | 允許的占位符 |
| --- | --- | --- |
| `narrator.system` | `narrator.yaml` | 無 |
| `npc_dialogue.system` | `npc_dialogue.yaml` | `{name}`、`{desc}`、`{location}` |
| `scenario_director.system` | `scenario_director.yaml` | 無 |
| `npc.thinking` | `npc.yaml` | `{name}` |
| `art.style` | `art.yaml` | 無 |
| `art.character_description` | `art.yaml` | `{race}`、`{name}`、`{age}`、`{style}` |
| `art.monster_description` | `art.yaml` | `{description}`、`{display_name}`、`{examples}` |
| `character_creation.system` | `character_creation.yaml` | 無 |

只有允許清單內的 `{token}` 會被替換，替換是逐一且精確的：

- `{name}`、`{location}` 這類允許的占位符會被代入實際值。
- 兩個大括號包住的名稱（如 `{{name}}`）是字面文字，不會被替換。
- 提示詞內的 JSON 範例（如 `{"speech": "你要說的話", "intent": {"kind": "..."}}`）原樣保留，不會被當成占位符。
- 不在允許清單內的 `{token}`（例如把 `{name}` 打成 `{nmme}`）會在載入時回報錯誤，不會靜默忽略。

## 編輯流程

1. 編輯 `prompts/` 下的 YAML 檔案。
2. 執行驗證指令確認每個鍵都合法：

   ```sh
   uv run --locked python -m world.prompts.validate
   ```

   成功會印出每個鍵的 `ok` 摘要並以 0 結束；失敗會印出每個具名錯誤（檔案、鍵、問題）並以 1 結束。
3. 重新啟動伺服器（或執行 reload，`evennia reload` 也會重新執行 `at_server_start`）。提示詞只在載入時讀取一次，編輯不會即時生效，也不會在執行中重新讀取。

## 故障隔離

一個壞掉的提示詞檔案只會影響它自己的層：載入時該鍵會被標記為不可用，並記錄具名錯誤（檔案、鍵、問題），伺服器照常啟動。消費該鍵的生成層會回到既有的確定性降級路徑：

- 旁白 → 模板渲染器
- NPC 對話 → 問候或沉默
- 任務企劃 → 任務模板池
- 思考回饋 → 不顯示
- 美術描述 → 以登錄表資料為底的確定性描述

前向註冊的 `character_creation.system` 失敗只會記錄警告，永遠不會阻擋啟動。修復檔案後重新驗證並重新啟動即可復原。

## 容器注意事項

- 掛載是唯讀的：伺服器不會寫入提示詞；管理員在主機上編輯。
- 同一個資料夾在容器內是世界可讀的，外部美術 worker（設計 D11 的可抽換指令）也可以讀取隨附的提示詞片段；worker 契約不變。
- 掛載會覆蓋映像內建的預設檔案，兩邊內容相同，沒有分歧風險。

## 本機預覽文件

```sh
uv run --locked python -m http.server --directory docs 3000
```

瀏覽 `http://localhost:3000` 預覽 docsify 文件站。
