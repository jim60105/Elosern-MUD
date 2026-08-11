## Context

The freeform adapter (`web/webclient/actions/exploration_actions.py:407-424`) checks presence and `interaction_reason(npc, "talk")` before calling `npc.at_talked_to`; `at_talked_to` (`typeclasses/npcs.py:337-349`) re-checks before `yield`-ing the LLM call, then `run_npc_exchange` resumes at `npcs.py:349-359` and calls `apply_npc_intent` (`world/rules/npc_intents.py`) with no post-yield checks. `party_invite`/`request_guild_exam` re-verify inside their own flows; `adjust_relation`, `reveal_lore`, `give_item`, `take_item` do not.

## Goals / Non-Goals

**Goals:**
- No intent applies after separation or busy-state transition.
- One shared completion gate for all intent kinds.

**Non-Goals:**
- Cancelling in-flight LLM calls.
- Changing the speech/presentation of replies.

## Decisions

**D1 — Shared completion gate in `apply_npc_intent`.** Add a required `context_ok` predicate (co-location + `interaction_reason(npc, "talk") is None`) evaluated at the top of the intent application seam; a failure returns a stable stale-completion result and skips the intent. Per-kind domain checks stay untouched below the gate.

**D2 — Surface stale completions to the player.** `at_talked_to` renders the speech and, when the gate fails, appends a short "對方已經離開／現在無法交談" note instead of applying the intent; the Web adapter returns the same outcome.

**D3 — No change to synchronous flows.** The gate is a no-op when the checks pass, preserving current co-located behavior; pre-call checks remain as an early fast-path.

## Risks / Trade-offs

- **LLM cost on stale replies**: the exchange still completes (speech shown); only mutation is skipped — consistent with the spec's speech-then-intent split.
- **Movement during reply**: rechecking at completion uses canonical state, so it also covers schedule-driven NPC moves that happen mid-exchange.
