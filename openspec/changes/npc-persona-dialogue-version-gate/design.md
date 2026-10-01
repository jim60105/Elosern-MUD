## Context

See proposal.md for motivation. `typeclasses/npcs.py::LLMNPC.run_npc_exchange` appends the player line, arms the thinking timer, builds persona blocks, yields `generate_npc_reply`, cancels the timer in `finally`, and appends the NPC reply to memory before returning `DialogueExchangeResult(degraded, reply)`. `at_talked_to` maps a degraded result to a greeting or silence, records the session line through `settled_line` only when `intent_context_ok`, and applies the intent with the separated-context gate. `explore.party_invite` (`_render_invite_outcome`) and `commands/invite.py` call `run_npc_exchange` directly and apply the fixed threshold on a degraded result. The foundation's metadata carries `persona_version`.

## Goals / Non-Goals

**Goals:** no stale reply reaches the player, memory, intents, the session, or the invite threshold after a card change; one shared mechanism for every consumer.

**Non-Goals:** retrying stale exchanges; undoing committed speech or effects; prompt or voice changes (`npc-persona-dialogue-consumption`).

## Decisions

### D1. Capture and compare on the reactor thread

`current_persona_version(npc) -> int | None` reads `db.npc_persona_meta` without writing (malformed → `None`). `run_npc_exchange` captures it synchronously before the yield (where the persona blocks are built) and re-reads it synchronously after the reply or degrade resolves. The editor writer also runs on the reactor thread, so no save interleaves inside that synchronous segment. Version inequality — not prose equality — decides, so change-and-revert still invalidates.

### D2. Stale-persona is a third terminal, checked before every effect

`DialogueExchangeResult` gains `stale_persona: bool = False`. On inequality `run_npc_exchange` returns `DialogueExchangeResult(degraded=False, reply=None, stale_persona=True)` without appending the NPC reply to memory and emits `npc_dialogue_stale_persona` (info: `npc`, `char`, `version_from`, `version_to`, `path`). `at_talked_to` checks `stale_persona` first: it sends `STALE_PERSONA_NOTE`, never calls `settled_line`, never applies an intent, and returns a module-level `STALE_PERSONA` sentinel. `_talk_freeform_adapter` maps the sentinel to a rejected result with code `stale_persona` and the same message (surfaced once; the dialogue panel line is unchanged). `_render_invite_outcome` and `commands/invite.py` check `stale_persona` before the degraded-threshold branch and report the explanation without any join, refusal line, or affinity read. The thinking timer is already cancelled in `finally`; no retry is scheduled. The separated-context gate stays in force for non-stale results.

## Risks / Trade-offs

- [Players lose a reply after editing mid-conversation] → intended; the explanation tells them to speak again; nothing is retried automatically.
- [Overlap with dialogue-consumption in `typeclasses/npcs.py`] → distinct functions/branches; sequence the two applies or rebase.
