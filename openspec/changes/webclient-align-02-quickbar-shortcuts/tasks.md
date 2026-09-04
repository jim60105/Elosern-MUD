# Tasks: webclient-align-02-quickbar-shortcuts

## 1. Server single-letter aliases

- [ ] 1.1 Add `g` to 拿(`lnGet`) and `s` to 說(`lnSay`) alias tuples in
  `commands/localized/general.py`; add `t` to `talk`, `w` to `wait`(skip), `c` to `CmdCast`.
  Verify no startup cmdset collision.
- [ ] 1.2 Add the pinning test: every bound letter (`l`,`g`,`s`,`t`,`w`,`c`) resolves to its
  pinned command in the installed player cmdset with no collision; annotate with
  `covers_requirement` for the new pinned-letters requirement (obtain the ID via
  `uv run --locked python -m tools.spec_traceability list`). Put it in an existing commands
  test module or register the new module in `.github/evennia-shards.json` in the same change.

## 2. Chip badges + letter bindings (client)

- [ ] 2.1 Restore the draft badge structure in `QuickWordChips.vue`: zh-TW label + `<b>` letter
  badge; exploration `看 l / 拿 g / 說 s / 交談 t / 等待 w`, combat `說 s / 施法 c`; emitted insert
  text becomes the badge letter (trailing space handling stays in the field path).
- [ ] 2.2 Add the global letter bindings to the existing key-router path (the one owning `/`):
  outside text-entry surfaces, in exploration/combat modes only, route `l/g/s/t/w` (and `c` in
  combat) through the same insert+focus path as chip clicks; never submit; leave `/`, Esc,
  arrows, 1–4, Tab untouched.
- [ ] 2.3 Update `QuickWordChips`/command-line Vitest: badge ⇔ insert-text ⇔ binding equality,
  chip sets per mode unchanged, letter press inside the field inserts text instead of routing.

## 3. Tab completion + truthful hint

- [ ] 3.1 Implement completion in `CommandLine.vue`: candidate set = session history + mode chip
  letters + committed exploration panel exit names and interact-target names (dedup); unique →
  full completion caret-end; many → longest-common-prefix then Tab/Shift+Tab cycle; no match →
  no-op; manual edit resets the cycle.
- [ ] 3.2 Change the hint cluster to `↑↓ 歷史 · Tab 補全`; update the hint-wording tests to the
  new truthful state.
- [ ] 3.3 Vitest: unique completion, LPC + cycle both directions, reset-on-edit, unmatched
  no-op, focus never leaves the field on Tab while candidates match.

## 4. Player-command docs

- [ ] 4.1 Update the alias lists in `docs/game/command-reference.md` (拿/說/talk/wait/rest-cast
  rows and the localized-wrapper index table) and the `docs/game/commands.md` overview rows;
  update the curated manifest in `tests/test_command_docs.py` if it pins alias sets; keep the
  drift contract green.

## 5. Verification

- [ ] 5.1 Focused Evennia tests (aliases + pinning) and `tools.spec_traceability check`.
- [ ] 5.2 Focused Vitest for chips/binding/completion; `node --test` gate if its command-line
  contract tests move.
- [ ] 5.3 Live browser check at 1600x900: chip badges render, `g` inserts `g `, Tab completes
  an exit name typed after commit, hint matches the draft.
