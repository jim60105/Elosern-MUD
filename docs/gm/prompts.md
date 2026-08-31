# 提示詞資料庫

所有由應用程式擁有的 LLM 提示詞（旁白、NPC 對話、任務企劃、思考回饋、美術描述）都存放在儲存庫根目錄的 `prompts/` 資料夾，作為唯一來源。調整提示詞不需要改 Python 程式碼或重建映像：編輯 YAML 檔案、驗證、然後重新啟動（或 reload）伺服器即可套用。

## 檔案位置

- 儲存庫：`prompts/`（本機裸機執行）
- 容器映像：`/app/prompts`（映像內建同一個資料夾，僅映像執行也可用）
- 容器執行期：`compose.yaml` 以唯讀 bind mount 掛載 `${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z`（`z` 為 SELinux relabel，於強制模式主機上仍可讀取），主機上的編輯在重新啟動或 reload 後生效

```
prompts/
├── narrator.yaml           旁白系統提示詞
├── npc_dialogue.yaml       NPC 對話系統提示詞範本
├── scenario_director.yaml  任務企劃（ScenarioDirector）系統提示詞
├── npc.yaml                NPC 思考回饋範本
├── art.yaml                美術描述範本、風格片段與生成提示詞（scene／portrait／negative）
├── character_creation.yaml 創角提示詞（前瞻註冊，尚未有消費者）
└── action_options.yaml     行動建議提示詞（前瞻註冊，消費者於 action-options-layer 落地）
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
| `art.scene_prompt` | `art.yaml` | `{description}` |
| `art.portrait_prompt` | `art.yaml` | `{description}` |
| `art.negative_prompt` | `art.yaml` | 無 |
| `character_creation.system` | `character_creation.yaml` | 無 |
| `action_options.system` | `action_options.yaml` | 無 |
| `action_options.user` | `action_options.yaml` | `{room_name}`、`{room_summary}`、`{npc_entries}`、`{monster_entries}`、`{objective}`、`{narrative_tail}`、`{affordances}` |

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
- 美術生成 → 記錄以具名錯誤碼（如 `sd_prompt_error`）結算為 `failed`，佔位圖不變

前向註冊的 `character_creation.system` 失敗只會記錄警告，永遠不會阻擋啟動。修復檔案後重新驗證並重新啟動即可復原。

## 美術生成提示詞（`art.scene_prompt` / `art.portrait_prompt` / `art.negative_prompt`）

引擎內的 sd-webui 客戶端（`world/art/sd_worker.py`）是美術圖像生成的唯一消費者，提示詞文字只存在於 `prompts/art.yaml`：

- `art.scene_prompt` — 場景主體的正向提示詞範本，含一個 `{description}` 占位符；代入值是該場景在登錄表中的確定性一句話描述。
- `art.portrait_prompt` — 角色／怪物肖像的正向提示詞範本，同樣含 `{description}` 占位符；代入值是確定性角色／怪物描述。
- `art.negative_prompt` — 每個請求共用的負向提示詞，純文字、無占位符。

範本文字以自然語言英文撰寫（風格、構圖、光線、鏡頭等），與其他層一樣在載入時驗證；未知的 `{token}` 是載入時錯誤。改動三個鍵中任何一個，都會改變記錄的「已渲染提示詞摘要」（rendered-prompt digest）：`done` 記錄會被標記 `hash_changed` 供管理員審核，已完成的圖片不會被悄悄取代，也不會在一般遊玩中重新生成。

### 生成設定（`ART_SD_*`）

| 設定 | 環境變數 | 預設值 | 說明 |
| --- | --- | --- | --- |
| `ART_SD_BASE_URL` | `SD_WEBUI_BASE_URL` | `http://127.0.0.1:7860` | sd-webui / Forge 的 API 根位址（compose 已傳入 `SD_WEBUI_BASE_URL`） |
| `ART_SD_TIMEOUT_SECONDS` | `ART_SD_TIMEOUT_SECONDS` | `600` | 單次 txt2img 交換的總牆鐘截止時間；租約回收以最壞批次（`ART_SCHEDULER_LIMIT` ×（此值＋本機轉碼餘量）＋ 餘量）計算 |
| `ART_SD_STEPS` / `ART_SD_CFG_SCALE` | 同名 | `30` / `7.0` | 取樣步數與 CFG（正整數／正浮點數，載入時驗證） |
| `ART_SD_SAMPLER` / `ART_SD_SCHEDULER` | 同名 | 空字串 | 空＝伺服器預設；設定後會以 `sampler_name` / `scheduler` 傳出，必須與伺服器列舉的名稱完全一致 |
| `ART_SD_CHECKPOINT` | `ART_SD_CHECKPOINT` | 空字串 | 選用：確切的模型標題（含 hash 後綴）；空＝伺服器現用模型 |
| `ART_SD_STYLES` / `ART_SD_MODULES` | 同名 | 空字串 | 逗號分隔的風格名稱／Forge 模組檔名清單；空＝請求省略該欄（`styles`／`forge_additional_modules`）；名稱逐字通過，可用 `@art options styles`／`@art options modules` 查伺服器實際名稱 |
| `ART_SD_SCENE_WIDTH/HEIGHT` | 同名 | `1344` / `768` | 場景（16:9）輸出尺寸，必須是正的 8 倍數（SDXL 友善） |
| `ART_SD_PORTRAIT_WIDTH/HEIGHT` | 同名 | `768` / `1024` | 肖像（3:4）輸出尺寸，必須是正的 8 倍數 |
| `ART_SD_CLIENT` | —（僅限程式碼） | `world.art.sd_worker.SDWebUIClient` | 客戶端類別的可抽換點（dotted path）；測試與瀏覽器測試掛鉤指向 `world.art.fake_sd_client.FakeSDWebUIClient`，永不開啟 socket。基於匯入注入風險刻意不提供環境變數 |
| `ART_SD_MAX_RESPONSE_BYTES` | 同名 | `52428800`（50 MiB） | 回應本文／base64 上限 |
| `ART_SD_MAX_IMAGE_DIMENSIONS` / `ART_SD_MAX_IMAGE_PIXELS` | 同名 | `4096` / `16777216`（16 MiP） | 解碼 PNG 的寬高與總像素上限 |
| `ART_SD_PREPIN_SAMPLES_FORMAT` | 同名 | `False` | 選用：啟動時把伺服器持久設定 `samples_format` 預先釘選為 `png`（`POST /sdapi/v1/options`，每行程式一次）。⚠️ 這會永久改變共用伺服器的持久預設值，只建議用於專屬 sd-webui 實例；一般情況靠請求內 `override_settings.samples_format` 即足夠 |
| `ART_SD_OUTPUT_FORMAT` | 同名 | `png` | 本機轉碼輸出的格式（`png`／`webp`／`jpeg`／`avif`，大小寫不拘）；衍生副檔名 `.png`／`.webp`／`.jpg`／`.avif`。切換格式後既有資產照常展示與服務，直到個別主題重新生成才換檔（換檔時舊檔在新狀態提交後才刪除） |
| `ART_SD_OUTPUT_QUALITY` | 同名 | `80` | 有損格式（webp／jpeg／avif）的品質 1–100；png 忽略此值 |
| `ART_SD_PRESERVE_GENERATION_METADATA` | 同名 | `True` | 是否在輸出內嵌 A1111 形式的生成資訊（提示詞、負向提示詞、步驟、CFG、取樣器、排程器、seed、尺寸、模型）；`png` 走文字區塊、有損格式走 EXIF，來源一律是引擎-known 的請求值；`False`＝完全不寫入（此時 seed 仍存於記錄供程式使用） |

