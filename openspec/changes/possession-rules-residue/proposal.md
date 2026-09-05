# Proposal: possession-rules-residue

## Why

The archived possession program (core + transition + webclient) landed its behavior, but a
post-archive static audit found five pieces of residue where the implementation drifted from the
synced specs or from the repo's own ownership rules. None breaks a shipped flow today; all are
silent-corruption seeds for the next change. Fixing them now keeps the synced specs
(`companion-possession-transition`, `service-anchoring`) truthful as the architectural source of
record. Audit evidence (re-verified in tree):

1. **Two owners for one handback reason code.** `world/rules/party.py:35` defines
   `REASON_HANDBACK_FIRST = "handback_first"` with `HANDBACK_FIRST_MESSAGE` (:45, mapped at :62)
   — raised by `leave_party` (:405-407) and consumed by `commands/leave.py`. `world/rules/
   possession.py:115` defines a second `REASON_HANDBACK_FIRST` with a *different* fixed line at
   :139 inside `POSSESSION_REJECTION_MESSAGES` — but possession never raises it. One wire reason
   code, two module-level constants, two prose strings, one of which is unreachable dead state.
2. **The multisession disconnect guard lives in the typeclass, not the single writer.**
   `typeclasses/accounts.py:202-218` scans `self.sessions.all()` for a puppet holding
   `possessed_by` and skips the release when another session still drives the possessed NPC —
   business rules in the lifecycle hook. The synced requirement says the hook SHALL call
   `release_on_disconnect(self)`, and the guard's skip semantics are unspecified; the existing
   tests (`world/rules/tests/test_possession_transition.py:167-180`) already pin the behavior
   through `at_post_disconnect`, so the rules module is the wrong layer to own it by accident.
   `release_on_disconnect` also runs a dead query — `ObjectDB.objects.filter(db_account=account)`
   never matches companion NPCs (they are not account-owned) and duplicates
   `_account_characters` for everything it can match.
3. **`_transfer_puppet` grants the lock before retiring the session.** `world/rules/possession.py:293`
   calls `_grant_puppet_lock` before the per-session `send_unpuppet_transition` /
   `retire_sequence` / `reset_client_sequence` block (:306-309). The synced requirement states the
   order explicitly: retire + epoch bump FIRST, then the additive grant — "a completion for A can
   never publish after the swap." Between grant and retire the account holds puppet authority over
   the NPC while the old epoch is still live; the window is small but the spec's stated invariant
   is inverted in code.
4. **`_service_entry`'s docstring sits after its first code block.**
   `web/webclient/presentation/affordances.py:453-484`: the possessed-actor guard is the first
   statement and the descriptive docstring follows it as a bare string expression — merge debris;
   the function currently has no docstring and the paragraph is invisible to `help()`/readers
   scanning declarations.
5. **`service-anchoring` spec overclaims registry-owned prose.** The synced requirement says
   "Fixed Traditional Chinese messages for `remote` **and** `off_anchor` SHALL be registry-owned
   constants." The gate owns only `MESSAGE_OFF_ANCHOR` (`service_gate.py:48`); `remote` refusal
   lines are deliberately per-surface in the callers (`commands/economy.py:56` "這裡沒有商人。",
   guild's "公會服務人員不在這裡。") because the noun differs per service. The code is right and
   the spec sentence is wrong.

## What Changes

- **`world/rules/possession.py`**: delete the dead `REASON_HANDBACK_FIRST` constant and its
  `POSSESSION_REJECTION_MESSAGES` entry (party owns the reason and its dismissal line); move the
  multisession skip INTO `release_on_disconnect` (it already scans sessions — the guard becomes
  per-account logic there); drop the dead `db_account` ObjectDB query; reorder
  `_transfer_puppet` to retire-then-grant exactly as the spec words it.
- **`typeclasses/accounts.py`**: `at_post_disconnect` becomes the thin lifecycle call the spec
  describes — no possession branch beyond the single call.
- **`web/webclient/presentation/affordances.py`**: move `_service_entry`'s paragraph to the top of
  the function so it is a real docstring.
- **Spec deltas**: `companion-possession-transition` MODIFIED disconnect requirement (guard is
  rules-owned, hook is thin); `service-anchoring` MODIFIED resolver requirement (registry owns
  `off_anchor` prose only; `remote` prose is caller-owned per surface).

## Capabilities

### Modified Capabilities

- `companion-possession-transition`: the disconnect hook requirement gains the multisession
  guard sentence; the transfer-ladder requirement is untouched (the code fix conforms TO it).
- `service-anchoring`: the resolver requirement's message-ownership sentence is corrected to
  match reality (no new player-visible behavior).

## Impact

- `world/rules/possession.py` (constants, `release_on_disconnect`, `_transfer_puppet`),
  `typeclasses/accounts.py`, `web/webclient/presentation/affordances.py` (docstring position).
- Tests: `world/rules/tests/test_possession.py`, `test_possession_transition.py` import the
  party-owned `REASON_HANDBACK_FIRST` already; new pins for retire-before-grant ordering and for
  the guard living in the rules module (call `release_on_disconnect` directly with a live second
  session puppet). No player command surface changes → `docs/game/commands.md` untouched.
- Independent of `possession-validator-lockstep` (no shared lines: that change edits
  `exploration.py`/`options.py`/`exploration_actions.py`/JS mirrors; this one edits
  `possession.py`/`accounts.py`/`affordances.py` `_service_entry`).
- No backward compatibility or migration concerns (unreleased, zero users).
