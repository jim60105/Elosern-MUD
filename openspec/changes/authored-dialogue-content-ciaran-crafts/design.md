# Design

## Context

Observed domain file world/lore/dialogue/ciaran.py contains these existing host rows: `ciaran_hailiel_home`, `ciaran_vethiel_home`, `ciaran_gwenaera_home`; four fixed keyword answers each. Existing profiles and place/assortment registries remain canonical. Old prose may all be discarded; service functionality may not.

## Goals / Non-Goals

**Goals:** Complete authored rewrite for ciaran_hailiel_home, ciaran_vethiel_home, ciaran_gwenaera_home. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Use Shared contract v1 in ../authored-dialogue-contracts/design.md, with condition/disclosure/reading/notice behavior supplied by prerequisites. This is an independently runnable content replacement for `ciaran_hailiel_home`, `ciaran_vethiel_home`, `ciaran_gwenaera_home`, exactly the existing registry ownership listed below. No production runtime changes except correcting this slice's explicit declaration metadata.

### Mandatory authoring and review gate

BEFORE composing or reviewing ANY dialogue prose, both writer and reviewer MUST read `tmp/story_settings/world_info.md`, skill://npc-dialogue-content, skill://chinese-content-writing-guideline, skill://writing-style-guideline, world/lore/npc_profiles/ciaran_homes_a.py;world/lore/npc_profiles/ciaran_homes_b.py, `world/lore/settlements/places.py`, relevant settlement domain rows, `docs/lore/settlement-locations.md`, and referenced item/religion/race lore. The proposal author deliberately did not read the reserved file. If it is unavailable at implementation, stop content writing/review and report that real prerequisite; no fabricated substitute lore. Explicitly review elves social standing relative to other races, their rarity, and distinctive religious beliefs. Record file/section source references and editorial decisions in this slice's existing content-review convention or new `ciaran-crafts-dialogue-review.md` under docs/lore; do not quote or commit the private world_info file.

### Complete owned inventory

- `ciaran_hailiel_home.topic_01` through `ciaran_hailiel_home.topic_04`: rewrite all four formal topics, all variants/refusals, and the host opening.
- `ciaran_vethiel_home.topic_01` through `ciaran_vethiel_home.topic_04`: rewrite all four formal topics, all variants/refusals, and the host opening.
- `ciaran_gwenaera_home.topic_01` through `ciaran_gwenaera_home.topic_04`: rewrite all four formal topics, all variants/refusals, and the host opening.

The runtime mechanical conversion assigns these stable topic IDs once in existing order. Retain them even when rewriting labels/questions/composition. No old response sentence, label-derived runtime actor prompt, temporary old-speech wrapper or prior greeting paragraph survives as authored scene prose. Labels/keywords may stay recognizable for text discoverability; all four topic scene bodies per host are newly written natural exchanges. Every topic fallback/variant has 3..8 meaningful authored lines starting with a complete actor utterance, at least one actual host response, and no invented player purchase, allegiance, quest acceptance, identity claim or consent. Opening greeting remains a bounded greeting string through existing precedence; replace it too. Include narration in at least one scene per host and consecutive same-speaker lines in at least one scene in this slice, using explicit line kinds. No LLM rewriting or runtime interpolation from persona.

### Domain-specific acceptance

Twelve topics plus three openings. Village crafts are sharing/personal interests, not inherited trades, schools or shops with hours. Check actual blade/clothing/adornment assortment and buy-back contracts; no prose-delivered repair/crafting effect. Race-specific welcome/curiosity variants must respect elf rarity and social standing from source; never imply elves have human career hierarchy.

Use conditions only with concrete existing canonical keys reviewed at implementation; no synthetic/absent keys in shipped content. Optional literary decisions are source-bound authoring choices, not unresolved engine interfaces. Variants use explicit distinct priority (20 for specific combined context, 10 for a single trait) and unconditional fallback. Public services and original baseline informational topics remain available; qualification added only to genuinely additional optional personal content and never to service access. This slice may add at most one optional additional formal topic per host when the source gives protected personal material, with visible lock/refusal and canonical hint; no invented quest facts. If no source-backed extra exists, do not fabricate one just to demonstrate a gate. Synthetic behavioral tests cover every condition independently of shipped prose.

### Validation ownership

Add tagged `world/lore/tests/test_authored_dialogue_content_ciaran_crafts.py` data-contract tests naming ONLY owned host keys; register in tools/test_data_freeze.json and .github/evennia-shards.json. Keep mechanism tests synthetic. Assertions cover complete topic inventory, stable IDs, actor-first multi-line attribution, all declaration references/bounds/fallbacks, no OOC/backticks/commands/mechanic names, host-specific canonical office/assortment facts and no old speech-only conversion. Do not freeze exact prose in behavior assertions or add a duplicate mutable balance table. Editorial review must check every line and record line-specific findings; green schema tests alone cannot establish in-character quality or mandatory-source fidelity.

Exercise one real constructed owned host through browser manual playback and the identical topic offline via CmdTalk, comparing scene identity/attribution and deterministic effect counts, not exact prose echo. Existing shared synthetic browser mechanics stay in owning engine changes; use a per-slice data-contract smoke/test so simultaneous content workers do not edit the shared browser fixture. Ensure replay gives no second effect and text emission records formal read. Update affected docs/lore review/authoring notes and any command-topic examples changed; preserve command syntax and service settlement. Full batch is complete only after every row in all five domain files has passed its owning rewrite, with no catch-all follow-up left to replace prose.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/lore/dialogue/ciaran.py (only owned ROWS/response constants)`
- `world/lore/npc_profiles/ciaran_homes_a.py`
- `world/lore/npc_profiles/ciaran_homes_b.py`
- `world/lore/tests/test_authored_dialogue_content_ciaran_crafts.py (new)`
- `docs/lore/ciaran-crafts-dialogue-review.md (new)`

## Risks / Trade-offs

Same-domain siblings share world/lore/dialogue/ciaran.py and profile source modules; apply serially or coordinate disjoint host hunks. New content test/review files are exclusive. All content changes share manifest append entries and the authored-dialogue-content main spec at archive; supervisor serializes manifest integration/archive, never edits sibling-owned hosts. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.lore.tests.test_authored_dialogue_content_ciaran_crafts
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
