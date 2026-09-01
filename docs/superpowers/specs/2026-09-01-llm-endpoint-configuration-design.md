# LLM 端點設定 — 環境變數可覆寫的 Profile 設計

**日期：** 2026-09-01
**狀態：** 已核准。實作拆為兩個 OpenSpec 變更，見 §8。
**範圍：** `world/ai/profiles.py`、`world/ai/client.py`、`server/conf/settings.py`、
`server/conf/llm_knobs.py`（新）、
`server/conf/test_settings.py`、`compose.yaml`、`.env.example`、
`docs/development/settings-and-environment.md`，以及 `llm-client`／
`settings-environment-overrides` 兩份主規格（經 OpenSpec delta 修訂）。

本文件從屬於 `2026-07-29-ai-mud-engine-design.md`（架構唯一真相來源）。本文件
僅修訂該設計中生成層的**設定表面**；單一寫入者邊界、guardrail 的
驗證—重試—降級管線、以及離線可玩性不變量，皆原樣重申、不予更動。

---

## 1. 問題陳述

`llm-client` foundation 以 local-first 出貨：每個生成層的端點來自一個凍結的
`LLMProfile`，其中唯一由環境推導的欄位是 `base_url`（讀自
`OLLAMA_BASE_URL`）。其餘一切——模型名稱、headers、每層取樣參數——只能靠手改
`secret_settings.py` 裡的 `LLM_PROFILES` 才能到達。

這對真實部署而言不可用：

1. **無法選模型。** 內建預設模型是 `llama3.2`。vLLM 只要以其他
   `--served-model-name` 啟動，每個請求都會得到 HTTP 4xx；guardrail 降級，
   玩家無論輸入什麼構想都看到 `concept_unavailable`。而且沒有任何 knob 可修。
2. **無法接託管供應商。** OpenRouter（及任何需驗證的 OpenAI 相容閘道）需要
   `Authorization: Bearer` 金鑰，且為完整歸因需要 `X-Title` + `HTTP-Referer`
   兩個 header。profile 有原生 `headers` 映射，但金鑰沒有第一class的存放位置，
   也沒有任何環境路徑可設定它。
3. **取樣參數完全不可設定。** vLLM 級端點接受 `frequency_penalty`、
   `presence_penalty`、`top_k`、`top_p`、`repetition_penalty`、`min_p`、
   `top_a` 與 reasoning 控制欄位，一個都表達不了——能調的只有 `temperature`。
4. **`OLLAMA_BASE_URL` 這個名字現在是錯的。** 該變數指向任何 OpenAI 相容端點；
   在 OpenRouter 進入範圍後，這個名字已成主動誤導。

繼承自倉庫、不可妥協的拘束：

- **開機即 fail-closed。** 設錯的部署 knob 必須在 settings 匯入時拋錯，點名
  變數、原始值與被違反的規則——這是 `_env_typed` 的契約。絕不靜默退回預設值。
- **離線可玩性。** 端點被關閉或連不上時，降級行為與今日完全一致
  （`concept_unavailable`、template 抽取、deterministic producers）。本設計改的是
  *請求*，永遠不是降級語意。
- **金鑰永不進記錄。** 傳輸層的 safe-log 行只報錯誤類別；API key 不得出現在
  任何 log、`repr` 或錯誤訊息中。
- **不做向後相容層。** 本專案無已發布使用者：舊變數名稱直接移除，不留 alias。

## 2. 決策

