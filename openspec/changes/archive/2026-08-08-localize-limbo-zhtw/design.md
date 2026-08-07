# Design: Localize the starting Limbo room, the shared appearance layer, and the player-facing default command surface to zh-tw

## Context

Evennia 6.1.0's first-boot initial setup (`evennia/server/initial_setup.py::create_objects`)
creates the starting room keyed `_("Limbo")` with the upstream English `LIMBO_DESC` ("Welcome to
your new Evennia-based game!…"). This project's `server/conf/at_initial_setup.py` is empty, so that
English room is never re-authored. The project's own startup syncs (`world/lore/sync.py::sync_all`,
`world/maps/bootstrap.py::sync_grid/sync_service_interiors/sync_wilderness`) already run
idempotently on every server start and, for interiors, rewrite authored descriptions in place — the
natural home for Limbo convergence is that same bootstrap.

Everything a player sees or types in the starting room currently falls through to Evennia's English
default surface in three layers:

1. **Appearance layer** — `DefaultObject.return_appearance()` and its hooks
   (`get_display_exits` builds `"Exits: …"` at `evennia/objects/objects.py:1800`,
   `default_description` is `_("You see nothing special.")`). This layer is reached both by the
   text `look` command and — critically — by the webclient's explore-look action
   (`web/webclient/actions/exploration_actions.py:327` calls `actor.at_look(target)` directly,
   bypassing any command wrapper).
2. **Command layer** — the stock defaults on the merged player cmdsets (`look`, `help`, `say`,
   `pose`, `get`, `drop`, `give`, `home`, `whisper`, `nick`, `setdesc`, `quit`, `who`, `ooc`, `ic`,
   `page`, `password`, `option`, `sessions`, `color`, `style`, `quell`) plus the XYZGrid contrib
   (`goto`, `map`, `@teleport`, `@open`). `CmdGoto.func()` decides auto-walk by
   `self.cmdname == "goto"` (`xyzgrid/commands.py:368`), so key renames alone break semantics.
3. **Prose layer** — the onboarding guard's `look` prompt (`world/onboarding/scenes.py`) and the
   新手引導 help entry (`world/help_entries.py`) name English command keys.

The project's own commands (`talk`, `engage`, `guild …`, `inventory`, `character`) already carry
zh-tw aliases and zh-tw output, and the `game-command-docs` contract test pins the docs to the
mounted registry. The `look` beat in onboarding completes through a `PlayerCharacter.at_look` seam
(command-agnostic), so localizing the command keys does not touch that mechanism.

Constraints: player-facing prose is Traditional Chinese; the single-writer invariant is untouched
(only presentation and read-only sync change); no formatter/type-checker is configured; every main
spec requirement needs `covers_requirement` test coverage; `docs/game/*` and
`tests/test_command_docs.py` must move together with any command surface change; the project has no
released users, so no migrations are required.

## Goals / Non-Goals

**Goals:**
- The starting room is a zh-tw, story-fitting Elosern location: zh-tw object key (draft 「虛境」,
  alias `limbo` retained), zh-tw description, zh-tw bridge exits, converged idempotently on every
  server start for existing developer databases, with a defined precedence when a legacy `"Limbo"`
  room coexists.
- The shared appearance layer renders zh-tw frames identically for the text `看` command, the
  `at_look` seam, and the webclient `explore.look` action.
- Every default Evennia command a normal player can invoke is localized: zh-tw primary key, the
  class's **full** alias set retained, zh-tw help text, zh-tw output, and upstream `cmdstring`
  branching preserved. No English-keyed or English-output variant remains reachable in normal play.
- The XYZGrid `goto`/`map` are replaced by zh-tw wrappers through a project-owned cmdset, with
  auto-walk semantics intact for both 「前往」 and the `goto` alias.
- Onboarding prose and the 新手引導 help entry name the zh-tw command keys.
- Docs, contract test, and spec deltas follow the surface exactly.

**Non-Goals:**
- Builder/admin/system commands (all `@*`, `access`, `perm`, `sethelp`, `emit`, `force`, `wall`,
  `ban`, `boot`, `unban`, `unlink`, `batchcode`, `batchcommands`, `charcreate`/`chardelete`,
  `@channel`/channel links, `ircstatus`, `@about`, `@time`, `@server`, `@service`, `@scripts`,
  `@tickers`, `@tasks`, `@examine`, `@py`, `@objects`, `@accounts`): retained as English defaults
  and enumerated in the reference index tables as the retained set. These are permission-gated
  (Builder/Developer/admin) or account-management tools outside the gameplay surface; the boundary
  is "reachable by a normal player without special permission". `charcreate`/`chardelete` are
  excluded even though `pperm(Player)` unlocks them, because the project's creation flow is the
  `character` command — noted as a documented exception.
