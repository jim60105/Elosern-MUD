## Why

Generated-quest NPCs (scene occupants) are a production creation path whose characterization carries only an optional `background` and an optional three-field prose block through a restricted proposal schema and the durable compile payload (`world/quests/characterization.py`, `world/quests/compile/*`, `world/quests/scene_builder.py`). The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §6.1 "Generated quests") requires the proposal shape, guardrail validator, deterministic characterization validator, compile contracts, durable payload codec, restore path, and scene materializer to be extended together so every occupant carries a complete compact card that survives compile and restore unchanged and is revalidated at materialization; an invalid LLM card follows the existing bounded failure/degradation path, whose offline template alternative must itself supply complete cards.

## What Changes

- **BREAKING (pre-release, no legacy decoder):** `BlueprintNpcReq` replaces `background` and the three-field `persona` pairs with a required frozen `persona` card; the scenario-director output schema requires the seven-field card object for every `npc_req`; `background` is removed from the proposal, the compile contract, the canonical payload, and the durable codec.
- The shared characterization helper validates the card through the compact card contract (required, normalized, bounded); the guardrail, the compiler, and the scene materializer all call it, and the materializer revalidates so a forged internal requirement cannot bypass it.
- The durable payload stores the normalized card; decoding requires it and rejects any other persona shape with a named error.
- The materializer writes the occupant card through `initialize_npc_persona` with `generated_quest` provenance (quest key, stage index, occupant position) inside the atomic materialization; re-materializing an existing occupant never overwrites its card.
- The `scenario_director.system` prompt asks for a complete card per `npc_req` with the field list, required/optional leaves, and budgets; the `scenario_director` default `max_tokens` rises from the 250-token generic default to 8,192 and a blueprint is capped at three occupants in total, so a blueprint with compact occupant cards fits one response (worked budget in design D6).
- The NPC-bearing offline template (`討伐林間盜匪`, occupant 黑鬍) gets a fully authored card, so offline degradation supplies complete characterization.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scenario-director`: blueprint validation requires and bounds the occupant card (MODIFIED); ADDED requirements for the prompt's card instructions and for complete cards on template occupants.
- `scene-builder`: the optional flavor-persona requirement is replaced by a complete-card requirement covering compile, durable restore, materialization, and revalidation.
- `llm-profiles`: the per-layer defaults name the `scenario_director` output budget.

## Impact

- Code: `world/ai/scenario_director/{blueprints,validators,prompt}.py`, `prompts/scenario_director.yaml`, `world/ai/director_templates.py`, `world/ai/profiles.py`, `world/quests/characterization.py`, `world/quests/compile/{contracts,fields,canonical,payload}.py`, `world/quests/scene_builder.py`.
- Tests: `world/ai/tests/`, `world/quests/tests/` (package-owned shard labels), `world/ai/tests` profile defaults.
- Durable data: a retained developer database whose generated-quest store holds pre-change occupant characterizations fails `sync_quest_runtime` with a named error naming the quest until `npc-persona-roster-cutover` (which rewrites those payloads before restore) lands; tests and CI use fresh databases. No runtime compatibility decoder is added.

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: sole editor in this batch of `world/ai/scenario_director/*`, `world/ai/director_templates.py`, `prompts/scenario_director.yaml`, `world/ai/profiles.py`, `world/quests/characterization.py`, `world/quests/compile/*`, and `world/quests/scene_builder.py`. `npc-persona-roster-cutover` reads this change's payload codec to rewrite durable payloads and must be applied after it; merge the two close together because of the retained-database interim described above. Shared append-only files: `tools/test_data_freeze.json` (template data-contract test), the observability catalog if materialization events gain the profile/provenance context.
