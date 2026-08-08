# affinity-ai

## Why

The `adjust_relation` NPC dialogue intent has been whitelisted since `npc-dialogue` but
forward-declared: the AI can express the desire to raise the player's affinity, but the
deterministic engine rejects it (`world/rules/npc_intents.py`). The affinity foundation
(`affinity-system`) now provides the sole-writer API and the capped `ai_dialogue` source, so this
change makes the AI's affinity decisions real: the dialogue prompt shows the NPC its true affinity
toward the player (value, cap, stage), and a validated `adjust_relation` delta of 0–10 is applied
through the deterministic writer, bounded by the daily budget, with the speech always kept.

## What Changes

- **Activate `adjust_relation` in the dialogue schema.** The intent kind's payload contract gains
  exactly one field, `delta`, a non-negative integer bounded to 0–10; the output jsonschema and a
  per-kind semantic validator enforce the bound, so an out-of-range delta is retried, never passed
  to the engine.
- **Apply the delta through the deterministic writer.** `world/rules/npc_intents.py` routes
  `adjust_relation` to `apply_affinity_change(npc, player, "ai_dialogue", delta)` from
  `affinity-system`. An applied delta changes affinity; a delta blocked by the daily budget, an
  out-of-range payload, or a non-NPC target is discarded as an intent while the speech is kept —
  the world is never changed by an intent the NPC could not perform. The numeric cap is never
  rendered to the player.
- **Inject affinity context into the dialogue prompt.** `build_npc_dialogue_prompt` gains an
  affinity context block (`player.affinity = {"value", "cap", "stage"}`) in the user payload,
  capped by the same per-field bounds as every other input; `LLMNPC.at_talked_to` reads the NPC's
  own affinity record for the speaking player through the relations handler (read-only, never
  persisting, omitted for recordless players) and passes it in. Identical input stays
  byte-identical.
- **Keep the numbers out of player-facing speech.** A new no-leak semantic validator rejects a
  reply whose speech echoes the affinity value or cap as a decimal integer substring, retries it
  within the budget, and degrades to greeting/silence rather than present the leak; stage names
  remain the sanctioned player-facing form.
- **Apply the delta through the deterministic writer.** `world/rules/npc_intents.py` routes
  `adjust_relation` to `apply_affinity_change(npc, player, "ai_dialogue", delta)` from
  `affinity-system`. The applier reports the actually applied amount (`IntentOutcome.delta_used`):
  a partially budget-applied delta is reported as applied, while a fully blocked, out-of-range, or
  malformed delta is discarded as an intent with the speech kept — the world is never changed by
  an intent the NPC could not perform. The numeric cap is never rendered to the player.
- **Teach the system prompt to use affinity.** The `npc_dialogue.system` prompt-library template
  gains guidance telling the NPC to use the affinity values when choosing a `delta` (the
  suggested range 0–10) and to treat the numbers as secrets — prompt text is library data, applied
  at apply time, with the module code unchanged in contract.
- **Offline behavior unchanged.** With the LLM offline the layer degrades exactly as before; no
  affinity is changed and no network call is made.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `npc-dialogue`: Four requirements change — the prompt contract injects the affinity context
  block; the intent-shape contract gains `adjust_relation`'s bounded `delta` payload; the
  application contract activates `adjust_relation` through the sole-writer affinity API (with the
  forward-declared rejection narrowing to `offer_quest` / `reveal_lore`); and the `LLMNPC` seam
  passes the NPC's own affinity context into the prompt.
- `prompt-library`: no requirement change — the `npc_dialogue.system` template text is data
  edited at apply time through the existing single-source-of-truth contract.

## Impact

- **New code**: `world/ai/tests/` and `world/rules/tests/` cases for the bounded delta validator,
  the applier, the prompt block, and the read-only seam injection; a `FakeLLMClient` replay for an
  `adjust_relation` reply.
- **Modified**: `world/ai/npc_dialogue.py` (schema + validator + prompt builder),
  `world/rules/npc_intents.py` (applier), `typeclasses/npcs.py` (seam context), the
  `npc_dialogue.system` prompt-library template (data).
- **Dependencies**: `affinity-system` (the writer and closed source set), `npc-dialogue`,
  `llm-client`, `prompt-library`.
- **Out of scope**: the `party_invite` intent (change `party-core`), affinity decrease events, cap
  breaks, and any player-visible numeric affinity display.
