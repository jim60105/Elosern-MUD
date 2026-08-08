# party-core

## Why

The affinity foundation (`affinity-system`) and the AI-judged affinity deltas (`affinity-ai`) are
in place, and the party auto-leave recheck hook waits unused. Players still cannot turn their
relationships into companionship. This change delivers the party's heart: the `invite` / `leave`
commands, the AI-judged invitation (with the fixed-threshold offline fallback), the bounded
membership binding (up to 4 NPC companions), and the bidirectional dismissal — including the
auto-leave rule that ends a party when affinity drops below the invite threshold. Movement follow,
joint combat, and quest assistance build on this binding in later changes.

## What Changes

- **New `party-system` capability: membership binding.** `world/rules/party.py` owns
  `join_party(npc, player)` / `leave_party(npc, player, reason)` / `purge_npc_memberships(npc)`
  as the sole writers of `player.db.party` (list of NPC dbids, max 4) and `npc.db.party_member`
  (player dbid). Joining requires co-location, an NPC target, not already a companion, and a
  non-full party; both writes commit atomically and persist across reloads. Deleting an NPC
  purges its bindings through the typeclass deletion hook, so companion slots are never consumed
  by deleted entities and stale dbids read as absent companions.
- **New `invite` command.** `invite <npc> [訊息]` (aliases 邀請 / 組隊) resolves the target like
  `talk`, preflights the deterministic gate, then runs a structured dialogue exchange (`reply` vs
  `degraded`) with the player's invitation message and the NPC's affinity context (already
  injected by `affinity-ai`). A `party_invite {accept: bool}` intent is verified and applied
  through `join_party`; any other or illegal intent keeps the speech and changes nothing; a
  rejected join (full party, duplicate, remote) surfaces a distinct Traditional Chinese message.
  Only on the `degraded` terminal does the invitation fall back to the fixed threshold
  (`affinity >= 70`, the 羈絆 stage) — an AI decision is never overridden by the threshold. The
  webclient offers the same flow with the injected client, registered through the action registry,
  exploration presenter, protocol validators, and UI affordances.
- **New `leave` command.** `leave <npc>` (alias 解散) dismisses a companion through
  `leave_party(reason="dismissed")` with no affinity change.
- **Activate the auto-leave hook.** The recheck installed by `affinity-system` now checks the
  companion binding after every negative affinity delta, fires
  `leave_party(reason="affinity_below_threshold")` inside the affinity write's transaction (a
  failed leave rolls back the whole operation), and notifies the player only after commit.
- **Eighth dialogue intent.** The npc-dialogue whitelist grows from seven to eight kinds with
  `party_invite`; the schema, a per-kind shape validator (`{accept: bool}` exactly), and the
  deterministic applier all enforce and route it.
- **Command surface docs.** `docs/game/commands.md` and `docs/game/command-reference.md` gain
  `invite` / `leave` entries per the command-docs contract.

## Capabilities

### New Capabilities

- `party-system`: The membership binding (storage, `join_party` / `leave_party`, bounds,
  atomicity, persistence), the `invite` command and webclient action with the AI-judged /
  threshold-fallback decision, the `leave` command, the auto-leave rule triggered by negative
  affinity deltas, and the party-aware player feedback.

### Modified Capabilities

- `npc-dialogue`: The whitelist grows to eight kinds; `party_invite` gains its `{accept: bool}`
  shape validation; the application contract routes `party_invite` through `join_party` with full
  deterministic re-verification.
- `affinity-system`: The auto-leave recheck hook requirement changes from "verified no-op" to the
  wired rule (below-threshold negative deltas end the party and notify).

## Impact

- **New code**: `world/rules/party.py`, `commands/invite.py`, `commands/leave.py`, a webclient
  `explore.party_invite` / `explore.party_leave` action pair (or one shared adapter), and the
  matching test modules.
- **Modified**: `world/rules/npc_intents.py` (party_invite path), `world/ai/npc_dialogue.py`
  (whitelist + validator), `world/rules/affinity.py` (hook wiring), `commands/default_cmdsets.py`
  (mount `invite` / `leave`), `docs/game/commands.md`, `docs/game/command-reference.md`,
  `tests/test_command_docs.py` (updated expectations).
- **Dependencies**: `affinity-system` (writer, stage ladder, hook), `affinity-ai` (affinity prompt
  context, merged intent-shape text), `npc-dialogue`, `llm-client`, `prompt-library`,
  `game-command-docs`.
- **Out of scope**: movement follow (`party-follow`), joint combat (`party-combat`), quest
  assistance and the +2 completion bonus (`party-quest`), affinity decrease events, cap breaks.
