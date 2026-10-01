## Context

See proposal.md for motivation. Current flow: the LLM (or the offline template pool) yields a `QuestBlueprint`; the guardrail runs the output JSON schema (`validators.py`) and semantic validators, including `world/quests/characterization.py::characterize_errors` for each `npc_req`; `compile_quest_blueprint` maps each `npc_req` to a `StageNpcCharacterization` (`background: str | None`, `persona: tuple[tuple[str, str], ...]`); `canonical.py` and `payload.py` encode it into the durable generated-quest store at registration; `restore_generated_quests` decodes every payload at boot (`sync_quest_runtime`, fail-loud); `scene_builder._validate_characterization` re-runs the shared helper at materialization and `_apply_characterization` writes a six-key record with empty containers into `npc.db.persona`. `QUEST_TEMPLATE_POOL` has one NPC-bearing template (黑鬍, tier `bandit`). The `scenario_director` profile uses the 250-token generic default.

## Goals / Non-Goals

**Goals:** one card shape from proposal to spawned NPC; identical validation at guardrail, compile, and materialization; byte-stable survival through compile and restore; versioned metadata on every occupant.

**Non-Goals:** rewriting already-stored payloads or already-spawned occupants (cutover); offline bundle selection inside the proposal (templates are fully authored); any new retry subsystem.

## Decisions

### D1. One frozen card value object end to end

`BlueprintNpcReq.persona: BlueprintPersona | None` where `BlueprintPersona` is a frozen value object mirroring the seven card fields (`identity_public`, `identity_hidden`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`, `social_connection`), keeping the immutability-by-construction guard. `None` is only a structural default so a missing card surfaces as the shared helper's named diagnostic. `StageNpcCharacterization.persona` becomes the contract's `NpcCard` (frozen). `background` is deleted from every layer. Alternative rejected: keeping pairs-of-strings tuples (loses the identity nesting and invites partial cards).

### D2. The shared helper delegates to the card contract

`characterize_errors` requires `persona` and calls `normalize_card(entry["persona"])`, converting `NpcCardError` into a named error string (`persona.<leaf>: <code>`). The helper's purity contract allows this import because the contract lives in `world/lore/`. `MAX_PERSONA_FIELD_LENGTH`/`PERSONA_PROSE_KEYS` and their parity test are removed in favor of the contract's constants.

### D3. Output schema and prompt

The `npc_req` JSON schema's `persona` becomes a required object with `required` = all seven keys, `identity` a required object with `public`/`hidden` strings, every leaf `{"type": "string"}`, `additionalProperties: false` at both levels; `background` is removed. Budget rules are semantic (the helper), not schema, because code-point and rendered-label bounds cannot be expressed in JSON Schema. `prompts/scenario_director.yaml` adds the card instruction: the field list with Traditional Chinese meanings, which leaves may be empty, "speech_style must describe how this person talks", and the per-leaf/total bounds; the existing name-inspiration sentence is unchanged. The prompt does not embed any example card prose from shipped NPCs.

### D4. Durable codec is strict

`canonical.py` writes `card.to_record()`; `payload.py` decodes with `normalize_card` and raises `QuestCompileError` naming the quest, stage, and occupant on any failure, including the pre-change shape. No version sniffing or legacy branch (pre-release; the cutover rewrites stored payloads before restore). A compile→encode→decode→materialize round trip is asserted byte-equal on the card.

### D5. Materialization writes through the initializer

`_validate_characterization` keeps revalidating through the helper. `_apply_characterization` replaces the six-key record write with `initialize_npc_persona(npc, card, {"kind": "generated_quest", "quest": <definition key>, "stage": <index>, "occupant": <position>})` inside the existing atomic materialization (a failure rolls back the whole stage spawn, as today). An existing occupant reused by idempotent materialization is never re-initialized (the initializer no-ops on a marked NPC).

### D6. Template content and token budget

黑鬍 receives a fully authored card consistent with its template (forest-path bandit chief near the capital, age 35, `bandit` tier); the template data-contract test asserts every NPC-bearing template occupant carries a valid card. `world/ai/profiles.py` adds `SCENARIO_DIRECTOR_MAX_TOKENS = 4096` applied to the `scenario_director` default profile like the two existing per-layer exceptions; operators can still override it through settings.

## Risks / Trade-offs

- [LLM proposals now fail more often on budget/shape] → that is the designed behavior: bounded retry, then degradation to the template pool, which carries complete cards. Observed via the existing `llm_call` result/reason events.
- [Retained developer databases fail restore until the cutover lands] → documented interim; merge `npc-persona-roster-cutover` soon after; no decoder shim.
- [Larger durable payloads] → a card is bounded at 2,000 code points; stage occupant counts are already bounded by the blueprint validators.