| # | 決策 | 理由 |
|---|---|---|
| C-1 | **環境解讀住在 `server/conf/settings.py`，不住 `world/ai/`。** 所有 `LLM_*` 變數經由既有 `_env_str` / `_env_typed` / `_env_bool` / `_env_choice` 助手讀取；解析結果注入 `default_profiles()`。 | 每個其他部署 knob 都遵此先例。重用助手使驗證器恰好只有兩處且各司其職（開機 env 語法、構造時 profile 界線），且 `profiles.py` 保持 env-free——這正是 `.env.example` 庫存契約所假設的形態。 |
| C-2 | **全域 knob + 每層例外覆寫。** `LLM_<SUFFIX>` 套用全部七層；`LLM_<LAYER>_<SUFFIX>` 覆寫單層。 | 常見情況操作者只需設幾個變數；profile 系統存在的原有理由（每層差異化）被保留，而不必寫 7×23＝161 個每層變數（共 184 個生成名稱）。 |
| C-3 | **優先序：code default < 全域 env < 每層 env < `secret_settings.py`，且 secret 層級按層合併。** `secret_settings.py` 的 `LLM_PROFILES` 只取代它具名的那些層（該層條目整組取代、不做欄位合併）；未具名的層保留其環境解析值。仍是操作者私密設定的最終權威，但只具名一層的 secret 覆寫不可能再靜默丟棄其他六層的環境設定（duck 審查 BLOCKER 修正）。 | 與所有其他 knob 已文件化的有效優先序一致；按層合併使宣稱的優先序在實作上真的成立。 |
| C-4 | **`LLMProfile` 用明確的型別化欄位，不用自由 `extra_body`。** 每個取樣參數都是具名、驗證過、可選的欄位。 | profile 系統的存在理由就是嚴格驗證。未型別的直通字典會讓 `min_p`、`top_a` 與罰項區間無界可守、無測可保。 |
| C-5 | **省略即預設；`None` 永不序列化。** 每個新取樣欄位預設 `None`／未設定，除非顯式設定，否則不出現在 request body。 | Ollama／vLLM／OpenAI 對可選欄位的接受度互不一致；只送操作者要求的是唯一可移植的行為，且在新 knob 全未設定時讓今日線格式逐位元組不變。 |
| C-6 | **扁平直通 + 一個標準化的 reasoning 映射。** `frequency_penalty`、`presence_penalty`、`top_k`、`top_p`、`repetition_penalty`、`min_p`、`top_a` 有設定者原樣進 body。reasoning 依 `reasoning_style` 映射：`openrouter` → `{"reasoning": {"enabled", "effort"}}`，`vllm` → `{"chat_template_kwargs": {"enable_thinking"}}`，`off` → 不送。 | vLLM 原生吃這些取樣 Extras；OpenRouter 把它們轉送給 provider Extras。reasoning 是唯一形態真正分歧的欄位，且裸送扁平 `reasoning` 會讓 vLLM 的 OpenAI 端回 400——所以它是明確、有測試的映射，不是猜測。 |
| C-7 | **`LLM_BASE_URL` 取代 `OLLAMA_BASE_URL`；舊名移除。** | 照專案政策的乾淨切割。`compose.yaml`、`.env.example`、容器契約測試、庫存 allow-list 與文件在同一變更內遷移。 |
| C-8 | **`LLM_API_KEY` 成為環境變數支援的憑證；文件政策為此單一 knob 反轉，並載明風險。** | 使用者要求免改檔部署的託管供應商存取。洩漏風險是真的（程序清單與 `compose inspect` 會暴露環境），文件點名風險與緩解：`env_file:` 取代 inline `environment:`；拒絕此暴露的操作者繼續用 `secret_settings.py`。`ART_SD_USERNAME`／`ART_SD_PASSWORD` 維持舊規則——本次反轉僅限 LLM 金鑰。 |
| C-9 | **歸因是一對可選 header。** `LLM_APP_TITLE` → `X-Title`，`LLM_APP_URL` → `HTTP-Referer`，各自非空才送。 | OpenRouter 歸因契約文件化了這兩個；多送的靜態 header 對其他端點無害，故這一對不需要供應商開關。 |
| C-10 | **`max_completion_tokens` 取代 `max_tokens`。** 有設定時在 body 中**取代** `max_tokens`，而非並存。 | OpenAI 已將 `max_tokens` 標為棄用而 vLLM 兩者都支援；同時送出會招來最嚴格端點的 400。 |

## 3. 環境變數表面

單一表格是唯一真相來源：宣告式 knob 清單（23 列：`(profile 欄位, env 後綴, 轉換器,
界線, 預設)`）住在新模組 `server/conf/llm_knobs.py`（匯入安全、零環境讀取），附純函式
`llm_env_names()` 產生全部 184 個名稱（23 全域 + 23×7 每層）。`server/conf/settings.py`
匯入並使用它、匯出 `LLM_ENV_NAMES = frozenset(llm_env_names())`。没有任何 knob 是每層
手寫的，表面不可能漂移；而測試 bootstrap 與庫存契約都能在匯入生產 settings 之前直接
消費同一個惰性定義（兩者的 AST 抽取都看不見迴圈生成的名稱）。

