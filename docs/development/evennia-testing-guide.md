# Evennia 測試效能優化指南

Evennia 的測試建立在 Django 測試框架之上。當測試數量增加後，執行時間通常不只來自被測程式碼，也包含 Django test database、Evennia 測試 fixture、Typeclass 物件建立、session 初始化，以及每個 test method 重複執行的 `setUp()`。

Evennia 目前提供的 `EvenniaTest` 會在 `setUp()` 中建立 accounts、rooms、objects、characters、script 與 session。這些工作會在每個 test method 前重新執行。相較之下，`EvenniaTestCase` 不經過 `EvenniaTestMixin`，官方文件也明確指出這種測試可以較快。

因此，優化 Evennia 測試時，建議從減少 fixture 成本開始，再考慮 test database 重用與平行處理。這個順序也比較容易維持測試隔離。

本文以目前 Evennia `main`／latest 文件與 Django 6.0 測試框架為依據。本專案已套用本文第一階段優化（`EvenniaTestCase`、`setUpTestData()`、test-only settings），實測數據與最終取捨記錄於「[Evennia 測試效能報告](evennia-test-performance)」。

!> **本專案已採用 `--parallel 16` 作為日常完整 suite 指令**（24-core 開發機實測 ~45s）。平行 runner 曾因測試非確定性（unseeded dice tie-break、共享 registry 未還原、直接覆寫共享 rulebook 檔）造成 race condition；這些問題已逐一修正（見「[Evennia 測試效能報告](evennia-test-performance)」的 Parallel Evaluation 一節），並以連續兩次全綠的完整 parallel run 作為證據。序列執行仍保留為最終 handoff 證據的標準做法。

!> **CI 的 quality gate 已改為多 job 平行結構（2026-08-11）**：non-browser Evennia suite 在 CI 以 `--parallel 4` 加上 subprocess-aware coverage 執行（`coverage run --concurrency=multiprocessing --parallel-mode`），managed browser suite 依 `.github/browser-shards.json` 的 manifest 分成六個 shard job（每個 test file 只有一個序列執行 owner），另有一個獨立的 top-level regression job；最後的 gate job 會下載所有 artifact、驗證每個預期的 coverage 與 evidence 檔都存在且非空、依 entry-point 順序合併 evidence、執行 `spec_traceability verify`、`coverage combine` 所有 sidecar、驗證 coverage roots、執行 90% aggregate gate，再產出並上傳 Codecov XML。top-level 的 contract tests（`tests/test_quality_gate_contract.py`、`tests/test_browser_verification_contract.py`、`tests/test_evennia_test_optimization_contract.py`）會持續 pin 這個結構。

## 先量測測試時間

不要直接從重構測試開始。先確認時間花在哪裡。

Django test runner 提供 `--timing` 與 `--durations`。前者會列出 database setup 與整體執行時間，後者會顯示最慢的 N 個測試。

```sh
evennia test \
    --keepdb \
    --timing \
    --durations 20 \
    mygame.tests
```

如果目前只修改一個 subsystem，日常開發不需要反覆執行整套測試。

```sh
# module
evennia test --keepdb world.tests.test_combat

# class
evennia test --keepdb \
    world.tests.test_combat.TestCombat

# method
evennia test --keepdb \
    world.tests.test_combat.TestCombat.test_attack
```

Evennia 官方文件也支援使用 dotted path 選擇特定測試。

遇到失敗時，可以加入 `--failfast`，讓 test runner 在第一個 failure 後停止。Django 的 `--failfast` 就是為縮短錯誤回饋時間提供的選項。

```sh
evennia test \
    --keepdb \
    --failfast \
    world.tests.test_combat
```

## 使用最輕量的測試基底

Evennia 的測試基底可以依測試需要的環境分級。

| 測試內容 | 建議基底 |
|---|---|
| 純 Python 邏輯 | `unittest.TestCase` 或 Django `SimpleTestCase` |
| 需要少量 Evennia DB 物件 | `EvenniaTestCase` |
| 需要完整 account、character、room、session 環境 | `EvenniaTest` |
| 需要完整 command fixture | `EvenniaCommandTest` |

`EvenniaTest` 的 `setUp()` 目前會依序建立 accounts、rooms、objects、characters、script，再建立 session。

因此，下面這種測試如果只測計算函式，沒有必要使用完整的 `EvenniaTest`。

```python
class DamageTest(EvenniaTest):
    def test_damage(self):
        self.assertEqual(
            calculate_damage(10, 3),
            7,
        )
```

