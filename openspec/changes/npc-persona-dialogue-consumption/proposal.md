## Why

The NPC prompt reader selects six persona fields and has no speech style, scripted hosts all share one misunderstanding line, and offline free-form NPCs without a table fall silent. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §4.2, §7.1, §11.1 case 9) requires the prompt to read the complete current card with explicit speech style and a current-versus-history frame, and scripted and offline paths to use the authored per-profile voice lines deterministically, with no LLM. (The persona-version completion gate is `npc-persona-dialogue-version-gate`.)

## What Changes

- The NPC prompt flattens the card in the contract's render order (seven fields, `speech_style` beside `personality`), wrapped by a new prompt-library key `npc_dialogue.persona_frame` that marks the card as the current setting and earlier conversation as unrewritten history. The player's public-only view is unchanged.
- Voice routing (read-only, no LLM): an unknown keyword on a scripted host returns the misunderstanding reply of the profile named in the host's persona provenance, else the shared line; the degraded generative path presents the table greeting, else the provenance profile's greeting, else silence. A dangling provenance key is a logged integrity failure that falls back to the shared line, never a fabricated voice. `explore.talk_open`'s greeting and narration fallback are unchanged.
- Read-only `provenance_profile_key(npc)` helper; event `npc_voice_profile_missing` (NPC, profile key).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `persona-dialogue-injection`: the NPC block uses the card render order with speech style and the current-setting frame.
- `scripted-dialogue`: unknown keywords use the provenance profile's misunderstanding reply; card edits never rewrite scripted lines.
- `npc-dialogue`: the offline degrade uses the profile greeting when no table greeting exists.
- `prompt-library`: ADDED registration of `npc_dialogue.persona_frame`.

## Impact

- Code: `world/ai/npc_dialogue.py` (field set, frame rendering), `prompts/npc_dialogue.yaml`, `world/prompts/registry.py`, `typeclasses/npcs.py` (degraded-greeting branch only), `world/rules/dialogue.py` (voice routing), `world/rules/npc_persona.py` (one read-only helper).
- Tests: `typeclasses/tests/`, `world/rules/tests/test_dialogue.py`, `world/ai/tests/`, `world/prompts/tests/` (package-owned except `world/rules/tests`, already registered).
- Observability catalog row for the new event.

## Batch:

depends-on: npc-persona-card-foundation
depends-on: npc-persona-profile-registry

Code-conflict notes: sole editor in this batch of `world/ai/npc_dialogue.py`, `prompts/npc_dialogue.yaml`, `world/prompts/registry.py`, and `world/rules/dialogue.py`. `typeclasses/npcs.py` is also edited by `npc-persona-dialogue-version-gate` (different functions/branches; sequence or rebase mechanically). `world/rules/npc_persona.py` gains one read-only function. Voice lines become observable on shipped NPCs only once producers and the cutover write profile provenance; behavior tests use synthetic profiles. Shared append-only: observability catalog.
