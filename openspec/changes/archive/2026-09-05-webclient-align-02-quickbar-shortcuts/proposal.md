# Proposal: webclient-align-02-quickbar-shortcuts

## Why

The design draft's quick-word chips carry command-initial letter badges that double as
keybindings (`看 l`, `說 s`, …), and its command line advertises `↑↓ 歷史 · Tab 補全`. The live
client dropped both badges and the completion affordance precisely because neither existed
(see the deliberate note in `QuickWordChips.vue`). This change makes the affordances real: the
badge letters are installed command words on the server (via Evennia's standard single-letter
aliases), the client binds those letters, and Tab completion works over candidates the player
could actually send.

## What Changes

- Server: add single-letter command aliases — `g`→拿(get), `s`→說(say), `t`→talk, `w`→wait,
  `c`→cast. `l`→看 already exists. No letter collides with an installed key/alias (verified).
  This is a player-command surface change: `docs/game/commands.md` and
  `docs/game/command-reference.md` updated in the same change.
- Client chips: restore the draft's letter-badge structure; every badge letter is a real,
  bound key and a real command word. Exploration set `看 l / 拿 g / 說 s / 交談 t / 等待 w`;
  combat set `說 s / 施法 c`. Pressing a bound letter from any non-input focus focuses the
  command line and inserts that letter + a trailing space (the inserted text is itself a
  playable command word); never submits.
- Client Tab completion: inside the input field, Tab completes the current prefix against
  command history + the mode's chip letters + committed exploration-panel exit names and
  interact-target names. One candidate → complete; many → complete to the longest common
  prefix, then cycle. Shift+Tab reverses the cycle.
- Hint cluster becomes the truthful draft string `↑↓ 歷史 · Tab 補全`.

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-contextual-hud`: the quick-word-chip requirement is restated for the draft's
  badge structure — visible zh-TW label + letter badge, inserted text is the badge letter,
  and each badge letter is a client binding AND an installed server command word; the
  command-line-hint requirement gains the now-real Tab-completion affordance; an added
  requirement pins the five bound letters against the installed player cmdset.

`game-command-docs` needs no delta: its existing accurate-details contract already requires
the reference's alias lists to match the command class definitions and the curated manifest,
so the new aliases are documentation updates under that standing requirement (tasks).

## Impact

- `commands/localized/general.py` (aliases on 拿/說), `commands/talk.py`, `commands/skip.py`,
  `commands/action.py` (aliases on cast); `tests/test_command_docs.py` green.
- `docs/game/commands.md` + `docs/game/command-reference.md`: alias lines updated.
- `web/webclient-app/components/QuickWordChips.vue`, `CommandLine.vue`, global key router
  bindings; Vitest coverage for badges, letter bindings, and completion.
- No protocol/panel changes. Tab candidates read the already-committed exploration panel only.
