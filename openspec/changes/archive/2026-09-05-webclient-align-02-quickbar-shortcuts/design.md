# Design: webclient-align-02-quickbar-shortcuts

## Context

`QuickWordChips.vue` carries an explicit note: badges, keybindings, and the Tab hint were
dropped because none existed. The installed verbs are 看(`l` exists), 拿(`get`), 說(`say`),
交談(talk), 等待(wait), 施法(cast). A repo-wide alias audit confirms the letters `g`, `s`,
`t`, `w`, `c` are unclaimed command keys/aliases. The draft's chips are
`<button class=verb>看 <b>l</b></button>` — the badge letter is the binding.

## Goals / Non-Goals

**Goals:**
- Every badge letter is simultaneously: a server-installed command word, the chip's binding,
  and the text inserted into the field (badge ⇔ alias ⇔ keybinding — no decorative lies).
- Tab completion over candidates the player could really send right now.
- Hint text becomes exactly `↑↓ 歷史 · Tab 補全`.

**Non-Goals:**
- No fictional 走/問 verbs (the draft's `走 g`/`問 q` letters are NOT claimed; `g` goes to 拿
  per the owner's command-initial rule, superseding the draft's chip table).
- No full 58-command catalog panel; no completion of free-form prose.

## Decisions

- **Insert text = badge letter.** `看` chip inserts `l ` — a complete playable command on every
  transport (telnet included), so the webclient inserts exactly what the badge teaches. The
  visible label keeps the zh-TW verb + badge (draft structure). Alternative (insert the verb
  word): rejected — the badge letter would no longer equal the inserted command word.
- **Binding site.** A document-level keydown listener (same router that owns `/`, Esc, arrows):
  active only when focus is not in the command field or any input/textarea/contenteditable,
  matching the existing `/`-focus gate. Letters are consumed only in exploration/combat modes
  (committed-mode gate), insert via the existing single `insert` → field path, and move focus
  to the field. Digits 1–4 card picks and Tab are untouched.
- **Alias placement.** Add to the existing localized commands' `aliases` tuples
  (`拿`+`g`, `說`+`s`) and to `talk`/`skip`/`CmdCast` (`t`/`w`/`c`). Evennia resolves aliases
  per-command; a collision would surface at startup — the repo audit shows none.
- **Tab candidate set.** Deduplicated union of: session command history (existing history
  state), the mode's badge letters, and committed `exploration` panel exit names + interact
  target display names (already in the store; zero protocol change). Matching: case-insensitive
  prefix on the current field text before the caret; completion replaces the whole field text
  (MUD-line semantics — no multi-token tokenization yet, YAGNI). One match → full completion +
  caret to end; multiple → longest-common-prefix, then Tab cycles matches, Shift+Tab reverse.
  If the field text matches no candidate, Tab is a no-op (never steals focus).
- **Docs.** `docs/game/commands.md` + `command-reference.md` list the new letters; the existing
  drift-contract test (`tests/test_command_docs.py`) is the enforcement.

## Risks / Trade-offs

- Single-letter aliases make `l`/`s`/`t`/`g`/`w`/`c` reserved prefixes on every transport;
  acceptable (Evennia convention; matches upstream default aliases like `l`, `gi`).
- Tab-cycle state must reset on any manual edit of the field (otherwise the cycle resurrects
  stale candidates) — covered by a focused test.