- The pre-login `UnloggedinCmdSet` surface (`connect`/`create`/`login` and the connection screen):
  already localized by the `connection-screen` capability; untouched.
- Webclient UI labels (buttons, menus) and `character`-wizard internals (already zh-tw): untouched;
  webclient presentation is owned by webclient changes.
- Renaming the project's own command keys (`talk`, `engage`, `guild …` stay English-primary with
  their existing zh-tw aliases; they already emit zh-tw output).

## Decisions

### D-1. The starting room's zh-tw identity: key 「虛境」, alias `limbo`, `LIMBO_KEY` constant

The room key becomes 「虛境」 (draft name; final wording is an authorship choice at implementation,
kept in `world/maps/bootstrap.py` as `LIMBO_KEY`). `limbo` stays as an alias so legacy references
(builder searches, documentation prose) still resolve. All searches for the room go through
`LIMBO_KEY`, never a literal `"Limbo"` string and never a dbref (the existing by-key-never-by-dbref
rule from `grid-room-sync` is preserved, only the key value changes).

Alternatives considered:
- Keep key `"Limbo"` and add a separate display name attribute: rejected — Evennia's `key` is the
  rendered name; a shadow display name would need custom rendering in the appearance layer, and the
  user-facing room name would still say `Limbo` everywhere else.
- Keep `"Limbo"` with a Chinese alias: rejected — the room title shown by `look` would remain
  English, failing the "object name into zh-tw" requirement.

### D-2. `sync_limbo()`: idempotent in-place convergence, called before `sync_grid()`

A new `world/maps/bootstrap.py::sync_limbo()` runs at every server start from
`server/conf/at_server_startstop.py` (immediately before `sync_grid()`):
- locate the canonical room by `LIMBO_KEY` (alias-aware);
- if absent, locate a legacy room keyed `"Limbo"` and rename it in place (this mirrors
  `sync_service_interiors`'s "update-in-place on every sync" convention rather than adding a
  data-migration layer, and keeps existing developer databases convergent without a wipe);
- re-author `db.desc` and re-affirm key/alias on every call;
- **dual-room precedence**: when both the canonical 「虛境」 room and a legacy `"Limbo"` room exist,
  the canonical room is used (and the bridge sync targets it), the legacy room is left untouched and
  a warning is logged — never a silent arbitrary pick;
- if neither exists, `log_warn` and return without raising (same degradation as `sync_grid`'s
  missing-Limbo path).

This is presentation/registry mirroring, not a state write: it owns no character, economy, quest,
or map-instance state, so the single-writer invariant is unaffected.

### D-3. Bridge exits: zh-tw aliases reconciled in place

`EXIT_TO_CITY` (「南門」) aliases `["south gate", "altoria"]` → zh-tw equivalents (e.g.
`["王都", "城門"]`); `EXIT_TO_LIMBO` (「離開王都」) aliases `["leave", "limbo"]` → zh-tw (e.g.
`["回虛境"]`). Because `_ensure_exit` returns early on an existing exit, the bridge sync gains an
**alias/key reconciliation step**: an existing exit matched by location+destination has its
`key`/`aliases` rewritten to the authored zh-tw values on every sync. This is what makes the
"no English aliases after a re-sync" requirement true for pre-existing developer databases, not
just fresh ones. Tests that typed `leave`/`limbo`/`south gate` move to the zh-tw aliases.

### D-4. Localized appearance layer first (shared by text and webclient look)

The zh-tw frame lives in `typeclasses/objects.py::ObjectParent`, overriding the Evennia appearance
hooks so **one** implementation serves every path:
- `get_display_exits` → 「出口：…」, contents/characters section headers → zh-tw, and
  `default_description` → 「你沒有看到什麼特別的。」 (plus the room header/desc hooks where English
  wording appears);
- the text wrapper 看 (`CmdLook`) keeps the stock command's thin structure — resolve target, call
  `caller.at_look(target)`, emit with `type="look"` — localizing only its own fallback strings
  ("You have no location to look at!" → zh-tw). Because `at_look` flows into `return_appearance`,
  the `PlayerCharacter.at_look` onboarding seam and the webclient `explore.look` action
  (`exploration_actions.py:327`) automatically produce the identical zh-tw appearance.

This order matters: the appearance layer is the foundation; the command wrapper then becomes a
thin delegation, not a re-implementation of the whole frame.

### D-5. Localized default commands: project-owned wrapper classes, stock commands removed

One new module (`commands/localized.py`) defines subclasses of the Evennia defaults:

