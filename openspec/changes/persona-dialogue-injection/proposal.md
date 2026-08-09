# persona-dialogue-injection

## Why

NPCs with persona data (imported characters today, creation-generated characters in the future)
have no voice: the dialogue prompt is built from name/desc/location only, so a card's personality,
life story, and habits never reach the LLM. The persona-store change supplies the handler; this
change consumes it so NPCs speak in character and recognize their conversation partner — while the
reply validator's secret set grows to cover disguised true traits, closing the D2 display-layer
leak contract.

## What Changes

- Extends the `npc_dialogue.system` prompt template with a `{persona}` placeholder and registers
  it in the prompt-library allowlist.
- Injects the NPC's own persona block into the system message and the player character's persona
  block into the user payload (`player.persona`), both built through `PersonaStore.flatten()`.
- Generalizes the per-call no-leak validator from affinity-only to a bounded secret set:
  affinity value/cap plus true trait values under an active disguise; a reply echoing any bound
  secret is rejected/retried/degraded exactly as today.
- Wires the persona blocks and secret set through `LLMNPC.at_talked_to` (read-only), keeping
  `world/ai/` free of typeclass and writer imports.
- Keeps degradation unchanged: offline dialogue falls back to greeting/silence; missing persona
  produces byte-identical prompts to today.

## Capabilities

### New Capabilities
- `persona-dialogue-injection`: persona blocks in the NPC dialogue prompt (NPC persona in the
  system message, player persona in the user payload) and the generalized no-leak validator with
  disguise true-value secrets.

### Modified Capabilities
- `npc-dialogue`: the dialogue seam's prompt construction gains persona injection and the extended
  secret set (requirement-level behavior change).
- `prompt-library`: the `npc_dialogue.system` key gains the `persona` placeholder in its
  allowlist.

## Impact

- `world/ai/npc_dialogue.py`: `_system_message` and `build_npc_dialogue_prompt` accept persona
  blocks; `_make_no_affinity_leak_validator` generalizes to a secret-set factory (affinity calls
  keep their current two-secret binding).
- `typeclasses/npcs.py`: `at_talked_to` / `run_npc_exchange` supply persona blocks and the
  disguise secret set (read-only, like the affinity context today).
- `world/prompts/registry.py` + `prompts/npc_dialogue.yaml`: `persona` placeholder allowlist and
  template text.
- No new transport, schema, or degradation path; no player-facing surface change.
