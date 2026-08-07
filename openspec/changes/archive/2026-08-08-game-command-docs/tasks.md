## 1. Command reference content

- [x] 1.1 Create `docs/game/command-reference.md` with canonical `### <key>` entries (指令 /
      別名 / 語法 / 情境 / 說明 table, aliases as backticked tokens separated by `、`) for
      every project-authored command on the `CharacterCmdSet`: `talk`, `rest`, `sleep`, `wait`,
      `進入`/`enter`, `cast`, `engage`, `combat forfeit`, `combat actions`, and the full `guild`
      family (`register`, `list`, `accept`, `log`, `show`, `abandon`, `turnin`, `merit`,
      `request`, `exam`)
- [x] 1.2 Add canonical entries for the economy commands (`shop stock`, `buy`, `sell`,
      `inventory`) and the admin `art` family (`art status`, `art run`, `art retry`,
      `art requeue`) with admin-only marking and the `Developer` permission requirement
- [x] 1.3 Add a single `character` entry covering `character`, `character preset <key>`, and
      `character create`, with the interactive wizard and `cancel` escape in 說明, plus a note
      that creation mode replaces other game commands while `help` and `quit` remain available;
      do not document the non-typable `CMD_NOMATCH` key
- [x] 1.4 Add detailed canonical entries for the `XYZGridCmdSet` contrib commands (`goto`,
      `map`, `@teleport`/`@tel`, `@open`) including keys, aliases, and syntax
- [x] 1.5 Add `##`-level index tables enumerating the complete key sets of
      `default_cmds.CharacterCmdSet()` and `default_cmds.AccountCmdSet()` with one-line
      Traditional Chinese descriptions and a pointer to Evennia documentation (rows shaped
      `| `key` | 描述 |`, distinct from canonical entries)
- [x] 1.6 Verify every entry's key, aliases, and syntax against the actual command classes in
      `commands/` (each canonical entry must carry non-empty 說明)

## 2. Overview and navigation

- [x] 2.1 Create `docs/game/commands.md` overview page grouping all documented commands by
      category (探索與移動、對話、時間跳躍、戰鬥、技能施放、公會、經濟、角色建立、管理員、
      系統與建造) with tables linking to `command-reference.md` anchors, plus a note that
      pre-login commands are Evennia defaults (pointer to Evennia documentation)
- [x] 2.2 Add the 遊戲指令 section with links to both new pages in `docs/_sidebar.md`

## 3. Drift contract test

- [x] 3.1 Add `tests/test_command_docs.py` following the `tests/test_contrib_matrix.py` bootstrap
      pattern (`DJANGO_SETTINGS_MODULE` + `django.setup()` + `evennia._init()`, no database);
      collect mounted project commands by instantiating `CharacterCmdSet` and
      `CharacterCreationCmdSet`, and expand the nested `XYZGridCmdSet` instance for its commands
- [x] 3.2 Add the curated `EXPECTED_COMMANDS` manifest (key → syntax/context) and assert per
      command: `### <key>` entry exists, 指令/別名 rows match the class key/aliases, 語法/情境
      rows equal the manifest, 說明 is non-empty; admin entries require the class locks to
      contain `perm(Developer)`, and context rows must be consistent with `help_category`
      (`Combat`/`Guild`/`Economy`/`Admin`)
- [x] 3.3 Assert no orphan canonical entries; assert the Evennia default index tables equal the
      key sets of `default_cmds.CharacterCmdSet()` and `default_cmds.AccountCmdSet()`
- [x] 3.4 Assert the overview category tables reference only documented canonical keys,
      `docs/_sidebar.md` links both new pages, and `AGENTS.md` contains the update convention
- [x] 3.5 Run `uv run --locked -m unittest discover -s tests -t .` and confirm the new test
      passes and the existing top-level regression tests remain green
      (note: two `test_container_contract` failures exist on the pristine baseline, caused by an
      unrelated uncommitted `compose.yaml` change (`:ro` → `:ro,z`); they are not introduced by
      this change)

## 4. Agent guide convention

- [x] 4.1 Add a documentation-convention section to `AGENTS.md` under "Python and Evennia
      conventions" requiring command-reference updates (`docs/game/commands.md` and
      `docs/game/command-reference.md`) in the same change as any command addition, removal,
      rename, or behavior change, keeping `tests/test_command_docs.py` green

## 5. Traceability and verification

- [x] 5.1 When syncing to main specs (archive), obtain canonical requirement IDs with
      `uv run --locked python -m tools.spec_traceability list` and annotate the matching test
      methods with `@covers_requirement("game-command-docs::<id>")`; run
      `uv run --locked python -m tools.spec_traceability check`
- [x] 5.2 Serve the docs locally (`uv run --locked python -m http.server --directory docs 3000`)
      and confirm the new pages render and are reachable from the sidebar and search
- [x] 5.3 Run `openspec validate game-command-docs --strict` and the relevant test domains
      (top-level regression suite)


## 6. Independent review

- [x] 6.1 Run an independent rubber-duck critique of the whole implementation; fix blocking
      findings (Builder permission notes for `map`/`@teleport`/`@open`, `character` entry
      `help`/`quit` nuance, Traditional Chinese description assertions) and update the delta spec
      and the synced main spec accordingly
- [x] 6.2 Re-run the affected tests and the traceability/validation gates after the review fixes
