# prefill-telnet-concept-from-proposal — Tasks

實作順序即分組順序：摘要與提示預填 → 請求組裝 → 測試 → 文件與登記。每組做完先跑該組 focused 測試再勾選；不跑 CI shard 指令。前置：`extend-concept-proposal-fields` 已合併。

## 1. 命令流（commands/character_creation.py）

- [ ] 1.1 `_proposal_summary`：persona 段落前增「姓名／實際年齡／外表年齡／背景／元素親和」行；缺席欄顯示「（未提案）」類措辭。
- [ ] 1.2 `_complete_interactively`：三道提示（姓名／實際年齡／外表年齡）在提案有值時改文案為「（預設：X，按 Enter 採納；輸入 cancel 取消）」；空輸入→採納預設、非空→覆寫（姓名 strip 後判空；年齡空→預設，非空→`_integer` 解析，失敗走既有錯誤路徑）；提案缺席該欄→強制輸入文案＋姓名空回覆就地重問迴圈（strip 後判空；現行無此迴圈，屬本變更新增——現行為空字串直送 preflight 整段中止）；`cancel` 路徑三處不動。
- [ ] 1.3 同檔：`_activate_creation` 的 `CharacterCreationRequest` 增 `background=proposal.background`、`affinity_elements=proposal.affinity_elements`；docstring 更新（提案＝暫態填入器語意，缺席＝None/中性）。

## 2. 測試（commands/tests）

- [ ] 2.1 `commands/tests/test_character_creation.py`（或既有 concept 測試所在模組）：預設採納（三道提示全空 → 提案值進入啟動）、輸入覆寫（改姓名）、缺席退回強制輸入（提案無 display_name → 空輸入就地重問、非空姓名繼續、cancel 中止）、玩家覆寫 17 歲仍被成年閘拒、夾到 18 的預設年齡 Enter 採納後啟動成功、背景與親和進入請求（斷言 persona record 含 background、角色 `affinity_elements` 為提案集；affinity=None → 中性）。
- [ ] 2.2 `commands/tests/test_command_branch_behaviour.py` 的 concept 分支案同步（prompt 文案斷言遷到新格式）。
- [ ] 2.3 Focused：`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands`。掛 `covers_requirement` 於 `character-creation-ux` 與 `generative-character-concept` 的兩條改寫條目 canonical ID（先 `uv run --locked python -m tools.spec_traceability list`）。

## 3. 文件與登記

- [ ] 3.1 `docs/game/commands.md` 與 `docs/game/command-reference.md`：`character concept` 條目更新為「提案預填、Enter 採納／輸入覆寫、背景與親和自動採納」（命令鍵／別名／語法不動）；`tests.test_command_docs` 綠。
- [ ] 3.2 `uv run --locked python -m tools.spec_traceability check`；`openspec validate prefill-telnet-concept-from-proposal --strict`；`uv run --locked python -m tools.observability_lint check`。