標註「同名」的設定由同名環境變數設定（變數不存在或空白時用預設值；存在但無效的值會在啟動時直接報錯並點名變數，絕不靜默失效）。完整的三層設定模型、優先順序與驗證規則見[設定與環境變數](/development/settings-and-environment)。

### 提示詞編輯流程（美術生成）

1. 編輯 `prompts/art.yaml` 的三個 `art.*` 生成鍵。
2. `uv run --locked python -m world.prompts.validate` 驗證。
3. 重新啟動（或 reload）伺服器。
4. 對已完成的 `done` 記錄，`@art status` 會顯示「提示詞變更」標記（`hash_changed`），圖片不會被取代。
5. 確認要套用後，用 `@art requeue <subject-key>` 重新生成；重新生成失敗時，先前的有效圖片會被保留，不會被破壞。

## 容器注意事項

- 掛載是唯讀的：伺服器不會寫入提示詞；管理員在主機上編輯。
- 同一個資料夾在容器內是世界可讀的；引擎內的 sd-webui 客戶端（設計 D11 修正）讀取 `art.*` 生成提示詞，與其他層共用同一個資料夾與載入驗證。
- 掛載會覆蓋映像內建的預設檔案，兩邊內容相同，沒有分歧風險。

## 本機預覽文件

```sh
uv run --locked python -m http.server --directory docs 3000
```

瀏覽 `http://localhost:3000` 預覽 docsify 文件站。