可以改成：

```python
from unittest import TestCase


class DamageTest(TestCase):
    def test_damage(self):
        self.assertEqual(
            calculate_damage(10, 3),
            7,
        )
```

如果計算需要 Evennia ORM 或 Typeclass，才升級為：

```python
from evennia.utils.test_resources import EvenniaTestCase


class DamageTest(EvenniaTestCase):
    ...
```

Evennia 官方將 `EvenniaTestCase` 定義為 Django `TestCase`，而且特別說明它會略過 `EvenniaTestMixin` 與預設遊戲物件。

一個實務上的規則是，新增測試時預設從最輕的基底開始；測試真的需要完整遊戲環境時，再改用 `EvenniaTest`。

## 將遊戲邏輯從 Command 分離

如果大量邏輯直接寫在 `Command.func()` 中，所有分支測試都容易變成 command integration test。

例如：

```python
class CmdAttack(Command):
    def func(self):
        attacker = self.caller
        target = ...

        # 大量 combat 邏輯
        ...
```

可以將規則移到獨立函式：

```python
def calculate_damage(
    attack: int,
    defense: int,
    critical: bool = False,
) -> int:
    ...
```

Command 保留 Evennia integration：

```python
class CmdAttack(Command):
    def func(self):
        damage = calculate_damage(
            attack=self.caller.db.attack,
            defense=self.target.db.defense,
        )

        self.target.apply_damage(damage)
```

如此一來，大量 edge cases 可以使用純 Python test：

```python
class DamageTest(TestCase):

    def test_damage(self):
        self.assertEqual(
            calculate_damage(10, 3),
            7,
        )
```

完整 command test 只需要驗證 command parsing、caller／target 整合與輸出訊息。

這種分層通常會同時改善 production code 的可測試性，也會降低測試所需的 Evennia fixture 數量。

## 合併同類的小測試

`EvenniaTestMixin.setUp()` 是每個 test method 都會呼叫的方法。

因此，如果許多測試只有輸入資料不同，把它們全部拆成獨立 method 會反覆付出相同 fixture 成本。

例如：

```python
class DamageTest(EvenniaTest):

    def test_damage_normal(self):
        ...

    def test_damage_zero_defense(self):
        ...

    def test_damage_high_defense(self):
        ...

    def test_damage_critical(self):
        ...
```

如果這些 case 共用相同環境，可以使用 `subTest()`：

```python
class DamageTest(EvenniaTest):

    def test_damage_cases(self):
        cases = [
            (10, 0, 10),
            (10, 3, 7),
            (10, 10, 0),
            (5, 10, 0),
        ]

        for attack, defense, expected in cases:
            with self.subTest(
                attack=attack,
                defense=defense,
            ):
                result = calculate_damage(
                    attack,
                    defense,
                )
                self.assertEqual(
                    result,
                    expected,
                )
```

原先的執行模式大致是：

```text
setUp()
test case A
tearDown()

setUp()
test case B
tearDown()

setUp()
test case C
tearDown()
```

合併後變成：

```text
setUp()

subTest A
subTest B
subTest C

tearDown()
```

這項技巧適合 input／output 型測試。

如果每個 case 都會修改 `self.char1`、`self.room1` 或其他共享 fixture，則必須在 case 開始時回復必要狀態：

```python
for case in cases:
    with self.subTest(case=case):
        self.char1.db.hp = 100
        self.char1.db.mp = 100

        ...
```

如果狀態很難完整回復，維持獨立 test method 比合併更安全。

## 不要把整個 suite 合併成少數大型 class

`subTest()` 可以減少 method-level setup，但 class 數量仍需要保留合理粒度。

Django 的 parallel runner 會把 `TestCase` subclasses 分派給不同 subprocess。當 test class 數量少於 worker 數量時，Django 會降低實際 process 數量。

因此，不建議把數千個案例最後整理成：

```text
TestEverythingCombat
TestEverythingWorld
TestEverythingCommands
```

比較合適的結構是按照功能邊界分 class：

```text
TestMeleeCombat
TestMagicCombat
TestInventory
TestEquipment
TestMovement
TestCrafting
```

每個 class 裡再用 `subTest()` 合併相同 fixture、相同測試目的的資料案例。

這樣可以同時降低 per-method fixture 成本，並保留 parallel runner 可使用的工作單位。

## 使用 `setUpTestData()` 重用 DB fixture

如果多個 test methods 都需要相同 DB 物件，可以使用 Django `TestCase.setUpTestData()`。

