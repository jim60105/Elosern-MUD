# Tasks: title-codex-removal

## 1. Read model + OOB contract

- [x] 1.1 `world/rules/title_view.py`: `TitleCodexView` /
  `FixedTitleRowView` / `EpithetRowView` (frozen dataclasses);
  `build_title_codex_view(character, *, max_rows, max_display_chars,
  max_basis_chars)` per spec (registry-order fixed rows with locked hint /
  unlocked flavor, newest-first epithet rows with basis/equipped/`can_remove`,
  equipped dict, live `full_title`, counters; pure, deterministic, clipped).
- [x] 1.2 OOB constants `TITLE_MAX_ROWS` / `TITLE_MAX_DISPLAY_CHARS` /
  `TITLE_MAX_BASIS_CHARS` + title-category enum across the four mirrors
  (rules read-model owner, webclient panel validator, JS
  `protocol.js` validator + exports, boundary tests — the same four mirrors
  the `lineage` panel uses; display cap 64 equals the epithet storage cap
  so rendered identifiers are never truncated).
- [x] 1.3 OOB `title` schema v1 send path:
  `{schema_version, fixed_rows, epithet_rows, equipped, full_title, unlocked,
  total, pending_ballot}`.

## 2. Removal (rules layer)

- [x] 2.1 `world/rules/titles.py::remove_epithet(entity, display)`: one-pass
  validation (unknown/wrong-kind stable rejection →
  `TITLE_LAST_EPITHET` → `TITLE_EQUIPPED_UNREMOVABLE`; last-remaining is
  evaluated before equipped because D8 makes the sole epithet the equipped
  one and the scenario demands the LAST code there) before any review state;
  un-gated success: delete entry + append `{tick, display}` to the bounded
  `title_epithet_removals` log (snapshot-registered, same transaction; the
  nomination prompt digest includes it) + return the `title_epithet_removed`
  EventLog; slots never touched; no fixed delete path added.
- [x] 2.2 Telnet `title remove epithet <display>` echo-then-`confirm` flow
  (re-validates gates at execution; any other continuation cancels);
  `title codex` text rendering of both blocks.

## 3. WebClient codex window

- [x] 3.1 Big window: header live full-title preview; 「稱號」block with category
  tabs + locked 🔒/hint cards + click-to-equip unlocked; 「異名」block with
  click-to-equip, ★ on equipped, 「移除」 rendered from `can_remove`; confirm card
  (display + basis verbatim, 「此操作不可恢復」) posting the two-step removal;
  「提名中」tab hosting G's ballot buttons; no 卸裝 control. Vitest coverage for
  locked render, both equip paths, preview update, `can_remove` hiding, confirm
  card display/cancel.

## 4. Docs + tests (register new modules in `.github/evennia-shards.json`)

- [x] 4.1 Docs trio updated (syntax list extends per the game-command-docs delta).
- [x] 4.2 Pure tests: view matrix (locked/unlocked hints, counters, newest-first
  ordering, clipping, determinism); removal matrix (both gate codes never enter
  review, missing-confirm cancels, swap-then-delete succeeds with slot intact,
  last-epithet refusal, unknown/wrong-kind refusal, re-nominatable name after
  deletion, EventLog entry).
- [x] 4.3 Integration: removal persists across logout/reload; view identical
  post-relogin; structural absence test for any fixed-title delete surface.
- [x] 4.4 One browser class (CI owns the full list): locked/unlocked render, two
  equip paths, preview update, ballot tab, `can_remove` button visibility,
  confirm card display/cancel.

## Verification

- [x] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules commands web.webclient tests.test_command_docs` (3555 tests OK, --parallel 16)
- [x] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors, 1124/1124)
- [x] V3 `uv run --locked python -m compileall -q world typeclasses commands server` (+ web/tests)
- [x] V4 `openspec validate title-codex-removal --strict`
- [x] V5 `git diff --check`

## Post-sync traceability (during archive/sync)

- [ ] P1 On sync, annotate the new `title-system` requirement IDs on the §4.2–
  §4.4 tests; re-check the `game-command-docs` title-entry ID coverage (same ID
  through F→G→H syntax extensions).
