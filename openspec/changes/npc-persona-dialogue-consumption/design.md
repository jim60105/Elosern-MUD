## Context

See proposal.md for motivation. `typeclasses/npcs.py::LLMNPC.run_npc_exchange` appends the player line, arms the thinking timer, builds persona blocks (`_persona_block` → `PersonaStore.flatten(NPC_PERSONA_FIELDS)`), yields `generate_npc_reply`, cancels the timer in `finally`, and appends the NPC reply to memory before returning `DialogueExchangeResult(degraded, reply)`. `at_talked_to` maps a degraded result to `greeting_for(self)` or silence, records the session line via `settled_line` only when `intent_context_ok`, and applies the intent with the separated-context gate. `explore.party_invite` and `commands/invite.py` call `run_npc_exchange` directly and apply the fixed threshold on a degraded result. `world/rules/dialogue.py::table_response` returns `NO_UNDERSTANDING_LINE` for unknown keywords. The `npc_dialogue.system` template prepends `{persona}` and must stay byte-identical when it is empty. The foundation's metadata carries `persona_version` and `provenance`.

## Goals / Non-Goals

**Goals:** the prompt reads the full current card; deterministic per-profile fallback voice on scripted and offline paths.

**Non-Goals:** LLM paraphrase or recompilation of scripted lines (rejected by the product design); changing `explore.talk_open`; changing the player persona view; the persona-version gate (`npc-persona-dialogue-version-gate`).

## Decisions

### D1. Field set and frame

`NPC_PERSONA_FIELDS = NPC_CARD_RENDER_ORDER` (imported from `world/lore/npc_card.py`; `world/ai` may import lore). When the flattened block is non-empty, `_system_message` renders `npc_dialogue.persona_frame` with `block=<flattened>` and passes the result as `persona`; when empty it passes `""`, preserving byte-identity. The frame text lives only in `prompts/npc_dialogue.yaml` (Traditional Chinese), e.g. a heading such as 「以下是你目前的人物設定，之後的回應以此為準；先前對話與已發生的事件仍是歷史，不因設定改變而改寫。」 followed by `{block}` and a blank line. NPCs whose stored persona is not a card (players are never the speaking NPC; legacy dev data before the cutover) still flatten tolerantly through `PersonaStore`.

### D2. Read-only provenance helper

`provenance_profile_key(npc) -> str | None` reads `db.npc_persona_meta` without writing or repairing (malformed meta → `None`).

### D3. Voice routing is instance-field-first and read-only

`misunderstood_line_for(npc)` and `offline_greeting_for(npc)` live in `world/rules/dialogue.py`. `offline_greeting_for` is the single greeting resolver for every no-keyword and degraded presentation path, in order: (1) the NPC's own persisted `db.npc_offline_greeting` field — a bounded per-instance greeting seeded at build by the companion builder under the `npc-persona-companion-profiles` amendment and author-editable through the persona editor — wins verbatim when non-empty, overriding table and profile defaults; (2) the dialogue-table greeting via the existing `greeting_for` lookup; (3) the profile greeting through `provenance_profile_key(npc)` — absent → `None`; present but missing from `NPC_PROFILE_REGISTRY` → `log_error("npc_voice_profile_missing", context={"npc", "profile"})` and `None`; present → the profile's `greeting` when authored, else `None`. The `talk` command's no-keyword path routes through `offline_greeting_for` instead of `greeting_for` alone, and the `explore.talk_open` adapter takes its session line from `offline_greeting_for`, falling back to the fixed server-authored fallback line only when it resolves to nothing (design §13a: the author-editable offline first line follows the editor on every no-keyword surface, including the dialogue panel opened by `explore.talk_open`; the `webclient-exploration-menu` delta specifies the adapter change). `greeting_for` remains the pure table lookup used as step 2 and by `default_greeting` presentation in the editor; the `webclient-dialogue-session` wording ("the host's greeting") already covers whatever the resolver returns and needs no delta. `table_response` gains the NPC argument path through `dialogue_response` (unknown keyword → `misunderstood_line_for(npc)`, provenance-only — the instance field never answers keywords); the missing-table branch keeps the shared line. The degraded branch of `at_talked_to` uses `offline_greeting_for(self)`. Profile voice lines and scripted table lines are immutable lore: card edits and field clears fall back to them, never rewrite them.

### D4. Events

`npc_voice_profile_missing` (error: `npc`, `profile`), added to the catalog §4.2.

## Risks / Trade-offs

- [Shipped NPCs show no per-profile voice until producers/cutover land] → expected; synthetic-profile tests prove the routing now.
- [A companion's greeting could also be reachable via its partner preset] → the instance field is the sole read source: the built NPC detaches from the template at build, so dialogue never resolves a preset key, and a later preset edit never changes an already-built companion.
- [An author override hides a service-critical table greeting permanently] → the override is author-visible in the editor (empty the field to restore the default), affects only the no-keyword path, and keyword answers (including guild 回報 service guidance) are structurally unreachable from it.
