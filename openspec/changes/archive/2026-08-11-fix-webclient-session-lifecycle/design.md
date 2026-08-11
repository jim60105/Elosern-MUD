## Context

`CmdOOC.func` (`commands/localized/account.py:136-168`) unpuppets and sends text only. The sequence reset in `_coordinator_for` (`web/webclient/presentation/ingress.py:66-83`) fires only when `elosern_actor_id` *changes*; OOC never clears it, `retire_sequence` (`dispatcher.py:88-102`) and `detach_coordinator` (`coordinator.py:216-220`) have no unpuppet caller, and `ui_action` with `actor is None` returns bare (`inputfuncs.py:76-77`) so the client lock (`elosern_actions.js:99-122`) never releases. Terminal combat results attach the same three-panel `AFFECTED_PANELS` as rounds (`combat_result.py:48-50`), while `mode_for` (`coordinator.py:130-137`) flips the envelope mode to exploration; the client reducer replaces only named panels (`protocol.js:3091-3109`).

## Goals / Non-Goals

**Goals:**
- Sequence retirement on the real puppet lifecycle, including same-character repuppet.
- Every client mutation gets a response (success, rejection, or error).
- Mode-changing terminal outcomes carry a complete, fresh presentation.

**Non-Goals:**
- Multi-character puppeting features.
- Changing the OOB wire format beyond the added no-puppet rejection.
- Optimizing snapshot size for terminal outcomes (correctness first).

## Decisions

**D1 — Hook the puppet lifecycle, not the actor-id diff.** OOC sends a client transition BEFORE retiring: a full unavailable snapshot (or dedicated lifecycle envelope) that clears character panels and locks mutations, delivered while the coordinator is still valid. Then OOC calls `retire_sequence(session)` + a new `reset_client_sequence(session)` (coordinator epoch bump + `elosern_actor_id` cleared); IC/repuppet always starts a fresh epoch because the retired state is gone. Keep the actor-id-diff reset as a fallback for non-OOC puppet changes.

**D2 — Bounded no-puppet rejection.** `ui_action` returns a `ui_action_result` envelope with a stable `no_puppet` outcome carrying no character data; the client treats it like any other rejection and releases its lock. The presentation state stays untouched.

**D3 — Terminal outcomes publish a full snapshot.** `settle_to_oob_result` returns an empty `affected_panels` (or a dedicated `full` marker) for terminal outcomes, so the dispatcher's rejection-style full-snapshot path (`dispatcher.py:319-320`) sends all panels at a fresh revision. Non-terminal rounds keep the three-panel update.

## Risks / Trade-offs

- **Full snapshots are heavier**: terminal outcomes are rare (once per fight); acceptable.
- **Client reset signal**: the new no-puppet/full-reset flow needs a client handler; scoped to the existing `ui_action_result`/snapshot paths to avoid a new protocol message type where possible.
- **Browser tests**: combat browser tests boot servers per test; the affected `test_browser_combat*` files must be re-run to confirm the lock-release and panel-freshness behavior.
