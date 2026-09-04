# Proposal: webclient-align-07-dialogue-session-state

## Why

The draft's dialogue presentation (change 08) needs a server truth it cannot observe today:
`talk` replies reach the client only as narrative text, with no record of WHO is being spoken
to, WHAT the latest authored line is, or whether a conversation is live at all.
This change ships only that state layer — a character-held dialogue session written
exclusively by the deterministic core. It is deliberately invisible on its own: the
protocol-visible `dialogue` panel + mode ship in webclient-align-10-dialogue-panel, and the
client surface in webclient-align-08-dialogue-surface. (Split from the original combined
change 07 after rubber-duck review: state contract and protocol contract are independently
shippable and independently testable.)

## What Changes

- **Session state:** persistent `db.dialogue_session` on the character
  (`{npc_id, line, updated_tick}`), written only by the deterministic core seams —
  opened/refreshed by the `explore.talk_scripted` and `explore.talk_freeform` adapter
  success paths (and the `talk` command path), cleared by movement settlement
  (`settle_movement`), by `explore.engage`, and on NPC departure/despawn/leave-party
  cleanup. No client can open or clear it directly.
- **Liveness rule:** a session whose NPC dbid no longer resolves to a present, interactable
  NPC in the character's location is not live; the stale dbid never reaches any presentation.
- **Offline guarantee:** with the LLM disabled, scripted dialogue (`run_scripted_talk`) fully
  drives open/refresh/clear (REDESIGN principle 7); the freeform degrade path (authored
  greeting/silence) also records its line.
- **Observability:** `session_open`/`session_clear` boundary events through the facade.

## Capabilities

### New Capabilities

- `webclient-dialogue-session`: session-state requirement only (panel + mode requirements
  are ADDED by webclient-align-10-dialogue-panel, which chains a MODIFIED of this one).

### Modified Capabilities

- `webclient-exploration-menu`: the `explore.talk_scripted` / `explore.talk_freeform`
  adapters record the session line on their success paths (no other adapter or presenter
  writes it). State-level scenarios only — panel/mode consequences land in change 10.

## Impact

- `world/rules/dialogue.py` (session read/write helpers on the character),
  `commands/talk.py` + `web/webclient/actions/exploration_actions.py` success-path hooks,
  `world/rules/movement_settlement.py` + engage + NPC cleanup clear hooks.
- Observability boundary events on session open/clear per the facade catalog; shard
  manifest + `covers_requirement` for the new server test module.
- No protocol, panel, or client changes (changes 10 and 08 consume this state); no
  player text-command surface changes.
