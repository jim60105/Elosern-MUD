# Design: companion-possession-transition

Source design: `docs/superpowers/specs/2026-09-05-companion-possession-design.md` (D3/D4/D7,
§3, §5). This design covers only the seams that `companion-possession-rules` deliberately left
unimplemented: the puppet transfer, the cmdset mount, the disconnect wiring, and the entrance
rendering. The state machine, gates, and release ordering are settled there.

## D-T1: Reuse the multichar transition ordering through the landed session-level helpers
The switcher (`multichar-03`, landed) solved the exact hazards this change re-traverses: silent
`puppet_object` refusals, retire/epoch ordering, and the `at_post_unpuppet` side effects. The
transition SHALL perform, in order: retire the acting session's in-flight action sequence
(`web/webclient/actions/dispatcher.py::retire_sequence(session)`) AND bump its presentation epoch
via `web/webclient/presentation/ingress.py::reset_client_sequence(session)` — the verified epoch
owner: it re-attaches the coordinator and calls `coordinator.reset()` plus the `ndb` actor-binding
clear (`send_unpuppet_transition` only signals the browser; it bumps nothing) — THEN the puppet
swap, then the transition push (`send_unpuppet_transition(session)`); all three are already
session-level and importable. The contract this ordering enforces: a completion Deferred started
for A's panel can never publish after the swap. Possession calls these directly; no second copy
of the ladder exists outside `possession.py` itself (the verify-`get_puppet`-after recovery ladder
is possession-local because its restore target — A — is possession-specific).

## D-T2: Lock grant is additive and survives; release strips it
Before the first puppet of B, `npc.locks.add("puppet:id(<account id>)")` is ADDED alongside the
default rule — not replacing it. The grant intentionally persists while possession is active so
Evennia's own reload re-adoption path can re-puppet B without a fresh grant. `_release` strips
the grant after B is unpuppeted. Stripping is idempotent (`locks.remove` of an absent rule is a
no-op); a grant orphaned by an unclean crash is harmless — possession attributes are cleared by
the disconnect hook, and `enter_possession` re-adding the same rule is idempotent.

## D-T3: The epithet nomination fires on the possession switch — accepted, not suppressed
`at_post_unpuppet` firing on every switch (including retirement) is already an accepted
consequence in the multichar design, with cooldown making repeated nomination cheap. Possession
entering releases A the same way an OOC switch does, so the rest-point nomination fires once for
A at the room possession began — thematically correct (that is where A stopped). No suppression
flag: fewer moving parts, and the documented consequence already covers it. The disconnect
release path goes through the same hook, so a disconnect while possessing nominates A's current
room exactly once (the possession release itself does not nominate).

## D-T4: Disconnect vs reload is Evennia's distinction, not ours
Verified against Evennia 6.1 sources: `at_post_unpuppet` fires on EVERY
`Account.unpuppet_object` (`evennia/accounts/accounts.py:577`), including deliberate puppet swaps
— possession's own release of A goes through it — so wiring the release there would clear the
fresh mirrors mid-possession. The disconnect-only point is `Account.at_post_disconnect`, fired
solely from `ServerSession.disconnect()` (`evennia/server/serversession.py:171`); when it runs the
session is already detached, so the release helper unpuppets the NPC if a session still holds it
and strips attributes otherwise. The wiring is therefore one line on `Account`:
`at_post_disconnect` calls `possession.release_on_disconnect(self)` (the account-keyed helper
from the rules change, scanning the account's characters for `db.possession`). Clean reload/
restart preserves sessions, fires neither hook, and re-puppets via Evennia's own re-adoption.
Nothing in possession code inspects shutdown state — reload persistence is pinned by a test that
round-trips the attributes through save+re-read, per the design doc's reload-survives row. The
session-reconnect re-puppet leg of re-adoption is Evennia-internal; the integration test exercises
the closest supported path (disconnect → reconnect on a retained grant) and the retained lock
grant is what makes re-puppeting B legal without a fresh mutation.

## D-T5: The mounted cmdset is the character act surface minus a denylist, rebuilt on enter
`LLMNPC.at_pre_puppet` accepts the account (Evennia calls it on the target before puppeting —
the typeclass override exists to permit, not to re-verify; the rules gate already decided).
`_mount_cmdset` builds a fresh derived `CharacterCmdSet`-shaped cmdset for the possessed NPC: the
movement/look/examine/act surface plus `unpossess`/`歸位`, minus an explicit denylist — the
switcher/play/quell family (its retire logic assumes the session puppet is the caller's own
character, which is false mid-possession) and the character-panel commands whose presenters read
PlayerCharacter-only state (`quest_log`, guild rank). Denylist membership is pinned by a test
against the landed `CharacterCmdSet`, not prose. `_unmount_cmdset` restores the NPC's default
cmdset by rebuilding it the same way Evennia's `at_object_creation` path did.

## D-T6: Entranced rendering lives on the typeclass display hook, keyed on the persisted mirror
A's room presence reads as entranced by having `PlayerCharacter`'s room-content display hook
(its `get_display_obvious_content`-side surface) consult `self.db.possession`: non-null appends
the fixed 呆立入神 line, null renders unchanged. No new attributes, no session checks — the
mirror is the truth, and a stale mirror after a crash still reads honestly (A looks entranced
while an orphan state exists, until the next release clears it).

## D-T7: Mid-release failure keeps the possession state and logs
If release unpuppets B but the re-puppet of A silently refuses, the ladder does NOT clear
possession attributes: B is left unpuppeted (no authority), the grant stays (so retry can
re-puppet B or A's grant stays for its own path), the error is logged through the facade with
`step="possession_release"`, and the fixed 「你的身體搖搖欲墜,彷彿從很深的水裡被拉回來。」line is sent.
The player retries 歸位 (idempotent attributes make the retry safe). This is the documented §5
row; silence is the worse failure.

## Cross-change seams
- `companion-possession-rules`: provides the writer, the seam call sites, `release_on_disconnect`,
  and the `restored_possession_surfaces` export this change's tests import.
- `companion-possession-webclient` (8): consumes the banner/panel surfaces this change makes
  real; replaces the server-side epoch reset (webclient-internal) with this transition path.
- multichar-03 (landed): shared ordering; `typeclasses/characters.py` `at_post_unpuppet` is
  edited by both lines — land after it. The possession release hook itself is NOT on that hook
  (D-T4); it lives on `Account.at_post_disconnect`, disjoint from the multichar switcher's turf.