Django 會在 class level 建立一次資料，而不是每個 method 都重新建立。官方文件明確指出，相較於 `setUp()`，這種方式可以縮短測試時間。

```python
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTestCase


class InventoryTest(EvenniaTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.room = create.create_object(
            "typeclasses.rooms.Room",
            key="Test Room",
        )

        cls.character = create.create_object(
            "typeclasses.characters.Character",
            key="Tester",
            location=cls.room,
        )

        cls.sword = create.create_object(
            "typeclasses.objects.Object",
            key="Sword",
            location=cls.character,
        )

    def test_has_sword(self):
        ...

    def test_drop_sword(self):
        ...
```

Django 的 `TestCase` 使用 class-level 與 method-level transaction，並會處理 `setUpTestData()` 建立的資料隔離。

這個方法適合建立成本較高、各測試需要相同初始狀態的 Evennia Typeclass。

## Command 測試也可以分級

`EvenniaCommandTest` 繼承 `EvenniaTest`，因此會取得完整 Evennia fixture。

Evennia 提供的 `EvenniaCommandTestMixin.call()` 本身不會啟動完整 cmdhandler，而是直接執行 command lifecycle，包括：

```text
at_pre_cmd()
parse()
func()
at_post_cmd()
```

官方說明這種做法比每次啟動 cmdhandler 更受控。

如果 command test 很多，可以考慮建立專案自己的 lightweight command base。

但不能單純寫成：

```python
class FastCommandTest(
    EvenniaTestCase,
    EvenniaCommandTestMixin,
):
    pass
```

目前 `.call()` 的實作會直接使用 `self.char1`、`self.account`，也會從 `SESSION_HANDLER` 取得 session。

如果要做 lightweight command base，需要自行提供最小 fixture，例如一個 caller、一個必要的 account，以及 mock 或最小化 session。

是否值得做這層 abstraction，要看 command tests 的數量。若專案有數百個 `EvenniaCommandTest` methods，而多數 command 不需要完整 world fixture，這通常值得進一步 benchmark。

## 使用 `--keepdb` 降低 test database 啟動成本

Django 的 `--keepdb` 會保留 test database，因此下一次執行可以略過 create 與 destroy。尚未套用的 migration 仍會在需要時套用。

```sh
evennia test \
    --keepdb \
    mygame.tests
```

Evennia 自己的測試開發文件也使用 `evennia test --keepdb`。

這項優化主要降低 suite-level startup cost。

它無法減少：

```text
每個 test method 的 setUp()
Typeclass 建立
每個 test 的 ORM query
Command fixture 建立
```

這些成本仍要靠前面的測試分層與 fixture 重用處理。

## 使用平行測試

Django 支援：

```sh
evennia test \
    --keepdb \
    --parallel 4 \
    mygame.tests
```

不指定數量時可以使用：

```sh
evennia test \
    --keepdb \
    --parallel \
    mygame.tests
```

Django 會依 CPU core 數決定 process 數。每個 process 都會取得自己的 test database。

不要假設 CPU core 越多就一定越快。

實際 benchmark：

```sh
time evennia test \
    --keepdb \
    --parallel 1 \
    mygame.tests

time evennia test \
    --keepdb \
    --parallel 2 \
    mygame.tests

time evennia test \
    --keepdb \
    --parallel 4 \
    mygame.tests

time evennia test \
    --keepdb \
    --parallel 8 \
    mygame.tests
```

例如測得：

```text
parallel 1     120 s
parallel 2      68 s
parallel 4      40 s
parallel 8      38 s
parallel 16     45 s
```

那麼 4 或 8 workers 會是較合理的固定值。

process startup、database workload 與記憶體壓力都會影響實際結果，所以這個數字應由專案本身的 benchmark 決定。

## Mock 延遲與外部 I/O

Unit test 不應等待真正的 timer。

Evennia 提供：

```python
mockdelay
mockdeferLater
```

這兩個 helper 可以處理 delayed callback。

同樣的原則可以套用到：

```text
HTTP request
LLM API
email
filesystem
object storage
external process
background worker
```

例如：

```python
from unittest.mock import patch


@patch("world.ai.client.request")
def test_ai_action(self, mock_request):
    mock_request.return_value = ...

    ...
```

真正需要驗證外部服務時，再把測試放到 integration test lane。

Django 也提供 `InMemoryStorage`，讓測試中的 media file 不必實際寫入 disk。

## 測試環境使用較快的 password hasher

