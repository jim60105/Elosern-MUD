# 提示詞資料庫

所有由應用程式擁有的 LLM 提示詞（旁白、NPC 對話、任務企劃、思考回饋、美術描述）都存放在儲存庫根目錄的 `prompts/` 資料夾，作為唯一來源。調整提示詞不需要改 Python 程式碼或重建映像：編輯 YAML 檔案、驗證、然後重新啟動（或 reload）伺服器即可套用。

> [!TIP]
> 若要深入了解使用這些提示詞的業務情境、系統架構與防護機制，請參閱開發者指南中的 [核心架構與邊界契約](/development/llm-architecture)、[7 大業務情境與調度流程](/development/llm-scenarios) 以及 [護欄天梯與語意驗證機制](/development/llm-guardrails)。

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
├── art.yaml                美術描述範本與生成提示詞（scene／portrait／negative）
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

## 鍵與預留位置

| 鍵 | 檔案 | 允許的預留位置 |
| --- | --- | --- |
| `narrator.system` | `narrator.yaml` | 無 |
| `npc_dialogue.system` | `npc_dialogue.yaml` | `{name}`、`{desc}`、`{location}` |
| `scenario_director.system` | `scenario_director.yaml` | 無 |
| `npc.thinking` | `npc.yaml` | `{name}` |
| `art.character_description` | `art.yaml` | `{race}`、`{age}`、`{appearance}`、`{equipment}`、`{custom}` |
| `art.monster_description` | `art.yaml` | `{description}`、`{display_name}`、`{examples}` |
| `art.scene_prompt` | `art.yaml` | `{description}` |
| `art.portrait_prompt` | `art.yaml` | `{description}` |
| `art.negative_prompt` | `art.yaml` | 無 |
| `character_creation.system` | `character_creation.yaml` | 無 |
| `action_options.system` | `action_options.yaml` | 無 |
| `action_options.user` | `action_options.yaml` | `{room_name}`、`{room_summary}`、`{npc_entries}`、`{monster_entries}`、`{objective}`、`{narrative_tail}`、`{affordances}` |

只有允許清單內的 `{token}` 會被替換，替換是逐一且精確的：

- `{name}`、`{location}` 這類允許的預留位置會被代入實際值。
- 兩個大括號包住的名稱（如 `{{name}}`）是字面文字，不會被替換。
- 提示詞內的 JSON 範例（如 `{"speech": "你要說的話", "intent": {"kind": "..."}}`）原樣保留，不會被當成預留位置。
- 不在允許清單內的 `{token}`（例如把 `{name}` 打成 `{nmme}`）會在載入時回報錯誤，不會靜默忽略。

`art.character_description` 的 `{appearance}` 槽位是外觀資訊進入肖像提示詞的唯一路徑。把該槽位從部署的 `art.yaml` 範本移除，外觀區塊會從提示詞消失而不會報錯。範本仍是唯一來源，移除槽位屬於合法編輯。

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

- `art.scene_prompt` — 場景主體的正向提示詞範本，含一個 `{description}` 預留位置；代入值是該場景在登錄表中的確定性一句話描述。場景不在去背階段的主體允許清單內，因此保留前景、中景與背景的繪製構圖。
- `art.portrait_prompt` — 角色／怪物肖像的正向提示詞範本，同樣含 `{description}` 預留位置；代入值是確定性角色／怪物描述。已出貨範本要求完整身形與白色平坦背景，讓去背階段取得適合的輸入。管理員可修改掛載範本中的背景措辭，變更會透過已渲染提示詞摘要顯示。
- `art.negative_prompt` — 每個請求共用的負向提示詞，純文字、無預留位置。

