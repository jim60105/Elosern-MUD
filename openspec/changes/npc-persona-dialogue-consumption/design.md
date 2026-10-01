## Context

See proposal.md for motivation. `typeclasses/npcs.py::LLMNPC.run_npc_exchange` appends the player line, arms the thinking timer, builds persona blocks (`_persona_block` → `PersonaStore.flatten(NPC_PERSONA_FIELDS)`), yields `generate_npc_reply`, cancels the timer in `finally`, and appends the NPC reply to memory before returning `DialogueExchangeResult(degraded, reply)`. `at_talked_to` maps a degraded result to `greeting_for(self)` or silence, records the session line via `settled_line` only when `intent_context_ok`, and applies the intent with the separated-context gate. `explore.party_invite` and `commands/invite.py` call `run_npc_exchange` directly and apply the fixed threshold on a degraded result. `world/rules/dialogue.py::table_response` returns `NO_UNDERSTANDING_LINE` for unknown keywords. The `npc_dialogue.system` template prepends `{persona}` and must stay byte-identical when it is empty. The foundation's metadata carries `persona_version` and `provenance`.

## Goals / Non-Goals

**Goals:** the prompt reads the full current card; deterministic per-profile fallback voice on scripted and offline paths; no stale reply can reach the player, memory, intents, the session, or the invite threshold after a card change.

**Non-Goals:** LLM paraphrase or recompilation of scripted lines (rejected by the product design); changing `explore.talk_open`; changing the player persona view; retrying stale exchanges.

## Decisions

### D1. Field set and frame

`NPC_PERSONA_FIELDS = NPC_CARD_RENDER_ORDER` (imported from `world/lore/npc_card.py`; `world/ai` may import lore). When the flattened block is non-empty, `_system_message` renders `npc_dialogue.persona_frame` with `block=<flattened>` and passes the result as `persona`; when empty it passes `""`, preserving byte-identity. The frame text lives only in `prompts/npc_dialogue.yaml` (Traditional Chinese), e.g. a heading such as 「以下是你目前的人物設定，之後的回應以此為準；先前對話與已發生的事件仍是歷史，不因設定改變而改寫。」 followed by `{block}` and a blank line. NPCs whose stored persona is not a card (players are never the speaking NPC; legacy dev data before the cutover) still flatten tolerantly through `PersonaStore`.

### D2. Read-only helpers on the persona service

`current_persona_version(npc) -> int | None` and `provenance_profile_key(npc) -> str | None` read `db.npc_persona_meta` without writing or repairing (malformed meta → `None`). `run_npc_exchange` captures `current_persona_version(self)` synchronously before the yield (same point the persona blocks are built) and re-reads it after the reply or degrade resolves.

### D3. Stale-persona is a third terminal, checked before every effect

`DialogueExchangeResult` gains `stale_persona: bool = False`. After the yield, if the captured and current versions differ (including `None` → int), `run_npc_exchange` returns `DialogueExchangeResult(degraded=False, reply=None, stale_persona=True)` without appending the NPC reply to memory, and emits `npc_dialogue_stale_persona`. `at_talked_to` checks `stale_persona` first: it sends the stale explanation (`player_messages.STALE_PERSONA_NOTE`), never calls `settled_line`, never applies an intent, and returns a module-level `STALE_PERSONA` sentinel. `_talk_freeform_adapter` maps the sentinel to a rejected result with code `stale_persona` and the same message (the dispatcher surfaces it once; the dialogue panel line is unchanged because the session was not refreshed). `_render_invite_outcome` and `commands/invite.py` check `stale_persona` before the degraded-threshold branch and report the explanation without any join, refusal line, or affinity read. The thinking timer is already cancelled in `finally`; no retry is scheduled anywhere. The separated-context gate stays in force for non-stale results.

### D4. Voice routing is provenance-based and read-only

`misunderstood_line_for(npc)` and `offline_greeting_for(npc)` live in `world/rules/dialogue.py`: resolve `provenance_profile_key(npc)`; absent → shared line / `None`; present but missing from `NPC_PROFILE_REGISTRY` → `log_error("npc_voice_profile_missing", context={"npc", "profile"})` and shared line / `None`; present → the profile's `misunderstood` / `greeting` when authored, else shared line / `None`. `table_response` gains the NPC argument path through `dialogue_response` (unknown keyword → `misunderstood_line_for(npc)`); the missing-table branch keeps the shared line. The degraded branch of `at_talked_to` uses `greeting_for(self) or offline_greeting_for(self)`. `greeting_for` itself (used by `explore.talk_open` and the `talk` command) is unchanged. Voice lines come from the immutable profile, so card edits never change them.

### D5. Events

`npc_dialogue_stale_persona` (info: `npc`, `char`, `version_from`, `version_to`, `path` ∈ {`talk`, `invite`}) and `npc_voice_profile_missing` (error: `npc`, `profile`). Added to the catalog §4.3/§4.2.

## Risks / Trade-offs

- [The stale check races a save landing between the re-read and presentation] → both run on the reactor thread synchronously after the yield; the editor writer also runs on the reactor thread, so no interleaving exists inside that synchronous segment.
- [Players lose a reply after editing mid-conversation] → intended; the explanation tells them to speak again; nothing is retried automatically.
- [Shipped NPCs show no per-profile voice until producers/cutover land] → expected; synthetic-profile tests prove the routing now.