### 3.1 Knob 清單

| 變數（全域形態） | Profile 欄位 | 型別／界線 | Code 預設 | 備註 |
|---|---|---|---|---|
| `LLM_BASE_URL` | `base_url` | 非空 URL 字串 | `http://127.0.0.1:11434` | 取代 `OLLAMA_BASE_URL`；compose 預設 `http://host.containers.internal:11434` |
| `LLM_PATH` | `path` | 非空字串 | `/v1/chat/completions` | |
| `LLM_API_KEY` | `api_key` | 自由字串，可選 | 空 → 不帶 `Authorization` header | dataclass 欄位標 `repr=False` |
| `LLM_APP_TITLE` | `app_title` | 自由字串，可選 | 空 → 不帶 `X-Title` header | OpenRouter 歸因 |
| `LLM_APP_URL` | `app_url` | 自由字串，可選 | 空 → 不帶 `HTTP-Referer` header | OpenRouter 歸因 |
| `LLM_MODEL` | `model` | 非空字串 | `llama3.2` | 必須等於 vLLM 的 `--served-model-name` |
| `LLM_TEMPERATURE` | `temperature` | 有限 float，`0..2` 含端點 | `0.7` | 既有界線，現在可用 env 設定 |
| `LLM_FREQUENCY_PENALTY` | `frequency_penalty` | float，`−2..2`，可省略 | 未設定 | |
| `LLM_PRESENCE_PENALTY` | `presence_penalty` | float，`−2..2`，可省略 | 未設定 | |
| `LLM_TOP_K` | `top_k` | 正整數，可省略 | 未設定 | vLLM Extras |
| `LLM_TOP_P` | `top_p` | float，`0 < x ≤ 1`，可省略 | 未設定 | |
| `LLM_REPETITION_PENALTY` | `repetition_penalty` | float，`x > 0`，可省略 | 未設定 | vLLM Extras |
| `LLM_MIN_P` | `min_p` | float，`0 ≤ x ≤ 1`，可省略 | 未設定 | vLLM Extras |
| `LLM_TOP_A` | `top_a` | float，`x ≥ 0`，可省略 | 未設定 | vLLM Extras |
| `LLM_REASONING_ENABLED` | `reasoning_enabled` | 布林三態：未設／truthy／falsy | 未設定 | 空白 ≠ `false`；空白＝不送 |
| `LLM_REASONING_EFFORT` | `reasoning_effort` | 閉集 `minimal`／`low`／`medium`／`high`，可省略 | 未設定 | 不分大小寫，儲存為小寫 |
| `LLM_REASONING_STYLE` | `reasoning_style` | 閉集 `openrouter`／`vllm`／`off` | `openrouter` | 選擇 C-6 的映射；僅在任一 reasoning 欄位有設定時才被查詢 |
| `LLM_MAX_COMPLETION_TOKENS` | `max_completion_tokens` | 正整數，可省略 | 未設定 | 有設定時在 body 中取代 `max_tokens` |
| `LLM_MAX_TOKENS` | `max_tokens` | 正整數 | `250`（action_options `320`、title_nomination `640`） | 每層 code 預設保留 |
| `LLM_TIMEOUT_SECONDS` | `timeout_seconds` | 正整數 | `60` | |
| `LLM_MAX_RETRIES` | `max_retries` | 非負整數 | `2` | |
| `LLM_SUPPORTS_RESPONSE_FORMAT` | `supports_response_format` | 布林 | `False`；`action_options` 被 `REQUIRED_PROFILE_FLAGS` 強制 `True` | 企圖用每層覆寫清掉 action_options 旗標仍會開機失敗 |
| `LLM_ENABLED` | `enabled` | 布林 | `True` | 每層離線降級開關 |

每層形態：`LLM_<LAYER>_<SUFFIX>`，層名大寫且底線保留——`NARRATOR`、
`NPC_DIALOGUE`、`SCENARIO_DIRECTOR`、`SCENE_BUILDER`、`ACTION_OPTIONS`、
`TITLE_NOMINATION`、`CHARACTER_CREATION`。例：
`LLM_CHARACTER_CREATION_MODEL=qwen2.5-32b-instruct`。

