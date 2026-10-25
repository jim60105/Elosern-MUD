# Design

## Context

Observed owner.guild_rank stores a canonical GUILD_RANK_REGISTRY key whose row.order defines comparison. QuestState values are in_progress/completed/failed/invalidated and unaccepted is absence. parse_reward_claims reads the shared guild_reward_claims exactly-once ledger for both counter and auto claims. RelationHandler.affinity_for/stage_for are pure; get_config owns stage order and boundaries.

## Goals / Non-Goals

**Goals:** Owner guild, quest lifecycle and host relationship qualification. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Shared contract v2 applies the same evaluator/hints to both sources. QuestIs resolves a canonical permitted definition or current package compiled definition from the immutable reference catalog, then uses the SAME owner read_records/claim semantics below. Generated quests need no static registry membership. Foreign-package references reject publication/runtime qualification. LLM conditions never assert completion or reward authority.

Complete the condition union with GuildRankAtLeast, QuestIs and AffinityAtLeast. Resolve all reads from context.owner; the host is context.host. Guild rank requires valid registration and known canonical key; compare GUILD_RANK_REGISTRY[row].order, never alphabetic rank or displayed stats. A missing registration/rank fails, even if the possessed actor owns a rank. AffinityAtLeast takes a canonical affinity stage key; compare the existing stage config boundary to host.relations.affinity_for(owner). Hints show stage display label only, no private value or threshold number. No NPC-to-NPC relationship record and no exposure-driven gain.

QuestIs names canonical definition_key, not user-entered prose. Match records from world.quests.runtime.read_records(owner). States supported by declarations are `not_accepted`, `in_progress`, `completed`, `reward_claimed`, `failed`, `invalidated`. `accepted` is not a second stored lifecycle; documentation calls in_progress accepted/in-progress. not_accepted means zero matching records ever; completed means any matching COMPLETED record regardless of reward claim; reward_claimed means a matching completed record whose quest_id is in parse_reward_claims(owner). in_progress/failed/invalidated match exact stored enum. Multiple repeatable instances use existential matching for positive states. Hints use definition display name and existing lifecycle display vocabulary; corruption raises bounded integrity failure and fails eligibility, never infer completed from prose, reward possession or a memory/thread. Do not change quest state or claim arithmetic.

Retain nonconsuming physical evaluator and combine owner and actor leaves within one bounded All/Any tree. Complete declaration validation for canonical guild/quest/stage keys. Focused synthetic cases include owner qualifies/actor does not and reverse; in-progress versus complete versus claimed; two instances and a stale unrelated claim. With models off, a fixture scene selects the correct complete variant or refusal/hidden response and effects settle only on allowed formal selection.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/rules/dialogue_conditions.py`
- `world/lore/dialogue/conditions.py`
- `world/rules/dialogue.py`
- `world/rules/dialogue_references.py (extend the physical-conditions builder)`

This slice extends, and never re-creates, the static catalog builder from `authored-dialogue-physical-conditions`: it adds the `guild_rank` table from the existing guild rank registry, the `quest` table from existing quest definitions, and the `affinity_stage` table from the existing relation stage configuration, composing them onto the frozen `DialogueReferences` with `child()`. Declared keys in these three families validate against those tables, and a key in a family whose table is absent fails closed.

## Risks / Trade-offs

Sequentially extends physical-condition files and capability. Quest/guild/affinity domain writers stay unchanged; no new lifecycle or rank arithmetic. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_dialogue_progression_conditions world.rules.tests.test_dialogue_physical_conditions
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