範本文字以自然語言英文撰寫，涵蓋風格、構圖、光線與鏡頭，並與其他層一樣在載入時驗證。未知的 `{token}` 是載入時錯誤。改動三個鍵中任何一個，都會改變記錄的「已渲染提示詞摘要」（rendered-prompt digest）。既有的 `done` 記錄會標記為 `hash_changed` 供管理員審核，已完成的圖片不會被悄悄取代，也不會在一般遊玩中重新生成。本次範本異動後，管理員可對標記的主體執行 `@art requeue`，以新提示詞重新產生圖片。

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
| `ART_SD_PREPIN_SAMPLES_FORMAT` | 同名 | `False` | 選用：首次生成前把伺服器持久設定 `samples_format` 預先釘選為 `png`（`POST /sdapi/v1/options`，每行程式一次；僅在生成流程觸發，`@art health` 探測不會觸發）。⚠️ 這會永久改變共用伺服器的持久預設值，只建議用於專屬 sd-webui 執行個體；一般情況靠請求內 `override_settings.samples_format` 即足夠 |
| `ART_SD_OUTPUT_FORMAT` | 同名 | `png` | 本機轉碼輸出的格式（`png`／`webp`／`jpeg`／`avif`，大小寫不拘）；衍生副檔名 `.png`／`.webp`／`.jpg`／`.avif`。切換格式後既有資產照常展示與服務，直到個別主題重新生成才換檔（換檔時舊檔在新狀態提交後才刪除） |
| `ART_SD_OUTPUT_QUALITY` | 同名 | `80` | 有損格式（webp／jpeg／avif）的品質 1–100；png 忽略此值 |
| `ART_SD_PRESERVE_GENERATION_METADATA` | 同名 | `True` | 是否在輸出內嵌 A1111 形式的生成資訊（提示詞、負向提示詞、步驟、CFG、取樣器、排程器、seed、尺寸、模型）；`png` 走文字區塊、有損格式走 EXIF，來源一律是引擎-known 的請求值；`False`＝完全不寫入（此時 seed 仍存於記錄供程式使用） |
| `ART_SD_PROBE_TIMEOUT_MS` | 同名 | `5000` | `@art health` 連線探測（`GET /sdapi/v1/samplers`）的總預算毫秒數，1000–60000 包含兩端；僅診斷用途 |
| `ART_SD_PROBE_CACHE_SECONDS` | 同名 | `300` | 探測判定可重複使用的最長秒數，5–3600 包含兩端；URL／憑證存在性／探測預算任一變更即失效；`@art health` 一律強制重新探測 |
| `ART_REMBG_ENABLED` | 同名 | `False` | 肖像背景移除（rembg）總開關。`true` 一行即啟用：`#ART_REMBG_ENABLED=true`（寫入 `.env` 後重啟）。場景藝術**永不**去背；種子同步的藝術保留原背景（引擎不重寫操作者供應的檔案） |
| `ART_REMBG_MODEL` | 同名 | `bria-rmbg` | 去背模型，封閉集合 `bria-rmbg/isnet-anime/isnet-general-use/u2net/u2netp`（不分大小寫）。⚠️ 授權：`bria-rmbg` 封裝 BRIA 授權的 RMBG-2.0 權重，非商業免費、商業使用需向 BRIA 取得授權；`isnet-anime`（約 176 MB）是寬鬆授權的替換品，改一個變數加 `@art requeue` 即可 |
| `ART_REMBG_DOWNLOAD_ENABLED` | 同名 | `True` | 允許首次使用時由 rembg 下載模型到持久 volume。`false` 加上預置的 `server/.rembg` volume＝無執行期網路配置；模型缺席時每個肖像 job 立即以有界的 `art_cutout_unavailable` 失敗 |
| `ART_REMBG_ALLOWANCE_SECONDS` | 同名 | `120` | 啟用時每項租約寬限秒數，10–1800 包含兩端；是租約預算而非強制逾時 |
| `ART_REMBG_THREADS` | 同名 | `0` | ONNX session 執行緒上限，0–256；`0`＝ONNX Runtime 自行決定；非零經 `OMP_NUM_THREADS` 送達（行程全域） |
| `ART_TRANSLATE_ENABLED` | 同名 | `False` | 提示詞本機前處理總開關。只翻譯含 Han 字的行，保留 authored `source_description` 與 `source_hash`；翻譯失敗會用原始提示詞生成圖片。執行引擎由 `add-ctranslate2-translate-backend` 提供 |
| `ART_TRANSLATE_DOWNLOAD_ENABLED` | 同名 | `True` | 允許首次使用時由 backend 下載翻譯模型到持久 volume（與 `ART_REMBG_DOWNLOAD_ENABLED` 同型，約 74 MB 的 `translate-zh_en-1_9` 封包）。`false` 加上預置的 `server/.translate` volume＝無執行期網路配置；模型缺席時立即以有界的 `art_translate_unavailable` 失敗 |
| `ART_TRANSLATE_THREADS` | 同名 | `0` | CTranslate2 intra-op 執行緒上限，0–256；`0`＝CTranslate2 自行決定；非零在建構時送達 translator |
| `ART_TRANSLATE_BACKEND` | —（僅限程式碼） | `world.art.translate_ct2.CTranslate2Backend` | 第三個 import-executing dotted-path seam，不提供環境變數。測試與瀏覽器 harness 使用 `world.art.fake_translate.FakeTranslator`，不載入翻譯函式庫也不開啟網路連線 |

