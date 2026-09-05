# Tasks: possession-rules-residue

## 1. Handback reason single ownership

- [x] 1.1 `world/rules/possession.py`: delete `REASON_HANDBACK_FIRST` (:115) and its
  `POSSESSION_REJECTION_MESSAGES` entry (:139). Grep-verify zero raise/import sites of the
  possession-module binding first (`from world.rules.possession import REASON_HANDBACK_FIRST`
  must have none; party's own constant and `commands/leave.py` stay untouched).

## 2. Disconnect guard moves to the rules layer

- [x] 2.1 `world/rules/possession.py::release_on_disconnect`: add the guard as the first step —
  scan `account.sessions.all()` and return without releasing when any live session's puppet
  carries a non-null `db.possessed_by`; delete the dead `ObjectDB.objects.filter(db_account=...)`
  sweep (companion NPCs are never account-owned; `_account_characters` + the session scan keep
  coverage). Keep the per-char `release_possession(char, reason="disconnect")` loop and its
  warn-on-failure shape.
- [x] 2.2 `typeclasses/accounts.py::at_post_disconnect`: reduce to `super()` + single
  `release_on_disconnect(self)` call — drop the inline `is_connected` scan/skip block
  (:205-215). Update the docstring to name the rules-layer guard.
- [x] 2.3 Tests: (a) UPDATE the three existing disconnect pins to the TRUE disconnect shape —
  `ServerSession.at_disconnect` unpuppets the departing session BEFORE `at_post_disconnect`
  fires (verified: serversession.py:155-171) — so before calling the hook/rules function, clear
  the departing session's puppet (or drop it from `account.sessions`):
  `test_possession_transition.py:155-182` (final-disconnect leg), `:352-369` (single-session
  disconnect), `test_possession.py:338-348` (direct-call idempotence). Keep the auxiliary-session
  leg of :155-182 as-is (a second NPC-puppeting session present → no release).
  (b) ADD direct `release_on_disconnect` pins for the two new scenarios with OBSERVABLE
  postconditions, not call-observation: still-driven case → assert both mirrors, the lock grant,
  and the surviving session's puppet are ALL unchanged; last-driver-gone case → assert both
  mirrors clear, grant stripped, account puppeting nothing. Also pin the count-based property:
  a second session puppeting an ORDINARY character does not block release.
  (c) Annotate with `covers_requirement` on the MODIFIED disconnect requirement's canonical ID
  (`tools.spec_traceability list`).

## 3. Transfer ladder ordering

- [x] 3.1 `world/rules/possession.py::_transfer_puppet`: restructure into the three D-R3 phases —
  empty-session refusal FIRST (no grant attempted); retire/send/reset loop over ALL acting
  sessions; `_grant_puppet_lock` ONCE after every retire; then the existing per-session
  access/puppet/verify ladder with unchanged `_strip_puppet_lock` recovery. Do NOT interleave
  grant between per-session retires.
- [x] 3.2 Ordering pin: patch `web.webclient.actions.dispatcher.retire_sequence` and
  `world.rules.possession._grant_puppet_lock` with call-order recorders on a **two-session**
  fixture (second session via the same `account.sessions.all` patching idiom the multisession
  disconnect test uses); assert the single grant lands after ALL retires, and that the
  no-sessions refusal never calls the grant at all. A one-session fixture passes vacuously for
  the interleaving bug — use two. Pin lands in
  `world/rules/tests/test_possession_transition.py` next to the ladder tests.

## 4. Presentation docstring debris

- [x] 4.1 `web/webclient/presentation/affordances.py::_service_entry` (:453-484): lift the
  stranded paragraph (:468-484) to directly under the `def` line so it is the function's
  docstring; the possessed-actor guard stays the first statement. Zero logic change — confirm
  with the existing service-affordance presentation tests only (no new test).

## 5. Gates

- [x] 5.1 Focused suite: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
  test_settings.py --keepdb world.rules.tests.test_possession world.rules.tests.test_possession_transition
  commands.tests.test_possess_commands web.webclient.presentation.tests` plus the
  service-gate/shop/guild command tests touched by prose-unchanged checks
  (`world.rules.tests.test_service_gate commands.tests.test_guild_economy_commands`).
- [x] 5.2 `uv run --locked python -m tools.spec_traceability check` green; no shard-manifest
  change (no new Python module files).