| Upstream class | Localized key | Retained aliases (full class set) |
|---|---|---|
| `CmdLook` | 看 | `look`, `l`, `ls` |
| `CmdHelp` | 說明 | `help`, `?` |
| `CmdSay` | 說 | `say`, `"`, `'` |
| `CmdPose` | 動作 | `pose`, `:`, `emote` |
| `CmdGet` | 拿 | `get`, `grab` |
| `CmdDrop` | 丟 | `drop` |
| `CmdGive` | 給 | `give` |
| `CmdHome` | 回家 | `home` |
| `CmdWhisper` | 耳語 | `whisper`, `wh` |
| `CmdNick` | 暱稱 | `nick`, `nickname`, `nicks` |
| `CmdSetDesc` | 設定描述 | `setdesc` |
| `CmdQuit` | 登出 | `quit` |
| `CmdWho` | 在線 | `who`, `doing` |
| `CmdOOC` | 離開角色 | `ooc`, `unpuppet` |
| `CmdIC` | 進入世界 | `ic` |
| `CmdPage` | 傳訊 | `page`, `tell` |
| `CmdPassword` | 密碼 | `password` |
| `CmdOption` | 選項 | `option` |
| `CmdSessions` | 連線 | `sessions` |
| `CmdColor` | 色彩 | `color`, `colour` |
| `CmdStyle` | 樣式 | `style` |
| `CmdQuell` | 降權 | `quell` |
| `CmdMap` (XYZGrid) | 地圖 | `map` |
| `CmdGoto` (XYZGrid) | 前往 | `goto`, `path` |

(The exact alias list is taken from the mounted class at implementation; the table is the contract
target. Wrappers inherit the upstream `locks`.)

Rules that make this safe:
- **Branch on `cmdstring`, never on the key**: `CmdWho` must still honor `doing` (narrower
  listing), `CmdGoto` must auto-walk for both 「前往」 and `goto` while `path` stays path-only
  (upstream checks `self.cmdname == "goto"` — the wrapper widens that check to the two walking
  forms), `CmdNick` must keep its switch behavior, etc. The docs-contract test's alias-equality
  assertion guards against dropped aliases.
- **Output re-implementation is per-command and minimal**: where the stock `func()` is thin and
  delegates (e.g. `look` → `at_look`), keep the delegation and translate only the command's own
  strings; where the command owns its output (`say` echoes, `get`/`drop`/`give` messages, `home`,
  `quit`, `who`, `ooc`, `ic`, `page`, `password`, `option`, `sessions`, `color`, `style`, `quell`,
  `nick`, `setdesc`, `whisper`), port the body with zh-tw strings.
- **`help` is not re-implemented wholesale**: subclass `CmdHelp` and override its presentation
  hooks (index listing, entry view, category display mapping General→一般, Combat→戰鬥, Guild→公會,
  Economy→經濟, Admin→管理員) and the no-result string; keep upstream topic fetching, permission
  filtering, subtopics, and the webclient `EvMore` behavior intact.
- **XYZGrid mounting**: a project-owned subclass of `XYZGridCmdSet` adds the native
  `CmdXYZTeleport`/`CmdXYZOpen` unchanged plus the 前往/地圖 wrappers, and is what
  `CharacterCmdSet` mounts — so no native `goto`/`map` ever coexists with the wrappers in the merged
  set (aliases `goto`/`path`/`map` would otherwise collide with the native keys).
- **Creation mode**: `commands/character_creation.py` swaps its `help`/`quit` seams for the
  localized 說明/登出 wrappers so the wizard's "說明 與 登出 仍可用" promise holds.
- Merged cmdsets (`CharacterCmdSet`/`AccountCmdSet`): after `super().at_cmdset_creation()`,
  `self.remove(...)` the stock localized keys and `self.add(...)` the wrappers, so no
  English-keyed variant ever matches.

### D-6. Docs and contract test follow the surface

- `docs/game/command-reference.md`: the localized wrappers become canonical `### <zh-tw key>`
  entries (指令=zh-tw key, 別名=full alias set, zh-tw 語法/情境/說明); the two Evennia default index
  tables now enumerate **retained** defaults (upstream key sets minus the localized set); a
  localized-commands index table lists the wrappers; the XYZGrid coverage is the project's mounted
  set (`@teleport`/`@open` canonical entries stay, `goto`/`map` canonical entries move to 前往/地圖).
