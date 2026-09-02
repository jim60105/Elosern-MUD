# add-persona-edit-surface — Tasks

順序：服務 → action/registry → panel/protocol → Vue drawer → 命令家族 → 文件／登記。每組做完先跑該組 focused 測試再勾選。

## 1. 寫入服務（world/rules/persona_edit.py）

- [ ] 1.1 新增 `PERSONA_EDITABLE_FIELDS = frozenset({"background","personality","life_story","habit"})` 與 `update_persona_field(character, field, text)`（欄位白名單驗證 → trim → 空值移鍵 no-op → 600 上限拒寫 → 無 record 建 import-card 六鍵 → 僅動該鍵、其餘鍵含未知鍵原樣保留）；`update_background` 改薄包裝；模組 docstring 單寫者宣言改述四鍵白名單。
- [ ] 1.2 擴充 `world/rules/tests/test_persona_edit.py`：四鍵 × (設定、清除、無 record 建卡、超界拒寫、未知鍵保留、wrapper 等值)；把舊 background  scenario 的 `covers_requirement` 遷移到 `persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields` 族 ID（`uv run --locked python -m tools.spec_traceability list` 取 canonical ID）。
- [ ] 1.3 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_persona_edit`。

## 2. Action 與 registry（web/webclient）

- [ ] 2.1 新增模組 `web/webclient/actions/character_actions.py`：`character.persona.update` 驗證器（恰 `{field, text}`、四鍵白名單、text null 或 trim 後 1..600）與 adapter（本人 puppet、已啟動、探索模式；直呼 `update_persona_field`；成功 `persona_updated`＋繁中訊息＋affected `character`；非白名單／超界穩定拒絕；清除未設定欄 no-op success）。
- [ ] 2.2 `web/webclient/actions/registry.py`：註冊新 action；registry 測試的恰鍵清單同步。
- [ ] 2.3 整合測試：happy path 刷新 panel、`field: "identity"` 拒絕、超界拒絕、no-op 清除、pending／非本人拒絕。掛 `covers_requirement`（`persona-editing::the-character-persona-update-action-edits-one-persona-field` 族）。
- [ ] 2.4 Focused：`... evennia test --settings test_settings.py --keepdb web.webclient.actions`。

## 3. Panel 與 wire（v6 → v7）

- [ ] 3.1 `web/webclient/presentation/character.py`：`CHARACTER_SCHEMA_VERSION` 6 → 7；`_validate_persona` 與 presenter 改恰四鍵 `{background, personality, life_story, habit}`（非字串→None、純空白→None、超界 fail-closed；結構鍵不上線）。
- [ ] 3.2 `web/static/webclient/js/elosern/protocol.js`：character v7 鏡像（persona 四鍵）＋ `character.persona.update` payload 鏡像＋行動清單常量同步；JS parity 測試更新。跑 `node --test web/static/webclient/js/tests/*.test.js`。
- [ ] 3.3 更新 `web/webclient/presentation/tests/test_character_panel.py`：四鍵渲染、null 化、結構鍵排除、唯讀不變、unavailable form 版本。

## 4. Vue drawer（CharacterStatusDrawer.vue）

- [ ] 4.1 persona 區四段渲染（個性／生平／習慣／背景），null → 「未設定」佔位；每段編輯 affordance 送恰一 `character.persona.update`，提交後依刷新 panel 更新。
- [ ] 4.2 Vitest：四段＋佔位、編輯提交恰一 action、清除送 null。`npm test`；`npm run build`、`npm run build-storybook`、`npm run showcase-coverage`（如清冊受影響則同步）。

## 5. Telnet 命令家族（commands/）

- [ ] 5.1 `commands/background.py`：抽 `CmdPersonaFieldBase`（三段式：無參顯示現值＋用法、有參設定、空白清除；經 `update_persona_field`；欄位鍵為類別屬性）並讓 `CmdBackground` 改為 `background` 子類（鍵／別名／行為不變）；新模組 `commands/persona.py` 定義 `設定個性`（`個性`）、`設定生平`（`生平`、`背景故事`）、`設定習慣`（`習慣`）三個子類；`commands/default_cmdsets.py` 保留 `CmdBackground` 掛載並新增三條。
- [ ] 5.2 `EvenniaCommandTest` 三新命令 × 四路徑（顯示、設定、清除、超界）＋ `commands/tests/test_background.py` 既有 `設定背景` 案作為基類重構的回歸鎖。掛 `covers_requirement`（`persona-editing::the-persona-command-family-mirrors-the-action-on-telnet` 族）。

## 6. 文件、登記與收尾

- [ ] 6.1 `docs/game/commands.md` 與 `docs/game/command-reference.md`：persona 家族四條目（語法含顯示／設定／清除、context 為活躍角色）＋總覽分類表；`tests/test_command_docs.py` curated manifest 同步，跑 `tests.test_command_docs`。
- [ ] 6.2 新測試模組（`commands/tests/test_persona_commands.py` 等）註冊 `.github/evennia-shards.json`；跑 `tests.test_evennia_test_optimization_contract`。
- [ ] 6.3 `uv run --locked python -m tools.spec_traceability check`（含舊 background 要求 ID 已遷移、無孤兒錨點）；`openspec validate add-persona-edit-surface --strict`。
- [ ] 6.4 終局：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 commands server typeclasses world web.webclient` 一次；可用環境下瀏覽器 smoke（drawer 四段 → 編輯一欄 → 刷新可見）。
