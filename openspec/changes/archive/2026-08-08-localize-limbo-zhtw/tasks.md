# Tasks: localize-limbo-zhtw

## 1. Starting room identity and sync

- [x] 1.1 Add `LIMBO_KEY` constant, the authored zh-tw description constant, and `sync_limbo()` to `world/maps/bootstrap.py`: locate the canonical room by `LIMBO_KEY`; when absent, rename a legacy `"Limbo"`-keyed room in place to `LIMBO_KEY`; when both exist, sync/bridge the canonical room, leave the legacy room untouched, and `log_warn`; re-affirm the `limbo` alias and description on every call; `log_warn` and return (never raise) when no qualifying room exists.
- [x] 1.2 Wire `sync_limbo()` into `server/conf/at_server_startstop.py::at_server_start()` immediately before `sync_grid()`.
- [x] 1.3 Update `world/maps/bootstrap.py::sync_grid()` to look up the starting room via `LIMBO_KEY` (never a `"Limbo"` literal), and change the bridge aliases: `EXIT_TO_CITY` to zh-tw (e.g. `["王都", "城門"]`), `EXIT_TO_LIMBO` to zh-tw (e.g. `["回虛境"]`). Add an in-place reconciliation step so a pre-existing bridge exit (matched by location+destination) has its key/aliases rewritten to the authored zh-tw values on every sync.
- [x] 1.4 Add `world/maps/tests/test_limbo_room.py` (or extend `test_bootstrap.py`): covers the `limbo-room` requirements — zh-tw key/alias/description after sync, legacy-key rename in place, idempotency, dual-room precedence with warning, missing-room degradation, zh-tw bridge aliases, and pre-existing English-alias exits reconciled in place without duplicates. Annotate with `covers_requirement` using canonical IDs from `uv run --locked python -m tools.spec_traceability list`.
- [x] 1.5 Add a startup-integration test proving `at_server_start()` calls `sync_limbo()` before `sync_grid()` (legacy `"Limbo"` renamed in place and then bridged), so a reordered or missing call fails the suite.
- [x] 1.6 Rename the room-key fixtures in map/bootstrap-adjacent tests (`world/maps/tests/test_bootstrap.py`, `test_movement_roundtrip.py`, `test_city_wilderness_roundtrip.py`, `test_city_movement_cost.py`, `test_city_walkthrough.py`, `test_service_interiors.py`, `test_wilderness_population.py`) from `key="Limbo"` to the `LIMBO_KEY` constant (or `"虛境"` where the constant would be overkill), and fix any bridge traversal that typed the English aliases (`leave`, `limbo`, `south gate`).
- [x] 1.7 Rename the generic "Limbo as an arbitrary room" fixtures in other packages (`world/quests/tests/*`, `world/rules/tests/*`, `typeclasses/tests/test_exits.py`, `web/webclient/*/tests/*`) to the zh-tw key so no `key="Limbo"` remains in the repository; update `web/tests/browser/seed.py`'s Limbo reference.

## 2. Shared appearance layer

- [x] 2.1 Localize the appearance hooks in `typeclasses/objects.py::ObjectParent`: zh-tw `get_display_exits` (「出口」), contents/characters section headers, and default description (「你沒有看到什麼特別的。」), plus any other English frame strings in `return_appearance` paths. Keep the room header/desc hooks rendering zh-tw.
- [x] 2.2 Add appearance-layer tests: text look in a room with an exit shows the zh-tw frame with no `Exits:`/`Characters:`/`You see` strings; the webclient `explore.look` action (`actor.at_look(target)`) produces the identical zh-tw appearance (assert through the webclient action path, not just the command wrapper); the `PlayerCharacter.at_look` onboarding seam still fires. Annotate with `covers_requirement` for the `localized-appearance` capability.

## 3. Localized default command surface

