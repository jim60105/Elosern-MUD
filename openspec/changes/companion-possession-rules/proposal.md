# Proposal: companion-possession-rules

## Why

Playing "from the companion's eyes" is architecturally unavailable through two player characters
(party membership is a star model, `join_party` rejects non-NPCs, and every downstream system is
(NPC, player)-keyed). Possession changes **control, not ownership**: the account temporarily
drives its own bound NPC companion while the party model, affinity records, and owner-companion
quest credit survive untouched. This change lands the deterministic core — the possession writer,
its gates, the unified player-driven predicate, and autonomy silencing — with the puppet-transfer
mechanics and webclient surfaces in the two following changes.
Source design: `docs/superpowers/specs/2026-09-05-companion-possession-design.md` (D1, D2, D5,
D6, D8).

## What Changes

- New capability `companion-possession-core`: `world/rules/possession.py`, a party-core-patterned
  single writer — `enter_possession(player, npc)` / `release_possession(player, npc, reason)`
  mirror `pc.db.possession = {npc_dbid, since_tick}` and `npc.db.possessed_by = pc_dbid` inside
  one `transaction.atomic()` with snapshot/restore of both surfaces and stable reason codes
  (`not_bound`, `not_co_located`, `in_combat`, `dialogue_open`, `already_possessing`,
  `write_failed`).
- Deterministic entry gates (D2), ALL before any AI/dialogue work: live bound companion;
  co-located; no active combat session on either side (the existing party-adjustment boundary);
  no open dialogue session for the NPC; no other possession held by the account. Exit-path
  coverage (D8): affinity auto-leave releases inside its own transaction before `leave_party`;
  dismissal of a possessed companion is refused "hand back first"; `purge_npc_memberships`
  unwinds; disconnect release is a seam (`release_on_disconnect(player)` — the puppet-transition
  change wires the unpuppet hook).
- New capability `player-control-predicate`: `world/rules/player_control.py::is_player_driven(
  entity)` — true for a puppeted `PlayerCharacter` OR an NPC with `db.possessed_by`;
  `charge_movement` and the room-entry action-options trigger consult it (the clock's "advances
  only on player action" invariant widens WHO, never WHEN).
- Autonomy silencing (D6): `schedule_silenced` gains its second OR-trigger (possessed NPC),
  `LLMNPC.at_talked_to` refuses the possessed self with the fixed line, and `settle_npc_schedules`
  needs no new branch (it already consults `schedule_silenced`). Quest-observer companion credit
  is deliberately untouched — possessed-B kills still credit A's quests (ratified feature).
- Text commands `附身 <夥伴>` / `歸位` (keys `possess`/`unpossess`, English aliases retained)
  drive enter/release; the puppet transfer itself is the next change — until it lands, enter
  records state and release clears it (guarded seams, no fake puppeting).

## Capabilities

### New Capabilities

- `companion-possession-core`: the possession writer, gate matrix, exit paths, and the
  player-facing command surface.
- `player-control-predicate`: the unified player-driven predicate and its consumers.

### Modified Capabilities

- `movement-cost-charging`: `charge_movement`'s traverser test widens from
  `isinstance(PlayerCharacter)` to `is_player_driven`.
- `action-options-trigger-hooks`: the room-entry trigger fires for a puppeted player-driven
  entity, not only a puppeted `PlayerCharacter`.
- `party-system`: dismissal of a possessed companion is refused until handback.
- `npc-schedule-runtime`: UNCHANGED — the possessed-NPC silence requirement lives in the new
  `companion-possession-core` capability (the shared `schedule_silenced` gate already owns the
  emission contract); the settlement requirement itself is untouched.
- `game-command-docs`: UNCHANGED — the generic "every mounted project command is documented"
  requirement already covers the two new commands; the doc rows are this change's tasks, not a
  requirement edit.

## Impact

- New: `world/rules/possession.py`, `world/rules/player_control.py`, `commands/possess.py`
  (+ localized keys registered in the `tests/test_command_docs.py` curated manifest), their test
  modules; edits in `world/rules/party.py` (auto-leave release, purge), `typeclasses/npcs.py`
  (`LLMNPC.at_talked_to` guard), `world/rules/service_gate.py` (second silence trigger),
  `world/rules/movement.py`, `typeclasses/exits.py` trigger site, `docs/game/*`.
- Depends on: `service-anchor-presentation-silence` (owns `schedule_silenced`). Code conflicts:
  the puppet-transfer change adds hooks into `possession.py`'s entry/release order — this change
  defines the ordering seam; `game-command-docs` delta is shared in shape with the multichar
  series (separate rows, no textual conflict).
- Player-facing command change ⇒ `docs/game/commands.md` + `command-reference.md` update in the
  same change with `tests/test_command_docs.py` green.

## Sizing

Deliberately kept as one change: predicate + writer + party hooks + commands + silencing are one
externally-consistent slice (any earlier seam ships unusable possession state). It is at the limit
of a single engineer day. If execution exceeds a day, land tasks §1–§2 (predicate, writer core,
party hooks) first — the release seams are safe at rest — then §3–§4 (silencing, dialogue gate,
commands, docs) in the same branch before merge; do not split the repo into a third change.
