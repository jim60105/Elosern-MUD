# prefill-telnet-concept-from-proposal

## Why

Telnet `character concept` 流在提案送達後，仍固定用互動提示強收名字與兩個年齡、且把提案的 `background`／`affinity_elements` 完全丟棄——`_complete_interactively` 組的 `CharacterCreationRequest` 不帶這兩欄。前端已能從提案暫態填入五欄（`retool-concept-fill-navigation`），Telnet 這條平行 surface 卻落後：輸入「貓人少女」得到的角色在 Telnet 下沒有名字、沒有背景、沒有親和，且年齡仍需手打。設計源頭：`docs/superpowers/specs/2026-09-03-concept-proposal-expansion-toast-feedback-design.md` §5.5。

## What Changes

- `_complete_interactively` 改為以提案值為提示預設：名字／實際年齡／外表年齡的提示文案顯示提案值，玩家直接按 Enter 即採納預設、輸入任何非空文字即覆寫；`cancel` 語意不變。提案缺席該欄時提示退回無預設的強制輸入（維持現行行為）。
- 提案送達後 `CharacterCreationRequest` 帶上 `background=proposal.background` 與 `affinity_elements=proposal.affinity_elements`（生成層已正規化，必過 `preflight_character_creation` 的成年閘、種族上限與 elf 清空規則）；缺席欄位維持 `None`。
- `_proposal_summary` 增列顯示名字、背景、年齡、親和，讓玩家在補欄前先讀到提案將要採納的值。
- 命令鍵、別名、語法不變；命令文件（`docs/game/commands.md`、`docs/game/command-reference.md`）的 concept 條目更新為「提案預填、Enter 採納或輸入覆寫」。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `character-creation-ux`: 「The creation surface offers a concept-driven custom entry」一條改寫——名字與年齡為「提案預填＋Enter 採納／輸入覆寫」而非強制輸入；請求承載提案的背景與親和。
- `generative-character-concept`: 「The character concept command runs a guarded generative proposal pipeline」一條改寫——命令以提案的正規化名字與年齡為預設值收集、並在啟動請求中攜帶提案背景與親和（成年閘仍是最終權威）。

## Impact

- `commands/character_creation.py`（`_complete_interactively`、`_proposal_summary`）。
- 測試：`commands/tests/test_character_creation.py`、`test_command_branch_behaviour.py` 的 concept 分支案（預設採納、輸入覆寫、缺席退回、背景／親和進入請求、成年閘對「Enter 採納一個被夾到 18 的年齡」仍通過且不可繞過）；`docs/game/commands.md` 與 `docs/game/command-reference.md` 同步、`tests/test_command_docs.py` 綠。
- 無後端相容層。與 `retool-concept-fill-navigation`（Vue）檔案不相交，可平行；共享前置僅 `extend-concept-proposal-fields`（提案先有五欄）。