Django 預設 password hasher 刻意設計得較慢。如果測試頻繁建立 account 或呼叫 `set_password()`，hashing 可能累積成可觀成本。

Django 官方建議在測試專用 settings 中使用較快的 hasher，例如：

```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
```

這項設定只能使用在測試環境。

如果 fixtures 中存在其他 hashing algorithm，Django 文件要求對應的 hasher 仍須列在 `PASSWORD_HASHERS`。

## 將 fast tests 與 integration tests 分流

Django 支援 test tags。

例如：

```python
from django.test import tag


@tag("integration")
class FullCombatFlowTest(EvenniaCommandTest):
    ...
```

日常開發可以：

```sh
evennia test \
    --keepdb \
    --exclude-tag=integration \
    mygame.tests
```

Django test runner 原生支援 `--tag` 與 `--exclude-tag`。

專案可以形成兩條測試路徑。

快速回饋路徑包含 pure Python tests、lightweight DB tests 與必要的 command tests。

完整驗證路徑再加入 integration tests、完整 game flow 與外部系統測試。

這樣改善的是開發者每次修改後等待結果的時間，而不只是完整 CI suite 的總秒數。

## 監控 ORM query 數量

有些 Evennia 測試慢的來源是 ORM query 數量。

例如：

```python
for obj in character.contents:
    weight = obj.attributes.get("weight")
```

如果底層 handler 或 Attribute 存取產生額外 query，測試時間會隨物件數增加。

Django 提供 `assertNumQueries()`，可以對重要操作設定 query regression test。

```python
with self.assertNumQueries(5):
    result = calculate_inventory_weight(
        self.character
    )
```

這類優化同時會反映到遊戲執行期間的 database workload，因此值得對熱門 execution path 使用。

## Profile Python import 時間

如果執行單一幾毫秒的測試仍需要數秒，瓶頸可能出現在測試開始之前。

Python 可以透過 `PYTHONPROFILEIMPORTTIME` 顯示每個 module 的 import 時間。

```sh
PYTHONPROFILEIMPORTTIME=1 \
evennia test \
    world.tests.test_combat
```

需要注意 module-level 的 expensive work，例如：

```python
DATA = load_large_json()
TABLE = build_large_table()
```

可以視用途改成 lazy loading：

```python
from functools import cache


@cache
def get_table():
    return build_large_table()
```

更需要避免 import-time DB query。

Django 明確警告，module import 與 `AppConfig.ready()` 階段的 database query 可能發生在 test database 建立之前，甚至讓 production database 的資料進入測試。

## 不要移除 Evennia 的 `flush_cache()`

Profile 時可能會看到 Evennia 每個 test 都執行：

```python
flush_cache()
```

這不適合作為優化目標。

Evennia 的 `EvenniaTestCase.tearDown()` 會呼叫 `flush_cache()`。官方原始碼也明確警告，自訂 `tearDown()` 如果沒有執行這項清理，會產生 flaky 與 order-dependent tests。

因此：

```python
class MyTest(EvenniaTestCase):

    def tearDown(self):
        cleanup_something()
```

應改成：

```python
class MyTest(EvenniaTestCase):

    def tearDown(self):
        cleanup_something()
        super().tearDown()
```

同樣地，自訂 `setUp()` 時也應呼叫：

```python
def setUp(self):
    super().setUp()
    ...
```

Evennia 自己的 `EvenniaTestMixin.tearDown()` 對漏掉 `super().setUp()` 的情況也有明確錯誤訊息。

## `--keepdb` 或 `--parallel` 造成失敗時

如果原本能通過的測試加入這兩個選項後開始失敗，應把它視為 test isolation 問題來診斷。

可以先跑四種組合：

```sh
# A
evennia test \
    --parallel 1 \
    mygame.tests

# B
evennia test \
    --parallel 1 \
    --keepdb \
    mygame.tests

# C
evennia test \
    --parallel 4 \
    mygame.tests

# D
evennia test \
    --parallel 4 \
    --keepdb \
    mygame.tests
```

結果可以用下面方式判讀：

| 結果 | 優先調查方向 |
|---|---|
| A 通過、B 失敗、C 通過 | `keepdb`、transaction 或殘留 DB state |
| A 通過、B 通過、C 失敗 | shared resource 或 race condition |
| A 通過、B 與 C 都失敗 | global state 或 test isolation |
| A 偶爾就失敗 | order dependency 或 flaky test |

### `--parallel` 失敗時，不要預設是 test DB 互相污染

Django parallel runner 會給每個 process 各自的 database。

因此：

