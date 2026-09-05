# Proposal: companion-possession-transition

## Why
The possession core (change `companion-possession-rules`) deliberately ships state, gates, and
release ordering with two named no-op seams — `_transfer_puppet` and `_mount_cmdset` — because
the control transfer is the riskiest hop and deserves its own change: it rides Evennia's
`puppet_object`, whose silent-refusal branches and recovery ladder the multichar switcher line
already researched and hardened (design doc §11 amendments: verify `get_puppet(session) is
target` after a silent refusal, the recovery ladder, `retire_sequence` + epoch-bump ordering).
This change replaces the seams with real control transfer: possession becomes playable on the
text surface.
Source design: `docs/superpowers/specs/2026-09-05-companion-possession-design.md` (D3, D4, D7,
§3 state machine, §5 recovery rows).

## What Changes

- `_transfer_puppet` becomes real: retire/epoch helpers → dynamic lock grant
  `puppet:id(<account>)` on the NPC → `account.puppet_object(session, npc)` for the acting
  session → verify `get_puppet(session) is npc`, on silent refusal run the recovery ladder
  (re-puppet A, clear lock, restore mirrors, raise) → A's puppet released through the same
  unpuppet path OOC 離開角色 uses (so `at_post_unpuppet` fires once for A — the accepted
  epithet rest-point nomination, per the multichar §Consequences precedent, is NOT suppressed).
- `_mount_cmdset` becomes real: the trimmed character cmdset (movement, look, actions, out-of-
  combat act surface) mounts on the possessed NPC via the existing derive pattern; removed on
  release.
- `release_possession` reverses the order: unpuppet B (releasing locks), re-puppet A on the same
  session with the verify-then-recover ladder, cmdset removal, mirror clear.
- The disconnect release wires on **`Account.at_post_disconnect`**, NOT
  `PlayerCharacter.at_post_unpuppet`: verified against Evennia 6.1, `at_post_unpuppet` fires on
  EVERY deliberate unpuppet (`Account.unpuppet_object` → `obj.at_post_unpuppet`,
  `evennia/accounts/accounts.py:577`) including possession's own release of A — wiring there
  would clear the fresh mirrors mid-possession; `at_post_disconnect` fires only from
  `ServerSession.disconnect()` (`evennia/server/serversession.py:171`), never on puppet swaps
  or reload. The call is account-keyed (scans the account's characters for `db.possession`),
  performs the session handback when the dropping session still puppets the possessed NPC, and
  reloads survive because state is persisted and puppet re-adoption is Evennia's own
  session-restore path. This removes the change's only edit to `typeclasses/characters.py`'s
  switcher-owned hook entirely.
- A possessed A renders as entranced in room prose (the display hook reads
  `player.db.possession`).

## Capabilities

### New Capabilities

- `companion-possession-transition`: puppet transfer with lock grant/revocation, cmdset
  mount/unmount, the verify-then-recover ladder at every hop, and the disconnect hook wiring.

### Modified Capabilities

None — this change replaces seams that `companion-possession-core`'s requirement explicitly
delegates to it; no shipped requirement text changes.

## Impact

- `world/rules/possession.py` (seam bodies), `typeclasses/npcs.py` (cmdset derive for possessed
  NPCs), `typeclasses/characters.py` (vacant rendering only), `typeclasses/accounts.py`
  (`at_post_disconnect` wiring), the landed session helpers
  `web/webclient/actions/dispatcher.py::retire_sequence` (retire) +
  `web/webclient/presentation/ingress.py::reset_client_sequence` (epoch bump + actor-binding
  reset) + `ingress.py::send_unpuppet_transition` (browser clear signal).
- Depends on: `companion-possession-rules`. Code conflicts: `typeclasses/characters.py`
  edits are rendering-only, disjoint from the multichar switcher's `at_post_unpuppet` turf;
  still land after multichar-03 (the shared helpers' epoch semantics it codified).
- No new player commands (附身/歸位 already landed; behavior deepens), no docs change (surface
  unchanged), no webclient surface yet.

## Sizing

At the limit of a single engineer day (real-session puppet tests dominate). If execution exceeds
a day, the split point is §1–§2 (transfer ladder + cmdset) before §3–§4 (disconnect hook,
entranced rendering, tests): the seam stays safe at rest because the rules change's release
ladder is idempotent, but do NOT deploy partway — possession without the disconnect hook leaks
live puppet state across sessions. One change, ordered landing.
