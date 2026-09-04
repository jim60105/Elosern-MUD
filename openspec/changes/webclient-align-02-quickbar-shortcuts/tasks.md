# Tasks: webclient-align-02-quickbar-shortcuts

## 1. Server single-letter aliases

- [x] 1.1 Add `g` to 拿(`lnGet`) and `s` to 說(`lnSay`) alias tuples in
  `commands/localized/general.py`; add `t` to `talk`, `w` to `wait`(skip), `c` to `CmdCast`.
  Verify no startup cmdset collision.
- [x] 1.2 Add the pinning test: every bound letter (`l`,`g`,`s`,`t`,`w`,`c`) resolves to its
  pinned command in the installed player cmdset with no collision, enumerating every
  installed key AND alias of both player cmdsets. The test carries NO
  `covers_requirement` annotation yet — the pinned-letters requirement's canonical ID
  only exists after this change archives/syncs (the checker resolves IDs only from
  `openspec/specs/`), so the annotation lands in that sync commit per repo convention.
  Lives in the existing shard-registered `commands/tests/test_localized.py`, so
  `.github/evennia-shards.json` needs no edit.

## 2. Chip badges + letter bindings (client)

- [x] 2.1 Restore the draft badge structure in `QuickWordChips.vue`: zh-TW label + `<b>` letter
  badge; exploration `看 l / 拿 g / 說 s / 交談 t / 等待 w`, combat `說 s / 施法 c`; emitted insert
  text becomes the badge letter (trailing space handling stays in the field path).
- [x] 2.2 Add the global letter bindings to the existing key-router path (the one owning `/`):
  outside text-entry surfaces, in exploration/combat modes only, route `l/g/s/t/w` (and `c` in
  combat) through the same insert+focus path as chip clicks; never submit; leave `/`, Esc,
  arrows, 1–4, Tab untouched.
- [x] 2.3 Update `QuickWordChips`/command-line Vitest: badge ⇔ insert-text ⇔ binding equality,
  chip sets per mode unchanged, letter press inside the field inserts text instead of routing.

## 3. Tab completion + truthful hint

- [x] 3.1 Implement completion in `CommandLine.vue`: candidate set = session history + mode chip
  letters + committed exploration panel exit names and interact-target names (dedup); unique →
  full completion caret-end; many → longest-common-prefix then Tab/Shift+Tab cycle; no match →
  no-op; manual edit resets the cycle.
- [x] 3.2 Change the hint cluster to `↑↓ 歷史 · Tab 補全`; update the hint-wording tests to the
  new truthful state.
- [x] 3.3 Vitest: unique completion, LPC + cycle both directions, reset-on-edit, unmatched
  no-op, focus never leaves the field on Tab while candidates match.

## 4. Player-command docs

- [x] 4.1 Update the alias lists in `docs/game/command-reference.md` (拿/說/talk/wait/rest-cast
  rows and the localized-wrapper index table) and the `docs/game/commands.md` overview rows;
  update the curated manifest in `tests/test_command_docs.py` if it pins alias sets; keep the
  drift contract green.

## 5. Verification

- [x] 5.1 Focused Evennia tests (aliases + pinning) and `tools.spec_traceability check`.
- [x] 5.2 Focused Vitest for chips/binding/completion; `node --test` gate if its command-line
  contract tests move.
- [x] 5.3 Live browser check at 1600x900: chip badges render, `g` inserts `g `, Tab completes
  an exit name typed after commit, hint matches the draft.

## 6. Review follow-through (post-implementation rubber-duck)

- [x] 6.1 Migrate the live browser contracts that pinned the superseded behavior: the chip
  scenario expects the badge letter insertion + label/badge structure, the hint scenario expects
  `↑↓ 歷史 · Tab 補全`, new scenarios pin live Tab completion (history seed + unmatched no-op with
  focus kept) and the outside-field bound-letter insert (`web/tests/browser/
  test_browser_input_narrative.py`).
- [x] 6.2 Update the Help overlay's client-owned controls reference to implemented truth: Tab is
  the command-field completion (with the Escape release named), chips write badge letter + space,
  and the bound quickbar letters are listed (`web/webclient-app/lib/controls-reference.js`).
- [x] 6.3 Keyboard-trap disclosure resolved without diverging from the draft hint: the dock
  shortcut legend already names `Esc 返回` (change-01 surface) and the Help reference now names
  the field release too; the delta spec states Tab never moves focus at all and Escape is the
  release path.
- [x] 6.4 Uppercase event-key normalization (Caps Lock / Shift) in the letter router with a
  regression test; in-field letters asserted as browser-default (not defaultPrevented).
- [x] 6.5 Candidate-source changes drop the in-flight completion cycle (watch on canonicalized
  content, not array identity) with a Vitest pin.
- [x] 6.6 Strengthened test claims: the AppClient suite pins committed-source refresh (departed
  exit stops completing, fresh exit completes); the explicit-unavailable exploration form is
  impossible by protocol (the client validator requires `available === true`), so absence is the
  faithful unavailable case and the delta spec wording reflects committed-panel truth.