### 3.2 解析規則

- 未設定、或 strip 後空白 ⇒ 無意圖 ⇒ code 預設（可省略欄位則為 `None`）。
  這正是既有 `_env_typed` 契約。
- 有值但非法 ⇒ settings 匯入時拋 `ImproperlyConfigured`，點名變數、原始值、
  規則。被拒絕的值包括：非有限 float、超出範圍的罰項、正整數 knob 收到 `0`、
  以及任何閉集之外的 reasoning-effort 值。
- 三態 `LLM_REASONING_ENABLED` 區分*未設定*（變數缺席或空白）與*顯式 false*
  （falsy 字），因為在支援 reasoning 的端點上「關閉推理」與「不送該欄位」
  是兩個不同的請求。布林字來自既有固定 truthy/falsy 字彙表。
- `server/conf/test_settings.py` 在匯入生產 settings 前把每個生成的名稱從
  `os.environ` pop 掉，與 `ART_SD_*` 的做法完全相同，因此執行環境的 shell
  永遠不可能改變一次測試跑的有效 profiles。

## 4. 元件與資料流

```
os.environ
   │  （唯一讀者：server/conf/settings.py，經由 _env_* 助手）
   ▼
LLM_PROFILES raw dict ──secret_settings.py 可整組取代──▶ build_profiles()
                                                            │ validate_profile_values
                                                            ▼
                                                     凍結 LLMProfile × 7
                                                            │ get_profile(layer)
                                                            ▼
                  server/*_service.py build_*_client() → OpenAICompatClient(profile)
                                                            │
                                             _format_request_body(profile, descriptor)
                                             _headers(profile)
                                                            ▼
                                              POST {base_url}{path}
```

### 4.1 `world/ai/profiles.py`

- `LLMProfile` 新增：`api_key`（預設 `""`，`field(repr=False)`）、
  `app_title: str = ""`、`app_url: str = ""`、`frequency_penalty: float | None`、
  `presence_penalty: float | None`、`top_k: int | None`、`top_p: float | None`、
  `repetition_penalty: float | None`、`min_p: float | None`、`top_a: float | None`、
  `reasoning_enabled: bool | None`、`reasoning_effort: str | None`、
  `reasoning_style: str`（預設 `"openrouter"`）、`max_completion_tokens: int | None`。
- `validate_profile_values` 為每個新欄位把界線，包括 `reasoning_style` 與
  `reasoning_effort` 的閉集驗證，並拋出既有的
  `ProfileValidationError(layer, field, message)`。
- `default_profiles(defaults: Mapping[str, Any] | None = None)` 不再讀
  `os.environ`。省略 `defaults` 時回傳純 code 預設；`server/conf/settings.py`
  傳入 env 解析後的覆寫值。結果：`server/conf/tests/test_env_overrides.py` 的
  `EXTERNAL_READERS` allow-list 中 `OLLAMA_BASE_URL` 條目被刪除，因為 settings.py
  之外再無任何環境變數讀者。
- `build_profiles`／`get_profile` 語意不變：未知層 → `UnknownLayerError`、
  重複條目 → `ProfileValidationError`、缺層 → 預設值、每層必要旗標在通用界線
  之後強制。

### 4.2 `world/ai/client.py`

`_format_request_body` 依序合成：

1. `model`、`messages`、`temperature`（如今日）。
2. `max_completion_tokens` 有設定時用它，否則 `max_tokens`。
3. 每個非 `None` 的取樣欄位原樣併入。
4. reasoning 依 `reasoning_style`，僅當 `reasoning_enabled` 或
   `reasoning_effort` 有設定時；`vllm` 形態送
   `chat_template_kwargs.enable_thinking` 並丟棄 `effort`（vLLM 無對應物），
   `openrouter` 形態送巢狀 `reasoning` 物件並省略 `None` 子鍵，`off` 什麼都不送。
5. `response_format` 與今日完全相同（旗標 AND 宣告的 schema）。

