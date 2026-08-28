# OpenSpec 測試可追溯性

每個現行的 OpenSpec 需求都必須至少關聯一個真實的單元測試或整合測試。需求可追溯性與 Python 程式碼覆蓋率是各自獨立的品質閘門，標註用於宣告測試所驗證的行為，Coverage.py 則測量實際執行的第一方程式碼。

現行契約僅從 `openspec/specs/<capability>/spec.md` 的直接能力規格讀取。位於 `openspec/changes/` 的提議規格與位於 `openspec/changes/archive/` 的歷史規格均不列入計算。

## 需求識別碼

驗證工具會以下列格式衍生識別碼：

```text
<capability>::<normalized-requirement-name>
```

正規化會套用 Unicode NFKC、大小寫摺疊（case folding），並將連續的非英數字元替換為 `-`。請勿手動組合識別碼。可透過下列命令列出標準識別碼及其來源位置：

```sh
uv run --locked python -m tools.spec_traceability list
```

更名後的需求會取得新的識別碼。在審查契約變更時，請同步更新其測試標註。空的識別碼與正規化衝突均屬驗證錯誤。

## 標註測試

從 `tools.spec_traceability` 匯入輔助函式，並直接套用在可被探索到的 `test_*` 函式或方法上：

```python
from tools.spec_traceability import covers_requirement


class DamageTests(unittest.TestCase):
    @covers_requirement("combat-resolution::damage-is-defense-reduced-with-a-floor-of-one")
    def test_defense_reduces_damage_but_never_below_one(self):
        result = calculate_damage(attack=10, defense=100)
        self.assertEqual(result, 1)
```

當一個測試的斷言實質上驗證了多個需求時，可以同時涵蓋它們：

```python
@covers_requirement(
    "world-clock::world-clock-advances-deterministically",
    "settlement-stage-order::due-events-settle-in-a-fixed-order",
)
def test_clock_advances_and_settles_stages_in_order(self):
    ...
```

參數必須是一個或多個字串常面值（string literal）。裝飾器必須從 `tools.spec_traceability` 匯入；支援該匯入的別名。驗證工具會拒絕動態參數、未知識別碼、無效匯入，以及放置於非測試可呼叫物件上的裝飾器。

標註是一項可供審查的宣告，並非斷言強度的證明。僅在測試輸入、動作與斷言確實建立該需求時才可加入標註。切勿附加無關測試、削弱斷言、加入占位測試，或使用略過的測試來填補可追溯性缺口。驗證工具刻意不提供基準線、豁免或允許清單。

## 靜態驗證

在編輯規格或測試時執行靜態驗證：

```sh
uv run --locked python -m tools.spec_traceability check
```

此命令會解析規格與測試原始碼，而不會匯入遊戲模組。若有標註錯誤或任何現行需求缺乏有效關聯，命令即告失敗。加入 `--json-output <path>` 可輸出確定性報告，供交接或自動化處理使用。

## 成功執行證據

僅具備靜態存在性不足以通過 CI 閘門。裝飾器僅在已標註的測試成功返回且已設定 `OPENSPEC_TEST_EVIDENCE` 時，才會寫入 JSON Lines 記錄。失敗、略過、預期失敗與未收集的測試均無法滿足需求。

請從全部三個互斥的 Python 入口點收集證據並進行驗證：

```sh
traceability_evidence=$(mktemp)
OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked python -m unittest discover -s web/tests/browser -t .
OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py --keepdb \
    commands server typeclasses world web.webclient
OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked -m unittest discover -s tests -t .
uv run --locked python -m tools.spec_traceability verify \
  --evidence "$traceability_evidence"
```

全部三個測試命令均為必要。受管瀏覽器、非瀏覽器 Evennia 與最上層測試套件彼此不可互相替代。

## 最終本機品質閘門

在交接前執行嚴格 OpenSpec 驗證、具備證據感知的可追溯性驗證，以及 `git diff --check`。當儲存庫達到零真實需求缺口且覆蓋率相依套件與設定均已啟用時，請執行確切的匯總覆蓋率流程：

```sh
COVERAGE_FILE=.coverage.browser \
  OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked coverage run -m unittest discover \
    -s web/tests/browser -t .
COVERAGE_FILE=.coverage.evennia \
  MUD_TEST_SETTINGS=1 \
  OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked coverage run -m evennia test \
    --settings test_settings.py --noinput \
    commands server typeclasses world web.webclient
COVERAGE_FILE=.coverage.top-level \
  OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked coverage run -m unittest discover -s tests -t .
uv run --locked coverage combine \
  .coverage.evennia .coverage.browser .coverage.top-level
uv run --locked coverage json --fail-under=0 -o coverage.json
uv run --locked python -m tools.verify_coverage_roots coverage.json
uv run --locked coverage report --fail-under=80
uv run --locked coverage xml -o coverage.xml
```

Evennia 測試執行器擁有 `commands`、`server`、`typeclasses`、`world` 與 `web.webclient` 底下的套件區域測試。明確的瀏覽器探索單獨擁有 `web/tests/browser/`；最上層儲存庫契約仍由 `unittest discover -s tests -t .` 擁有。覆蓋率仍精確測量 `commands`、`server`、`typeclasses`、`web` 與 `world` 這五個第一方根目錄；僅有位於 `*/tests/*` 底下的模組可被排除。相依套件程式碼、OpenSpec 工件與儲存庫工具均位於已設定的原始碼根目錄之外。所有三個覆蓋率資料檔案在套用匯總 80% 硬性門檻（hard gate is 80%）或為 Codecov 產生 `coverage.xml` 之前必須完成合併。專案將 90%（targets 90%）作為文件記載的目標而非強制門檻。瀏覽器包裝器記錄其父層測試控管架構，不主張受管伺服器子行程的覆蓋率。

專用的保留資料庫為 `server/db/evennia-test.sqlite3`。若資料庫遷移有所變更，可在重建時略過 `--keepdb` 並加上 `--noinput`。若保留狀態已損壞，僅刪除該檔案並重新執行乾淨設定；切勿刪除位於 `server/db/evennia.db3` 的開發者資料庫。

## 處理真實覆蓋缺口

若現有測試無法實質驗證某項需求，請維持未覆蓋狀態並產生確定性 JSON 報告。擁有該需求的行為變更必須補上缺失的單元測試或整合測試。待其斷言涵蓋契約後，在該測試旁加入標註，然後以執行證據重新執行兩個測試入口點。

在仍存在任何真實缺口時，切勿啟用或弱化所需的 CI 工作流程。進行中變更的需求在其增量同步進主規格後會進入此索引；其所屬變更必須已具備對應的行為測試，以便在主識別碼存在時立即加入標註。
