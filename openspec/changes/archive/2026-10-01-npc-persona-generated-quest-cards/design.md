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

`_validate_characterization` keeps revalidating through the helper. `_apply_characterization` replaces the six-key record write with `initialize_npc_persona(npc, card, {"kind": "generated_quest", "quest": <definition key>, "stage": <index>, "occupant": <position>})` inside the existing atomic materialization (a failure rolls back the whole stage spawn, as today). An existing occupant reused by idempotent materialization is never re-initialized (the initializer no-ops on a marked NPC). The initializer opens a savepoint inside the outer materialization transaction, so its commit-bound `npc_persona_initialized` event fires only when the whole stage commits; `NpcCardError` and `NpcPersonaStorageError` are raised as `SceneBuilderSpawnError` so callers see one named failure family. When a later step of the outer transaction fails, the discarded spawned NPC may keep stale in-process attribute cache entries; nothing reuses that object, so no extra cache restoration is added.

### D6. Template content and token budget

黑鬍 receives a fully authored card consistent with its template (forest-path bandit chief near the capital, age 35, `bandit` tier); the template data-contract test asserts every NPC-bearing template occupant carries a valid card. `world/ai/profiles.py` adds `SCENARIO_DIRECTOR_MAX_TOKENS = 8192` applied to the `scenario_director` default profile like the two existing per-layer exceptions; operators can still override it through settings.

Worked budget: a compact card requested at about 800 rendered code points costs at most about 1,600 output tokens at a conservative 2 tokens per Traditional Chinese code point (JSON escaping included in the estimate); three occupants cost about 4,800 tokens and the rest of the blueprint under about 1,000 — about 5,800 in total, inside 8,192 with headroom. A new guardrail-only semantic rule (a model-response budget rule; the compiler does not mirror it, and the template data-contract test keeps the offline pool inside it) caps a blueprint at three `npc_req` occupants in total across stages (the output schema previously placed no bound on the `npc_req` array, so a blueprint could declare any number of occupants). Cards near the 2,000-code-point maximum on all three occupants may still exceed the budget; such a response is cut off by `max_tokens`, fails to parse as JSON, and the guardrail treats the malformed body as a transport failure that degrades immediately (without spending the retry budget) to the template pool, whose cards are complete — the designed behavior, not a silent loss. The 800-code-point target is a prompt instruction, not an enforced bound; the enforced bound stays the card contract. A unit test serializes a three-occupant blueprint with 800-code-point cards and asserts `2 × card code points + JSON bytes of the non-card remainder` stays under `SCENARIO_DIRECTOR_MAX_TOKENS`.

Splitting this change (schema/codec versus prompt/template/budget) was considered and rejected: a required card in the schema without the prompt asking for it, or without the template carrying it, would leave the LLM path or the offline path failing between the two merges.

## Risks / Trade-offs

- [LLM proposals now fail more often on budget/shape] → that is the designed behavior: bounded retry, then degradation to the template pool, which carries complete cards. Observed via the existing `llm_call` result/reason events.
- [Retained developer databases fail restore until the cutover lands] → documented interim; merge `npc-persona-roster-cutover` soon after; no decoder shim.
- [Larger durable payloads] → a card is bounded at 2,000 code points; stage occupant counts are already bounded by the blueprint validators.
