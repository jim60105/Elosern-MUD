## Context

Elosern's in-game input surface has three layers: 25+ project-authored commands mounted on the
`CharacterCmdSet` in `commands/default_cmdsets.py` (plus the replacement `CharacterCreationCmdSet`
during character creation), the `XYZGridCmdSet` contrib commands (`goto`, `map`, `@teleport`,
`@open`), and the Evennia default character/account commands retained through `super()`. The
`AccountCmdSet` merges with the `CharacterCmdSet` when an account puppets a character, so both are
part of the typed in-game surface.

The docsify site under `docs/` (Traditional Chinese, `index.html` + `_sidebar.md`, served with
`uv run --locked python -m http.server --directory docs 3000`) currently covers only
game-master operations, development notes, and the engine design spec. There is no player-facing
command reference, so in-game input vocabulary is undiscoverable and command changes drift silently.

This change is documentation-focused: it adds the reference, wires it into the sidebar, and
introduces a deterministic contract test plus an `AGENTS.md` convention so the reference cannot
drift. The contract test follows the established top-level regression bootstrap pattern used by
`tests/test_contrib_matrix.py` (`DJANGO_SETTINGS_MODULE` + `django.setup()` + `evennia._init()`);
it opens no database and performs no state writes. The project is unreleased, so no
backward-compatibility layer is needed.

## Goals / Non-Goals

**Goals:**
- Provide a complete, accurate, Traditional Chinese reference of every command a player can type
  while playing: project-authored commands and the `character` creation command in full detail
  (key, aliases including Traditional Chinese, syntax, context restrictions, admin marking),
  XYZGrid contrib commands in full detail, and complete enumerated index tables of the Evennia
  default character and account cmdsets.
- Make the reference discoverable through the docsify sidebar and search, with an overview page
  that groups commands by category.
- Enforce freshness with a repository-level contract test and an `AGENTS.md` convention requiring
  command-reference updates in the same change as any command addition, removal, or behavior
  change.

**Non-Goals:**
- No changes to command behavior, keys, aliases, locks, help categories, or cmdsets.
- No automation that generates the reference from `help_text`: project `help_text` is sparse and
  English, while the docs are player-facing Traditional Chinese prose; hand-written entries with
  a curated manifest keep quality and language consistent.
- No documentation of pre-login `UnloggedinCmdSet` commands (`connect`, `create`, `login`):
  those are not in-game input; a one-line pointer to Evennia documentation is provided in the
  overview.
- No documentation of webclient OOB commands or UI menus; the reference covers keyboard input
  only.
- No changes to `docs/index.html` or the docsify configuration: the existing setup (sidebar,
  search, Prism languages) already serves the new Markdown pages.

## Decisions

### D1. Page layout: two new pages under `docs/game/`

- `docs/game/commands.md` — overview and category index (探索與移動、對話、時間跳躍、戰鬥、
  技能施放、公會、經濟、角色建立、管理員、系統與建造), one table per category linking to the
  in-page anchors of the reference page, plus the note about pre-login commands and the pointer
  to Evennia documentation.
- `docs/game/command-reference.md` — one `### <key>` section per canonical command with a table
  (`| 指令 | | 別名 | | 語法 | | 情境 | | 說明 |`), followed by `##`-level index tables for the
  Evennia default character and account commands.

Rationale: a single reference page keeps the contract test to one parse target and lets the
docsify full-text search index every command heading; the overview page answers "what can I type"
at a glance. Alternatives considered: per-category files (more files to maintain and test) and a
generated-from-code reference (rejected in Non-Goals).

### D2. Canonical per-command entry format (machine-checkable)

Every canonical command entry (project-authored plus XYZGrid contrib) uses the same table shape:

```
### guild accept

| 項目 | 內容 |
| --- | --- |
| 指令 | `guild accept` |
| 別名 | `guild 接取`、`接取任務` |
| 語法 | `guild accept <definition_key>` |
| 情境 | 公會（需當地公會服務人員） |
| 說明 | 接取任務板上的委託。 |
```

- The contract test parses only `###`-headed sections with this exact table shape; the `##`-level
  Evennia default index tables use a different row shape (`| `key` | 描述 |`) and are excluded
  from the canonical parser and the orphan check.
- Aliases are backticked tokens separated by `、`; multi-key commands such as the guild family
  are documented per full key (`guild accept`, `guild list`, ...) rather than per class.
- `character` is a single canonical entry: its 語法 row covers `character`,
  `character preset <key>`, and `character create`, and its 說明 explains the interactive wizard
  and the `cancel` escape. `CmdCreationRequired`'s `CMD_NOMATCH` key is not player-typable and is
  deliberately absent from the docs and from the orphan check.
- The 指令 / 別名 / 語法 / 情境 rows are the contract surface; 說明 is free-form Traditional
  Chinese prose that must be non-empty.

### D3. Coverage scope by source layer (precise surface definition)

- **Project-authored commands (full detail, strictly enforced):** every command class added in
  `CharacterCmdSet.at_cmdset_creation` (`commands/default_cmdsets.py`) and the `character`
  command from `CharacterCreationCmdSet` (`commands/character_creation.py`). This is the
  drift-prone surface.
- **XYZGrid contrib commands (full detail, strictly enforced):** `goto`, `map`, `@teleport`,
  `@open`, because they are game-relevant movement commands players actually type.