```text
--parallel 1    PASS
--parallel 4    FAIL
```

優先調查 DB 以外的共享資源：

```text
filesystem
Redis
Django cache
Celery / RQ
固定 TCP port
Unix socket
lock file
search index
外部服務
```

Django 文件特別提醒，不同 test classes 不應共用相同 filesystem resource，並建議各自建立 temporary directory。

例如不要：

```python
TEST_FILE = "/tmp/result.json"
```

改成：

```python
import tempfile
from pathlib import Path


def test_export(self):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "result.json"
        ...
```

### Cache 也會造成測試互相干擾

Django 的 test database 有隔離機制，但 cache 沒有獨立的「test cache」，而且 cache 不會在每個 test 後自動清空。Django 官方文件直接記載這項行為。

如果所有 parallel workers 都連同一個 Redis：

```text
worker 1 ─┐
worker 2 ─┼─> Redis DB 0
worker 3 ─┤
worker 4 ─┘
```

使用固定 key：

```python
cache.set(
    "player-state",
    value,
)
```

就可能互相覆寫。

測試環境可以使用 process-local cache，或為 cache key 加入 test／worker namespace。

### `--keepdb` 失敗時檢查交易隔離

Django `TestCase` 會把 test code 包在 database transaction 中，測試結束時 rollback 到原始狀態。

因此正常的 `EvenniaTestCase` 與 `EvenniaTest` 不應因為 `--keepdb` 而讓普通 test data 一直累積。

如果：

```text
第一次 --keepdb    PASS
第二次 --keepdb    FAIL
```

就值得調查資料是否逃出了 transaction boundary。

常見來源包括 background thread、額外 database connection、subprocess、background task，以及不合適的 test base class。

例如這種測試如果會操作 Django DB：

```python
import unittest


class MyTest(unittest.TestCase):
    ...
```

應考慮改成：

```python
class MyTest(EvenniaTestCase):
    ...
```

Django 的 `TestCase` 會使用 transaction rollback 回復 database。`TransactionTestCase` 則會以 table truncation 等方式回復 DB，並允許真正觀察 commit／rollback 行為。

如果測試本身就是驗證 transaction semantics，才應使用 `TransactionTestCase`。

### 不要依賴固定 primary key

避免：

```python
obj = ObjectDB.objects.get(id=3)
```

以及：

```python
self.assertEqual(
    obj.id,
    5,
)
```

test database sequence 不應被視為測試 API。

建立物件後直接保留 reference：

```python
self.sword = create_object(...)
```

後續使用：

```python
self.assertEqual(
    result,
    self.sword,
)
```

這也會降低 `--keepdb`、migration 或 fixture 順序改變後的脆弱度。

## 使用 `--shuffle` 找 order dependency

Django 的 `--shuffle` 會改變測試順序，而且 seed 可以重現。它就是用來發現 isolation 問題的工具之一。

```sh
evennia test \
    --parallel 1 \
    --shuffle \
    mygame.tests
```

如果輸出：

```text
Using shuffle seed: 381927184
```

可以用相同 seed 重跑：

```sh
evennia test \
    --parallel 1 \
    --shuffle 381927184 \
    mygame.tests
```

還可以使用：

```sh
evennia test \
    --parallel 1 \
    --reverse \
    mygame.tests
```

Django 的 `--reverse` 也明確用於協助找出沒有妥善隔離的測試。

如果正常順序通過，但 reverse 或 shuffle 後失敗，應優先調查前一個 test 留下的 DB、cache、global state、filesystem 或 mock state。

## 重複執行同一個 `--keepdb` suite

另一個簡單的 isolation check 是連跑多次：

```sh
evennia test \
    --keepdb \
    mygame.tests.test_inventory \
&& \
evennia test \
    --keepdb \
    mygame.tests.test_inventory
```

理想情況下，同一套測試不應因為前一次執行而改變結果。

如果第一次通過、第二次失敗，可以把調查範圍集中到持久化狀態。

必要時先執行一次不帶 `--keepdb` 的測試，讓 test database 重新建立，再觀察後續 `--keepdb` 執行。

Django 說明 `--keepdb` 會保留既有 test database，並在後續執行繼續使用。

## 檢查全域 mutable state

Database 之外也可能存在 Python process 內的共享狀態：

```python
CURRENT_CHARACTER = None
COMBAT_STATE = {}
ACTIVE_SESSIONS = []
```

如果 test 修改這些物件而沒有復原：

```python
COMBAT_STATE["combat"] = ...
```

測試就可能依賴 execution order。