- `docs/game/commands.md`: rows for the localized commands; links use the zh-tw heading anchors.
- `tests/test_command_docs.py`: `mounted_command_classes()` already surfaces non-default-class
  commands, so the wrappers land in the project surface; the curated `EXPECTED_COMMANDS` manifest
  gains their syntax/context rows; the XYZGrid enumeration uses the project-owned cmdset (native
  `@teleport`/`@open` plus wrappers); the index-table assertion is re-based to "retained defaults" =
  upstream key sets − localized keys, plus a localized index table equal to the mounted wrapper key
  set; `character`'s 情境 row reads 「說明」與「登出」.
- The `game-command-docs` capability delta rewrites the "Evennia defaults are enumerated",
  "Contrib commands are documented", and "Default command index stays complete" scenarios
  accordingly.

### D-7. Prose that names commands is updated

- `world/onboarding/scenes.py::LOOK_BEAT.prose`: 「先用 look 看看四周」 → 「先用「看」看看四周」.
- `world/help_entries.py::新手引導`: the `look` mention becomes 「看」 (`talk`, `guild register`,
  `guild turnin` keep their English primaries).
- `world/rules/onboarding.py` and guide beat ids (`"look"`, `COMMAND_LOOK`) stay as internal
  identifiers — only player-facing prose changes.

### D-8. Spec deltas

- `limbo-room` (ADDED): the starting room's zh-tw key/alias/description; `sync_limbo()` idempotency,
  legacy rename, and dual-room precedence; zh-tw bridge aliases reconciled in place.
- `localized-appearance` (ADDED): the shared appearance layer renders zh-tw frames for the text 看
  command, the `at_look` seam, and the webclient `explore.look` action.
- `grid-room-sync` (MODIFIED): the Limbo lookup requirement/scenarios switch to `LIMBO_KEY` (by
  key, never by dbref — unchanged rule), alias changes and in-place reconciliation documented.
- `game-command-docs` (MODIFIED): localized surface enumerated; index-table equality re-based to
  retained defaults; XYZGrid enumeration re-based to the project's mounted set; localized wrappers
  covered by the accurate-details requirement.
- `onboarding-guide` (MODIFIED): the arrival-scene `look` prompt prose/scenarios name the zh-tw key.
- Every new/changed main-spec requirement is implemented with a test annotated via
  `covers_requirement` (per `docs/development/spec-test-traceability.md`).

## Risks / Trade-offs

- **`self.remove()` + wrapper-by-alias changes command resolution.** If a stock command's removal
  is missed, both the English key and the zh-tw key remain reachable → mitigated by a contract test
  asserting the merged player cmdsets contain no stock localized command class (index-table
  re-base doubles as the guard).
- **`help` is a large subsystem.** A wholesale `func()` rewrite risks losing topic fetching,
  permission filtering, subtopics, or webclient behavior → mitigated by overriding presentation
  hooks only (D-5), plus behavior tests for index, entry, no-result, category display, and popup.
- **Behavioral aliases could regress** (`doing`, `path`, `grab`, `emote`, `unpuppet`) → mitigated by
  the cmdstring-branching rule and the docs-contract alias-equality assertion, with focused tests
  for the alias-driven behaviors.
- **Webclient look could bypass the localized frame** → mitigated by localizing at the appearance
  layer (D-4) and adding a webclient action-path test asserting the same zh-tw appearance as the
  text 看 command.
- **`goto` auto-walk could silently become path-only** after the key rename → mitigated by the
  widened `cmdstring` check (D-5) and an integration test walking via 「前往」.
- **Dual-room ambiguity** (both 「虛境」 and legacy `"Limbo"` present) → canonical room wins, legacy
  warned and left untouched (D-2), with a dedicated test.
- **Docs/contract churn is large** but mechanical → mitigated by updating manifest, docs, and
  contract test in one task, then running `spec_traceability check` and the full `tests/` +
  `commands` test domains.
- **Existing developer databases** still contain the English room until the next server start, when
  `sync_limbo()` converges them → no migration needed (pre-release); documented in the delta.
- **Out-of-scope English surface remains** (permission-gated builder/admin/system commands, plus
  `charcreate`/`chardelete`) → deliberate, documented boundary ("reachable by a normal player");
  the index tables keep them visible and the reference page points at Evennia docs; a future change
  can localize them without breaking this one.

## Migration Plan

No data migration. On next server start after deploy, `sync_limbo()` renames the room in place and
re-authors the description; the bridge aliases are reconciled in place by the grid sync. Rollback
is equally a restart after reverting the code. No released users; developer databases are wiped
freely if preferred.

## Open Questions

- Final zh-tw room name and description wording (draft 「虛境」) — authored at implementation time,
  pinned in the delta spec and tests.
- Whether `charcreate`/`chardelete` should later join the localized set — currently excluded as
  account-management tools (project creation flow is `character`), re-visited if a future
  multi-character account change lands.
