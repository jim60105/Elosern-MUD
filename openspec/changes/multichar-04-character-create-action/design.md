## Context

`multichar-03-character-switch-action` established, and this change reuses without modification:

- The decide-synchronously / schedule-the-transition contract, and why it is mandatory (an inline
  transition retires the sequence `_publish_completion` guards on, so the request receives no
  result; and driving the client `detached` while a request is in flight marks that request
  uncertain).
- The injectable clock seam.
- `_attach_puppet(session, account, target)` — detach signal, retire, reset, `puppet_object`, and
  the **verification** that the session actually holds the target afterwards, because Evennia's
  `puppet_object` can refuse silently.
- `_recover_transition(...)` — the three-rung ladder ending in an explicit "you hold no character"
  message and an error-severity log.

New machinery this change relies on, read from the tree:

- `DefaultAccount.create_character` (`evennia/accounts/accounts.py:931-976`) calls
  `check_available_slots()` first and returns `(None, [slot_check])` — it **does not raise** on a
  full account. `key` defaults to `self.key` (the account name) and `location` defaults to
  `settings.START_LOCATION`.
- The project's `Account.at_post_create_character` (`typeclasses/accounts.py:162-165`) calls the
  parent hook and then sets `character.creation_pending = True`.
- `PlayerCharacter.at_cmdset_get` (`typeclasses/characters.py:104-109`) derives the
  `CharacterCreationCmdSet` gate from `creation_pending` on every merge, so a freshly created shell
  is gated the moment it is puppeted.
- `PresentationCoordinator.mode_for` resolves `creation_pending` → `creation` before every other
  branch (`presentation/coordinator.py:143-146`), so the new shell's snapshot mounts
  `CreationOverlay` with no client change.
- `creation_start_screen()` (`commands/character_creation.py`) is the reusable no-argument
  presentation; `render_pending_character_login` in `typeclasses/accounts.py` is the only sender of
  `WORLD_INTRODUCTION`, and after `multichar-01` it is reached only from `at_post_login`.

## Goals / Non-Goals

**Goals:**

- One allowlisted creation action that adds no new mechanism — it is a second caller of change 03's
  helper.
- A capacity failure that costs the player nothing: no detach, no recovery, no visible interruption.
- The existing creation wizard, unmodified, for every character after the first.
- The world introduction structurally unable to reappear.
- An end-to-end integration test proving the whole feature works across two characters.

**Non-Goals:**

- No second wizard, no new creation panel, no change to `creation.*` actions.
- No naming of the new shell. The wizard's activation is the sole writer of a character's display
  name.
- No client UI — the confirmation gate on the create control is `multichar-05-topbar-switcher-ui`.
- No character deletion or slot purchase.

## Decisions

### D1 — Create the shell first, detach second

This is the ordering decision that matters, and it differs deliberately from the switch path.

`create_character` can fail for a reason the synchronous decision cannot fully rule out: the
capacity check it performs internally is the authoritative one, and it runs against committed state
at transition time. If the transition detached the current character first and *then* discovered a
full account, the player would have been thrown OOC by a request that turns out to be refusable —
and the recovery ladder would have to repair a situation that never needed to happen.

Creating first inverts that. `create_character` returning `(None, [error])` is a pure no-op with
respect to the session: nothing was detached, no snapshot was retired, no signal was sent. The
transition simply logs, tells the player, and stops — the session continues on its current character
with its epoch intact and no recovery needed.

Order inside the scheduled call:

1. Re-validate: the account is still below `settings.MAX_NR_CHARACTERS` and the current puppet is
   still not in an active combat session.
2. `account.create_character()` — no `key` override, so Evennia's default applies and
   `at_post_create_character` sets the pending marker. A `(None, errors)` return, or a raise, stops
   here with a logged warning and one player line. **Nothing about the session has changed.**
3. `_attach_puppet(session, account, shell)` — change 03's verified attach.
4. On verified success: `account.db._last_puppet = shell`, `synchronize_session(session, shell)`,
   and `account.msg(creation_start_screen())`.
5. On failure: change 03's `_recover_transition`, with one addition — the orphaned shell that was
   created but never attached is left in place rather than deleted. It is a legitimate pending
   character the player owns; it appears in the roster with its pending marker and can be entered
   later through `account.character.switch`. Deleting it inside a failure path would be a
   destructive write on the error branch, which is exactly where destructive writes are least
   trustworthy.

### D2 — The synchronous capacity check is the fast path, not the authority

The adapter still rejects `character_slots_full` at admission, so the ordinary full-account case
gets an immediate, stable rejection and never schedules anything. `create_character`'s own slot
check at transition time is the authority; D1 makes the two disagreeing harmless.

### D3 — The combat lock applies to creation exactly as to switching

Creating leaves the current character, so `is_in_active_session(actor)` gates it with the same
`in_combat` code and message. Re-derived from the predicate, never read from the roster panel's
advisory field.

### D4 — The world introduction cannot be resent

`WORLD_INTRODUCTION` reaches a player only through `render_pending_character_login`, which
`multichar-01` binds to `at_post_login` and keys on the session's own puppet. A mid-session puppet
change does not run the login hook, so there is no code path from this action to the introduction.
The requirement is expressed as a guarantee and asserted by a test, but it is satisfied
structurally rather than by an explicit suppression the action has to remember.

`creation_start_screen()` *is* sent, for parity with the first character's experience: the WebClient
gets its `creation` panel from the snapshot either way, and the narrative feed should read the same
for a second character as for the first.

### D5 — The action is result-only, like the switch

`no_presentation: True` on both outcomes, for the same two reasons: a success's completion snapshot
would be built from the old puppet and immediately superseded, and a rejection must not trigger a
full snapshot that re-renders an open creation surface and discards unsaved form edits. That second
reason is sharper here — a player already inside the wizard is exactly who might hit the capacity
rejection.

### D6 — The shell keeps Evennia's default key

`create_character` names the shell after the account and `activate_player_character` renames it to
the chosen display name inside the activation transaction. The action does not intervene:
`multichar-02`'s roster reports the object key truthfully with a pending marker, and
`multichar-05`'s switcher renders 「建立中」 beside it. Assigning a placeholder key here would be a
canonical-identity write outside the deterministic core's creation service.

## Risks / Trade-offs

- **An orphaned shell after a failed attach.** The account holds a pending character it never
  entered, consuming a slot. → Accepted and specified (D1 step 5): it is reachable through the
  roster and the switch action, so it is recoverable by the player rather than lost. The
  alternative — deleting on the error branch — is a destructive write in the least trustworthy
  place, and the account is not silently poisoned because the roster shows the row.
- **A player repeatedly hitting a failing attach could fill their slots with orphans.** → Bounded
  by `MAX_NR_CHARACTERS` (≤10) and by the capacity check, which counts orphans like any other
  character; the third attempt is refused with `character_slots_full` at admission.
- **The integration test spans two changes' surfaces** (`roster` panel from `multichar-02`, switch
  from `multichar-03`). → Stated in the proposal's Impact: this change is developable in parallel
  with `multichar-02` but not fully verifiable in CI until it lands. Sequencing the merge after
  `multichar-02` avoids a temporarily-skipped assertion.
- **`creation_start_screen()` arrives as narrative text a WebClient player may not read**, because
  the creation overlay covers the feed. → Accepted: it is the same text the first character
  receives at login, and the overlay itself is the primary surface. Suppressing it would make the
  second character's feed differ from the first's for no gain.
