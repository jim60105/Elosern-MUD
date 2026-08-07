## Why

The game now exposes 25+ project-authored player commands (combat, guild, economy, time-skip,
scene, talk, cast, art, character creation) on top of the Evennia defaults and the XYZGrid
contrib commands, but the docsify site under `docs/` documents only game-master operations.
There is no player-facing reference for what can be typed in-game, so players, contributors,
and the AI features cannot discover the available input vocabulary, and command changes are
never reflected anywhere.

## What Changes

- Add a player-facing game input reference under `docs/` (docsify) covering every project-authored
  command mounted on the `CharacterCmdSet` and the `character` creation command: key, aliases
  (including Traditional Chinese aliases), syntax, context restrictions (combat, guild, shop,
  character creation, admin-only), and a Traditional Chinese description.
- Include the mounted XYZGrid contrib commands (`goto`, `map`, `@teleport`, `@open`) in the same
  reference, and enumerate the complete Evennia default character and account command key sets
  in compact index tables with one-line descriptions and a pointer to Evennia documentation.
- Add an overview page that groups commands by category (探索與移動、對話、時間跳躍、戰鬥、
  技能施放、公會、經濟、角色建立、管理員、系統與建造) and marks admin-only commands.
- Wire the new pages into `docs/_sidebar.md` so they appear in the docsify navigation.
- Add a deterministic repository-level regression test (`tests/test_command_docs.py`, no database)
  that cross-checks the mounted command registry, a curated syntax/context manifest, the class
  keys/aliases/locks, the Evennia default cmdset key sets, the sidebar, the overview, and the
  `AGENTS.md` convention against the reference pages, so the documentation cannot silently drift.
- Update `AGENTS.md` with a convention that any command addition, removal, or behavior change
  must update the command reference documentation in the same change.

## Capabilities

### New Capabilities

- `game-command-docs`: A player-facing, docsify-served command reference for all in-game input,
  plus the documentation-update convention enforced by a repository-level contract test.

### Modified Capabilities

<!-- None: this change introduces a new documentation capability and does not alter the
     behavioral requirements of any existing capability. -->

## Impact

- New Markdown pages under `docs/game/` (`commands.md`, `command-reference.md`) and a
  `docs/_sidebar.md` update.
- New top-level regression test `tests/test_command_docs.py` that follows the existing
  `tests/test_contrib_matrix.py` bootstrap pattern (settings + `django.setup()` +
  `evennia._init()`), opens no database, and runs under
  `uv run --locked -m unittest discover -s tests -t .`.
- `AGENTS.md` convention addition; no behavioral code, schema, migration, or dependency changes.
- No release-facing impact: the project is unreleased, so no backward-compatibility layer is
  needed. This change is additive and does not touch the deterministic core.