必要時在 test lifecycle 中清理：

```python
def setUp(self):
    super().setUp()
    COMBAT_STATE.clear()


def tearDown(self):
    COMBAT_STATE.clear()
    super().tearDown()
```

更好的設計是把 mutable state 放進 instance 或明確的 state object，降低 module global 對測試的影響。

## 無法平行的測試可以序列化

有些測試確實必須使用 global resource，例如不能複製的外部服務或固定 resource。

Django 提供 `SerializeMixin`，讓指定 test classes 不同時執行。官方 parallel testing 文件也將它列為無法平行化測試的處理方式。

這比較適合作為最後的相容措施。

如果資源可以改成 per-test temporary resource，通常仍值得優先做隔離，因為如此仍能保留 parallelism。

## 不要用每個 test `flush` database 解決污染

遇到 isolation 問題時，不建議在每個 test 中執行：

```python
call_command("flush")
```

Django `TestCase` 原本就會使用 transaction rollback 回復 database。

如果必須額外 flush 才能通過，通常代表還有 transaction 外部狀態沒有被處理。

每個 test flush DB 也會抵銷大量測試效能改善。

比較合理的目標是：

```text
Django transaction isolation
        +
Evennia flush_cache()
        +
external resource isolation
```

## 建議的優化順序

現有 Evennia 專案可以按照以下順序處理。

```text
量測 --timing / --durations
          │
          ▼
縮小日常執行範圍
          │
          ▼
EvenniaTest
    ↓
能否改成 EvenniaTestCase？
          │
          ▼
domain logic
    ↓
能否改成 pure Python test？
          │
          ▼
重複 DB fixture
    ↓
setUpTestData()
          │
          ▼
大量同型 cases
    ↓
subTest()
          │
          ▼
Mock timer / I/O / external services
          │
          ▼
--keepdb
          │
          ▼
benchmark --parallel 2 / 4 / 8
          │
          ▼
fast / integration test tags
          │
          ▼
查 ORM query 與 import startup
```

如果加入 `--keepdb` 或 `--parallel` 後出現 failure，暫時停止追求速度，先用 `--shuffle`、`--reverse` 與前面的 2 × 2 組合找出 isolation 問題。

## 一組實用的日常命令

本專案所有指令都經由 `uv run --locked` 執行，測試 settings 守衛要求 `MUD_TEST_SETTINGS=1` 與 `--settings test_settings.py`。以下範例直接套用本專案路徑。

開發中的快速回饋：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --keepdb \
    --failfast \
    world.rules.tests.test_combat_session
```

排除 integration tests：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --keepdb \
    --exclude-tag=integration \
    world
```

完整本機測試（平行執行，開發中預設，24-core 機器實測 ~45s；最終 handoff 證據請改為下方序列指令）：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --noinput \
    --parallel 16 \
    commands server typeclasses world web.webclient
```

完整本機測試（序列執行，最終 handoff 證據標準）：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --keepdb \
    commands server typeclasses world web.webclient
```

定期找慢測試：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --keepdb \
    --timing \
    --durations 30 \
    commands server typeclasses world web.webclient
```

檢查 order dependency：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --parallel 1 \
    --shuffle \
    commands server typeclasses world web.webclient
```

檢查 parallel isolation（以日常開發 profile 執行）：

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test \
    --settings test_settings.py \
    --keepdb \
    --parallel 16 \
    commands server typeclasses world web.webclient
```

## 最後的判斷原則

Evennia 測試的主要優化空間通常存在於 fixture 粒度。

如果一個測試只需要驗證純函式，就不要建立完整遊戲世界。如果只需要一個 Character，就不要支付兩組 Account、Room、Object、Character、Script 與 Session 的建立成本。Evennia 目前的 `EvenniaTestMixin.setUp()` 確實會建立這整套預設環境。

`--keepdb` 處理的是 test database 的 create／destroy 成本。`--parallel` 利用多核心縮短整體執行時間。`setUpTestData()` 與 `subTest()` 則降低重複 fixture 成本。這些方法處理的是不同層級，可以一起使用。

當優化造成原本通過的測試失敗時，失敗本身也是有價值的訊號。Django 提供 `--shuffle`、`--reverse` 與獨立 parallel databases，就是為了讓測試隔離問題更容易暴露與定位。

最終理想狀態是讓大部分測試停留在 pure Python 或 lightweight DB 層，保留較少量的完整 Evennia integration tests。這樣可以縮短本機 feedback cycle，也不必用降低測試隔離程度來換取速度。