`_request_headers(profile)` 先對非空的對應欄位注入派生值——`Authorization: Bearer
<api_key>`、`X-Title`、`HTTP-Referer`——再疊上 `profile.headers`，使操作者在
`secret_settings.py` 顯式設定的同名 header（exact-case）取勝（逃生口）。金鑰絕不被插入
任何 log 行或錯誤字串；`_safe_log_error` 本來就只記 `LLMTransportError.kind`。
防走私：`_normalize_headers` 以大小寫不分拒收 `authorization`／`proxy-authorization`／
`x-api-key`／`api-key` 這幾個敏感 header 名稱（dataclass `repr` 包含 headers 映射，把
bearer 塞進 headers 會癱瘓 `api_key` 的 `repr=False` 保護）；錯誤點名層與 `headers`
欄位並指回 `api_key` 這條正當路徑。

`FakeLLMClient` 不受影響：它以 messages + `schema_id` 比對，body 形態的斷言
屬於真實客戶端的測試。

### 4.3 降級行為

不變，且刻意不動：傳輸／HTTP／malformed／timeout 失敗用盡重試預算 →
該層的降級標記 → `concept_unavailable`（concept seam）、template 抽取
（director）、其他層的 deterministic producers。本設計的目標是「正確設定的
端點不再降級」；失敗模式本身不在重新規格的範圍。

## 5. 部署表面

- `compose.yaml`：`evennia` 服務以既有 `host.containers.internal` 預設傳
  `LLM_BASE_URL`，其餘可選 knob 經由 `${LLM_X:-}` 轉傳，使未設定的變數到達時
  為空白（＝省略）而非字面文字。`OLLAMA_BASE_URL` 移除。
- `.env.example`：每個 knob 依該檔既有的逐 knob 註解格式文件化，含一個完整的
  vLLM 範例與一個完整的 OpenRouter 範例，以及每層覆寫範例。
  `OLLAMA_BASE_URL` 由 `LLM_BASE_URL` 取代，不留 alias。
- `tests/test_container_contract.py`：compose 斷言遷移到 `LLM_BASE_URL`。
- `docs/development/settings-and-environment.md`：新增 LLM knob 表；
  「必須留在 `secret_settings.py`」一節失去 `LLM_PROFILES` 每層那行（已可經 env
  到達，secret_settings 仍是最終權威），並加入一條限定範圍的說明：
  `LLM_API_KEY` 是「憑證不走環境」規則的刻意例外，附其洩漏途徑
  （`/proc/<pid>/environ`、`podman compose config`、`docker inspect`）與緩解
  （以 `env_file:` 取代 inline `environment:`，或維持改用 `secret_settings.py`）。
- OpenSpec：一個變更，delta 落在 `llm-client`（env 推導的 profile 預設值、新
  profile 欄位、request body／header 序列化）與 `settings-environment-overrides`
  （庫存契約、C-8 的政策反轉）。`llm-client` 主規格的需求
  「No commercial API endpoint SHALL be configured as a built-in default」
  **逐字保留**——OpenRouter 只有在操作者顯式設定 `LLM_BASE_URL` 時才可到達。

## 6. 測試

| 領域 | 測試 |
|---|---|
| Profiles（`world/ai/tests/test_profiles.py`） | 每個新欄位的界線矩陣（區間內、邊界、超界、非有限、錯型別）；`reasoning_style`／`reasoning_effort` 閉集驗證；`None` 預設值缺席；`repr(profile)` 不含 `api_key`；注入 `defaults` 的合併；`action_options` 必要旗標失敗路徑 |
| Client（`world/ai/tests/test_client.py`） | Request body 序列化矩陣：每個取樣欄位的出現／缺席；`max_completion_tokens` 取代 `max_tokens`；三種 reasoning 形态 × enabled/effort 組合；新 knob 全未設定時 body 與今日_payload_逐位元組相容（回歸）；有／無 `api_key`、`app_title`、`app_url` 的 header 矩陣；錯誤路徑字串絕不含金鑰 |
| Settings（`server/conf/tests/`） | 每個 knob 的 fail-closed 開機錯誤（點名變數、原始值、規則）；全域—每層優先序；空白 ⇒ 預設；三態 reasoning-enabled 的未設 vs false；`test_settings.py` sanitize 清單涵蓋每個生成名稱 |
| 庫存契約（`test_env_overrides.py`） | `.env.example` 金鑰 ↔ settings.py AST env 讀取（生成的名稱全部可解析）；`EXTERNAL_READERS` 不再列 `OLLAMA_BASE_URL`；AST 讀者學會識得生成的 knob 迴圈，庫存檢查不得假陰錯 |
| 容器（`tests/test_container_contract.py`） | `LLM_BASE_URL` 存在且帶 host-gateway 預設；`OLLAMA_BASE_URL` 不存在 |
| 追溯 | 新增／變更的主規格需求以 `tools.spec_traceability list` 的 ID 標 `covers_requirement`；`check` 閘門綠燈 |

