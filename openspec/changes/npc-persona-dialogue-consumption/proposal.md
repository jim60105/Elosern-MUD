## Why

The NPC prompt reader selects six persona fields and has no speech style, scripted hosts all share one misunderstanding line, offline free-form NPCs without a table fall silent, and an asynchronous dialogue exchange built from an old card can settle after the card was edited and still speak, write memory, and apply intents. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §4.2, §7.1, §7.2, §11.1 cases 8–9) requires the prompt to read the complete current card with explicit speech style and a current-versus-history frame, scripted and offline paths to use the authored per-profile voice lines deterministically, and a persona-version completion gate across every consumer of the exchange seam.

## What Changes

- The NPC prompt flattens the card in the contract's render order (seven fields, `speech_style` beside `personality`), wrapped by a new prompt-library key `npc_dialogue.persona_frame` that marks the card as the current setting and earlier conversation as unrewritten history. The player's public-only view is unchanged.
- Voice routing (read-only, no LLM): an unknown keyword on a scripted host returns the misunderstanding reply of the profile named in the host's persona provenance, else the shared line; the degraded generative path presents the table greeting, else the provenance profile's greeting, else silence. A dangling provenance key is a logged integrity failure that falls back to the shared/neutral line, never a fabricated voice. `explore.talk_open`'s greeting and narration fallback are unchanged.
- Persona-version completion gate: `run_npc_exchange` captures the NPC's `persona_version` when it builds the prompt and compares at settlement; any inequality yields a new stale-persona terminal (`DialogueExchangeResult.stale_persona`) that suppresses speech, NPC memory append, intent application, session-line recording, and the degraded invite threshold, settles with one localized explanation, and never retries. Wired through `at_talked_to`, `explore.talk_freeform`, `explore.party_invite`, and the text `invite` command.
- Operational events: `npc_dialogue_stale_persona` (NPC, character, captured and current version, consumer path) and `npc_voice_profile_missing` (NPC, profile key).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `persona-dialogue-injection`: the NPC block uses the card render order with speech style and the current-setting frame.
- `scripted-dialogue`: unknown keywords use the provenance profile's misunderstanding reply; card edits never rewrite scripted lines.
- `npc-dialogue`: the offline degrade uses the profile greeting when no table greeting exists (MODIFIED); ADDED persona-version completion gate across all exchange consumers.
- `prompt-library`: ADDED registration of `npc_dialogue.persona_frame`.

## Impact

- Code: `world/ai/npc_dialogue.py` (field set, frame rendering), `prompts/npc_dialogue.yaml`, `world/prompts/registry.py`, `typeclasses/npcs.py` (version capture/compare, stale result, offline greeting), `world/rules/dialogue.py` (voice routing), `world/rules/npc_persona.py` (read-only `current_persona_version` and `provenance_profile_key` helpers; no writer change), `world/rules/player_messages.py` (stale-persona explanation), `web/webclient/actions/exploration_actions.py` (talk_freeform and party_invite mapping), `commands/invite.py`.
- Tests: `typeclasses/tests/`, `world/rules/tests/test_dialogue.py`, `world/ai/tests/`, `world/prompts/tests/`, `web/webclient/actions/tests/`, `commands/tests/` (package-owned shard labels except `world/rules/tests`, already registered).
- Observability catalog rows for the two new events.

## Batch:

depends-on: npc-persona-card-foundation
depends-on: npc-persona-profile-registry

Code-conflict notes: sole editor in this batch of `typeclasses/npcs.py`, `world/ai/npc_dialogue.py`, `prompts/npc_dialogue.yaml`, `world/prompts/registry.py`, `world/rules/dialogue.py`, and `commands/invite.py`. `web/webclient/actions/exploration_actions.py` is edited here only (the editor change puts its adapters in a new module and only imports the shared presence resolver). `world/rules/npc_persona.py` gains two read-only helpers here and the cutover's writer suspension later — distinct functions, mechanical rebase at most. Voice lines become observable on shipped NPCs only once producers and the cutover write profile provenance; behavior tests use synthetic profiles and do not wait for content. Shared append-only: observability catalog, `.github/evennia-shards.json` (only for a new `world/rules/tests` module).