- [x] 3.1 Create `commands/localized.py` with zh-tw wrapper classes retaining the **full** upstream alias set of each: 看 (CmdLook), 說明 (CmdHelp), 說 (CmdSay), 動作 (CmdPose), 拿 (CmdGet), 丟 (CmdDrop), 給 (CmdGive), 回家 (CmdHome), 耳語 (CmdWhisper), 暱稱 (CmdNick), 設定描述 (CmdSetDesc), 登出 (CmdQuit), 在線 (CmdWho), 離開角色 (CmdOOC), 進入世界 (CmdIC), 傳訊 (CmdPage), 密碼 (CmdPassword), 選項 (CmdOption), 連線 (CmdSessions), 色彩 (CmdColor), 樣式 (CmdStyle), 降權 (CmdQuell). Each carries a zh-tw docstring (help text), inherits the upstream `locks`, branches on `self.cmdstring` (not the key) so behavioral aliases keep upstream semantics (`doing` narrower listing, `unpuppet`, `grab`, `emote`, `tell`, …), and emits zh-tw output.
- [x] 3.2 Implement 看 as a thin delegation (target resolution + `caller.at_look(target)` + `type="look"` emit, zh-tw fallback strings) so it shares the localized appearance layer; add a `character_creation.py` swap of its `help`/`quit` seams to the 說明/登出 wrappers.
- [x] 3.3 Implement 說明 by subclassing `CmdHelp` and overriding the presentation hooks (index listing, entry view, category display mapping General→一般, Combat→戰鬥, Guild→公會, Economy→經濟, Admin→管理員, no-result string), keeping upstream topic fetching, permission filtering, subtopics, and webclient popup behavior.
- [x] 3.4 Add a project-owned XYZGrid cmdset (in `commands/`): native `CmdXYZTeleport`/`CmdXYZOpen` plus wrappers 前往 (CmdGoto) and 地圖 (CmdMap) with zh-tw surrounding output (ASCII grid art unchanged); widen the auto-walk check so both 「前往」 and the `goto` alias walk while `path` stays path-only. Mount this cmdset in `CharacterCmdSet` in place of the contrib `XYZGridCmdSet`.
- [x] 3.5 Mount the wrappers in `commands/default_cmdsets.py`: after `super().at_cmdset_creation()`, `self.remove(...)` the stock localized commands (look, help, say, pose, get, drop, give, home, whisper, nick, setdesc, quit, who, ooc, ic, page, password, option, sessions, color, style, quell) from `CharacterCmdSet`/`AccountCmdSet` and `self.add(...)` the wrappers, so no English-keyed variant remains in the merged sets.
- [x] 3.6 Add command tests: a contract test that the merged player cmdsets expose no stock localized default class; per-command output tests asserting zh-tw strings (說 echo, 拿/丟/給 messages, 回家, 登出, 在線, 離開角色, 進入世界, 傳訊, 密碼, 選項, 連線, 色彩, 樣式, 降權, 耳語, 暱稱, 設定描述, 地圖, 前往); an integration test walking via 「前往」 and via the `goto` alias proving auto-move, and `path` proving no-move; keep the onboarding look-beat integration test green.

## 4. Prose and help entries

- [x] 4.1 Update `world/onboarding/scenes.py::LOOK_BEAT.prose` to prompt 「看」 (「先用「看」看看四周……」) and update any test asserting the old wording.
- [x] 4.2 Update `world/help_entries.py::新手引導` text to name the zh-tw key （看） for the look step; `talk`/`guild register`/`guild turnin` stay English-primary.

## 5. Docs and contract test

- [x] 5.1 Rewrite `tests/test_command_docs.py`: add the localized wrappers to `EXPECTED_COMMANDS` with zh-tw syntax/context rows; re-base the default-index-table assertions to "retained defaults" = upstream default key sets minus the localized set, plus a localized index table equal to the mounted wrapper key set; re-base the XYZGrid enumeration on the project-owned mounted XYZGrid cmdset; update the `character` 情境 row to 「說明」與「登出」; keep every `covers_requirement` annotation and the `docsify_slug` pin tests (add slugs for the new zh-tw keys).
- [x] 5.2 Update `docs/game/command-reference.md`: canonical `### <zh-tw key>` entries for all localized wrappers (指令/別名 with full alias sets/語法/情境/說明), a localized-commands index table, the retained-defaults index tables (minus the localized set), the XYZGrid section covering `@teleport`/`@open` plus 前往/地圖, and the `character` entry wording.
- [x] 5.3 Update `docs/game/commands.md`: add the localized commands with correct docsify anchors (看, 說明, 說, 動作, 拿, 丟, 給, 回家, 耳語, 暱稱, 設定描述, 登出, 在線, 離開角色, 進入世界, 傳訊, 密碼, 選項, 連線, 色彩, 樣式, 降權, 地圖, 前往) under the existing categories.
- [x] 5.4 Run `uv run --locked python -m unittest tests.test_command_docs` (top-level discovery) and `uv run --locked python -m tools.spec_traceability check`; fix drift until both are clean.

## 6. Specs and verification

- [x] 6.1 Validate the change artifacts: `openspec validate localize-limbo-zhtw --strict`.
- [x] 6.2 Run the affected test domains: `uv run --locked evennia test --settings test_settings.py --keepdb world.maps world.rules world.quests commands typeclasses web.webclient.actions` and the managed browser suite (`uv run --locked -m unittest discover -s web/tests/browser -t .`); run the full Evennia suite and top-level discovery once before handoff.
- [x] 6.3 `uv run --locked python -m compileall -q world typeclasses commands server` and `git diff --check`.
- [x] 6.4 Run the required traceability entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's `verify --evidence` mode before handoff.