標註「同名」的設定由同名環境變數設定（變數不存在或空白時用預設值；存在但無效的值會在啟動時直接報錯並點名變數，絕不靜默失效）。完整的三層設定模型、優先順序與驗證規則見[設定與環境變數](/development/settings-and-environment)。

### 翻譯模型種子（zh→en）

提示詞翻譯引擎（`world.art.translate_ct2.CTranslate2Backend`，add-ctranslate2-translate-backend）是本機 CPU 神經機器翻譯：它**不會拒絕**任何描述（這正是選它而非 chat 模型的原因）。模型取得走雙軌政策（add-translate-model-download-policy）：預設（`ART_TRANSLATE_DOWNLOAD_ENABLED=true`）下，若佈局檢查失敗，backend 會在首次使用的引擎建構鎖內、以有界的方式（逾時＋串流大小上限、零重試、失敗即鎖住本行程）把同一個 `translate-zh_en-1_9` 封包抓進持久目錄；設 `false` 則對話伺服器沒有任何下載翻譯模型的執行期網路行為——模型由操作者在主機上種子到持久目錄（下方路線一／二），缺目錄＝有界的 `art_translate_unavailable`。

**佈局契約**：`ART_TRANSLATE_MODEL_DIR`（裸機 `server/.translate`、容器 `/app/server/.translate`）必須包含

- `model/` — CTranslate2 模型目錄（`config.json` + `model.bin`）
- `sentencepiece.model` — SentencePiece 來源模型

兩條種子路線產生完全相同的佈局，引擎對「模型從哪來」一無所知（D3：換模型是操作者動作，不是程式碼變更）。

#### 路線一：Argos Open Tech `.argosmodel` 封包（建議，一條指令）

Argos 發行 CTranslate2 模型；只有它的 Python wrapper（本專案刻意不引入的重量級依賴）很肥。封包本身解壓就是上述佈局。使用隨附腳本（在主機執行，只依賴 `curl` 與 `unzip`）：

```sh
scripts/fetch-translate-model.sh                # 裸機預設種到 server/.translate
scripts/fetch-translate-model.sh --force        # 已種過時需 --force 覆蓋
scripts/fetch-translate-model.sh /some/path     # 指定目錄
```

腳本下載 `translate-zh_en-1_9.argosmodel`（官方封包索引指向 `https://argos-net.com/v1/`），驗證 zip 與所需項目（`model/config.json`、`model/model.bin`、`sentencepiece.model`），解出 `model/`＋`sentencepiece.model`，任何一環失敗都大聲退出。封包內含的 `stanza/`（wrapper 的斷句資料）不需要，刻意不解出——seam 已經按行切分。