所有測試離線且確定性（FakeLLMClient／注入 reactor 時鐘）；沒有任何測試接觸真實
端點。本地閘門：先跑 focused labels，再以 `--parallel 16 --noinput` 跑非瀏覽器 suite。

## 7. 範圍外

- 回應側 reasoning-content 的解析（供應商是否回傳 `reasoning_content` 欄位、
  narrator 各層如何消費）。
- guardrail 重試預算、語意驗證器、降級 hook 或 prompt registry 的任何改動。
- 逐請求模型路由（呼叫時選模型而非每層選）、供應商健康探測、成本核算。
- sd-webui 憑證對（`ART_SD_USERNAME`／`ART_SD_PASSWORD`）——維持「不走環境」舊規則。
- 把 `SECRET_KEY`／`ALLOWED_HOSTS` 遷出 `secret_settings.py`。

## 8. OpenSpec 變更清單與實作順序

本設計由兩個 OpenSpec 變更實作，每個變更都是單一工程師一個工作天（8 小時）可完成的
規模：

| 順序 | 變更 | 內容 | Delta 規格 |
|---|---|---|---|
| 1 | `env-overridable-llm-profiles` | `LLMProfile` 新欄位＋驗證；惰性 knob 模組 `server/conf/llm_knobs.py`＋`llm_env_names()`；settings 解析（全域＋每層 env、`_env_optional`／`_env_optional_bool`）；D-A7 按層 secret 合併；`OLLAMA_BASE_URL`→`LLM_BASE_URL` 乾淨改名；`test_settings.py` sanitize；庫存契約改造；`headers` 憑證走私拒收；文件 knob 表 | `llm-profiles`、`settings-environment-overrides`、`llm-client`（僅 base-URL 改名需求） |
| 2 | `llm-endpoint-wire-configuration` | `_format_request_body` 序列化（取樣直通、`max_completion_tokens` 取代、reasoning 三形態完整案例表）；`_request_headers` 標頭合成；金鑰防洩漏守衛；`StubAgent` 擷取改造＋線級測試矩陣；compose 可選 knob 空白轉傳；`LLM_API_KEY` 政策反轉文件 | `llm-client`、`settings-environment-overrides` |

**依賴：** 變更 2 依賴變更 1（profile 欄位與 `llm_env_names()` 必須先存在；否則變更 2
無法構造帶欄位的 profile，測試會響亮失敗而非半可用）。順序由共用的 `LLMProfile`
簽名強制，不需要執行期守衛。

**衝突面（不可並行）：** 兩者都碰 `world/ai/tests/test_client.py`、`.env.example`、
`docs/development/settings-and-environment.md`、`compose.yaml` 區塊與
`llm-client`／`settings-environment-overrides` 的 delta——同檔同規格，必須序列化實作。
建議批次：Batch 1 = 變更 1（單獨）；Batch 2 = 變更 2（單獨）。變更 1 實作完成並
`openspec archive`＋delta 同步後，變更 2 的 `settings-environment-overrides` delta
才對準 post-變更 1 的規格狀態。

**Rubber-duck 審查（已套用）：** 3 BLOCKER（secret 全圖取代破壞每層優先序→D-A7 按層
合併；delta 六層/實作七層漂移→七層修正＋預設值存活場景；標頭優先序自相矛盾→D-B2
單一字序）與 4 MAJOR（24→23 knob 計數＋精確集合等式測試；`LLM_ENV_NAMES` 匯入順序
不可行→惰性 `llm_knobs.py`＋純 `llm_env_names()`；`headers` 內 Authorization 走私
繞過 `repr=False`→構造時大小寫不分拒收敏感標頭名；reasoning 邊角（openrouter
effort-only、vllm effort-only 不送、`off` 帶值不送、enabled=false 要送 false）→
完整案例表＋測試矩陣）與 1 MINOR（shard 清單陳述）全部修正於兩份變更的 artifacts。