- **Evennia default character and account cmdsets (enumerated index tables, strictly enforced):**
  the complete key sets of `default_cmds.CharacterCmdSet()` and `default_cmds.AccountCmdSet()`,
  each as a compact table with one-line Traditional Chinese descriptions and a pointer to the
  Evennia documentation. Enforcing key-set equality makes the "complete" claim of the reference
  precise and testable.
- **Pre-login surface (`UnloggedinCmdSet`):** excluded from the reference; a one-line pointer in
  the overview.

Rationale: full detail where the project owns drift, complete-but-compact enumeration where
Evennia upstream is the authority. Enforcing the default key sets is cheap (one iteration over
the evennia cmdset instances) and prevents silent gaps.

### D4. Contract test: `tests/test_command_docs.py` (top-level regression domain)

A `unittest.TestCase` following the bootstrap pattern of `tests/test_contrib_matrix.py`
(`os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")`, `django.setup()`,
`evennia._init()`). No database is opened and no state is written. The test:

1. Instantiates the project `CharacterCmdSet` and `CharacterCreationCmdSet` creation paths and
   collects every mounted project command class; explicitly instantiates the nested
   `XYZGridCmdSet` and collects its commands (no reliance on `CmdSet.add()` merge internals).
2. Holds a curated manifest — `EXPECTED_COMMANDS: dict[key, {syntax, context}]` — as the single
   human-curated source for syntax and context (the commands parse `self.args` by hand, so syntax
   cannot be derived mechanically). Machine-verifiable facts are never curated: keys and aliases
   come from the classes, admin status from the class `locks` (`perm(Developer)`), and context
   rows must be consistent with `help_category` where it is `Combat`/`Guild`/`Economy`/`Admin`.
3. Parses `docs/game/command-reference.md` canonical entries and asserts, per command: the
   `### <key>` entry exists; the 指令 / 別名 rows match the class key and aliases; the 語法 and
   情境 rows equal the manifest; the 說明 row is non-empty; admin entries carry the permission
   note and the class locks require `Developer`.
4. Asserts there are no orphan canonical entries (every `###` entry maps back to a known mounted
   command).
5. Asserts the Evennia default index tables enumerate exactly the keys of
   `default_cmds.CharacterCmdSet()` and `default_cmds.AccountCmdSet()`.
6. Asserts `docs/game/commands.md` overview category tables reference only documented canonical
   keys, that `docs/_sidebar.md` links both new pages, and that `AGENTS.md` contains the update
   convention.
7. Carries `@covers_requirement("game-command-docs::<id>")` annotations (canonical IDs obtained
   from `uv run --locked python -m tools.spec_traceability list` when the specs are synced to main
   specs at archive) so every requirement of the capability maps to a substantively matching test.

It runs under `uv run --locked -m unittest discover -s tests -t .`, the existing top-level
regression domain, so the full suite stays under the existing ownership split.

Rationale: a curated manifest with machine-checked facts keeps the test honest (it never claims
to verify what it cannot), the bootstrap pattern is already proven in the repo, and the
`covers_requirement` annotations satisfy the traceability gate on archive. Alternative: adding
machine-readable usage metadata to every command class (rejected: expands the change into
command behavior code and alters `help` output; the docs-only scope keeps game code untouched).

### D5. `AGENTS.md` convention

Add a short section (under "Python and Evennia conventions") stating: any change that adds,
removes, renames, or alters a player command (key, alias, syntax, or context) must update
`docs/game/commands.md` and `docs/game/command-reference.md` in the same change, and keep
`tests/test_command_docs.py` green.

Rationale: the agent guide is the natural place for a repo-wide convention; the contract test
makes the convention mechanically enforceable rather than advisory.

## Risks / Trade-offs

- [Docs drift on future command changes] → Contract test fails on any mounted command without a
  matching entry; `AGENTS.md` convention makes the test a same-change requirement.
- [Syntax/context drift inside hand-written parsers] → The curated manifest is the single review
  point; keys/aliases/admin/context-category are machine-verified, so only prose and the manifest
  syntax string need human review, both diffed in code review.
- [Test brittleness against Markdown formatting] → The entry format is a documented contract
  (D2); the parser matches the canonical `###` table shape only, default index tables use a
  distinct row shape, and prose lives in the 說明 row, which the test does not parse.
- [Evennia default key sets change after an upgrade] → The enumerated index tables must track
  Evennia's key sets; the test surfaces any drift as a small, obvious diff, and the tables carry
  a pointer to Evennia documentation.
- [Evennia bootstrap in a top-level test] → Follows the proven `tests/test_contrib_matrix.py`
  pattern; no database writes, so the test stays in the fast regression domain.
- [Traditional Chinese alias coverage gaps] → The test compares the docs alias row against the
  class `aliases` attribute, so an alias missing from the docs is a test failure.
- [Large single reference page] → Mitigated by the overview page and docsify full-text search; a
  single page is also the simplest parse target for the contract test.

## Migration Plan

No runtime migration: this is documentation plus a test. Rollback is a plain revert of the docs
pages, the sidebar entry, the test file, and the `AGENTS.md` section. The `AGENTS.md` convention
and the test take effect immediately on merge; no data or settings changes are involved.