⚠️ **授權**：封包 README 記載其模型衍生自 OPUS-MT zh→en（Tiedemann & Thottingal, EAMT 2020），**CC-BY 4.0**。腳本會把 `README.md` 一併種下作為來源與授權紀錄。

#### 路線二：自 `Helsinki-NLP/opus-mt-zh-en` 離線轉換

在有網路的作業站（不必是遊戲主機）用 CTranslate2 轉換器：

```sh
ct2-transformers-converter --model Helsinki-NLP/opus-mt-zh-en \
  --output_dir ct2-zh-en &&
mkdir -p /path/to/server/.translate/model &&
mv   ct2-zh-en/model.bin ct2-zh-en/config.json ct2-zh-en/shared_vocabulary.json /path/to/server/.translate/model/ &&
cp   ct2-zh-en/source.spm /path/to/server/.translate/sentencepiece.model
```

（Helsinki 的 OPUS 倉庫用 `source.spm`／`target.spm` 命名 Marian 的 SentencePiece 檔；轉換輸出直接構成 `model/`，再把 `source.spm` 複製為套件根目錄的 `sentencepiece.model`，即為引擎要求的佈局。轉換前先 `ls ct2-zh-en` 確認產生的是 `source.spm` 這個名字——不同筆轉換指令輸出略有出入，以實際檔名為準。若已存在種子，先確認兩個檔案都在再覆寫。）

⚠️ **授權**：`Helsinki-NLP/opus-mt-zh-en` 的 model card 標示 **CC-BY 4.0**（與路線一同一模型譜系與授權）。

#### 操作者食譜（端到端）

1. **種子**：跑路線一的腳本（或路線二轉換）到 `server/.translate`（裸機）或一個暫存目錄（容器）。
2. **掛載**：
   - 裸機：什麼都不用做——`server/.translate` 就是程式碼內預設的 `ART_TRANSLATE_MODEL_DIR`。
   - 容器：先 `podman compose up -d` 建立 `evennia-translate` 具名 volume，再一次性把暫存種子拷進 volume（腳本會印出完整指令）；之後 volume 在容器重建間保留。
3. **開啟**：`.env` 加 `ART_TRANSLATE_ENABLED=true`，重啟。
4. **確認**：啟動時會記錄 `art_optional_stages`（context 含 `art_translate: {setting: "ART_TRANSLATE_ENABLED", enabled: …}`）——它只反映開關狀態，不載入模型；翻譯階段真正就緒以一張含漢字的圖片生成成功、並記錄 `art_translate_done`（含 lines_total／lines_offered／lines_untranslated）為準，此時存放的中繼資料引用英文提示詞。

**未種子 volume 的降級路徑是設計內行為**：每次生成記錄一條 `art_translate_failed`（`art_translate_unavailable`）警告、以 authored 提示詞出圖、圖片照常產生——翻譯是「提示詞比較差」，不是失敗的工作。`@art status` 與 `@art retry`/`requeue` 的行為不變。

**肖像去背的誠實成本**：啟用後，首次生成肖像前 rembg 會下載約 1 GB 的模型檔（快取在持久的 `server/.rembg` volume，跨容器重建保留）；每張肖像在單一 worker 執行緒上多花約 10 秒 CPU；ONNX session 建立後 Evennia 伺服器行程的常駐記憶體**永久**增加約 1–1.5 GB（`isnet-anime` 少一個數量級）——小機器請以此估算，避免 OOM。去背只影響啟用後新生成的肖像；既有資產與種子同步檔案不會被回溯改寫，需要時用 `@art retry`／`@art requeue` 逐張重生成。去背失敗是有界失敗（`art_cutout_unavailable`／`art_cutout_error`）：保留前一份有效輸出、不阻斷批次、`@art retry` 在修復後即可恢復。`ART_REMBG_ENABLED=true` 時 `ART_SD_OUTPUT_FORMAT` 不得為 `jpeg`（JPEG 無法攜帶 alpha，啟動即拒絕）；`png`／`webp`／`avif` 皆可。

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
