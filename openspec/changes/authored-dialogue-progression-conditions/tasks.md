# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Guild and affinity leaves

Shared contract v2 covers authorized package quest definitions through the same owner record/claim readers. Test foreign reference rejection without requiring static quest registry membership.

- [x] 1.1 Implement canonical registration/rank and host-to-owner stage readers/hints; add world/rules/tests/test_dialogue_progression_conditions.py with owner/actor inverse controls and private-number omission. Document existing registry ownership and no independent ordering.
  - `GuildRankAtLeast` requires a strict registration and a canonical
    `GUILD_RANK_REGISTRY` key, compares `row.order` (never alphabetic order or
    display stats), and reads `guild_rank` through the non-materializing
    attribute handler. `AffinityAtLeast` compares
    `host.relations.affinity_for(owner)` against
    `get_config().stage_by_id(key).floor`. Both read only `context.owner`, so a
    possessed actor's own rank or relation grants nothing; hints render the
    canonical rank/stage label and never a private value or threshold.
    `docs/development/adding-npcs.md` documents the families and ownership.

## 2. Quest lifecycle predicates

- [x] 2.1 Implement definition-key matching over read_records and parse_reward_claims with explicit six-state semantics; add deterministic absence/in-progress/completed/claim/failed/invalidated/repeatable/corruption cases and no-write assertions.
  - `QuestIs` resolves the key against the permitted catalog (canonical
    declarations plus registered definitions), matches
    `read_records(owner)` existentially, and reads
    `parse_reward_claims(owner)` only for `reward_claimed` (a completed record
    whose own quest_id is in the ledger). Fully malformed stored quest logs and
    claim ledgers (scalar, mapping, string) fail closed with one bounded
    `dialogue_condition_integrity` event instead of satisfying `not_accepted`;
    evaluation and hints leave every owner/host surface byte-identical.

## 3. Complete condition selection acceptance

- [x] 3.1 Test mixed physical/progression All/Any scenes through real selection offline, with a stale state change refusing without effects. Update condition author documentation, manifests and traceability; run focused condition tests and contract_gate.
  - The behavior suite drives `select_authored_topic` through rank-, quest-,
    affinity-, mixed `All` and mixed `Any` synthetic topics, proves a lawful
    possession's own rank cannot qualify the owner, and shows a locked quest
    refusal grants no affinity or quest effect while a stale changed state
    refuses a fresh selection and the committed replay keeps its scene. The
    module is registered in the rules shard; `test_dialogue_references` covers
    the new families and cold-process quest/stage references;
    `openspec validate --strict`, the focused suites and `contract_gate` pass.

