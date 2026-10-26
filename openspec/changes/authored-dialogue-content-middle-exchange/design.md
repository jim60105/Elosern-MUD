# Design

## Context

Observed domain file world/lore/dialogue/altoria_middle.py contains these existing host rows: `altoria_jeweller`, `altoria_alchemist`, `altoria_merchant_hall`; four fixed keyword answers each. Existing profiles and place/assortment registries remain canonical. Old prose may all be discarded; service functionality may not.

## Goals / Non-Goals

**Goals:** Complete authored rewrite for altoria_jeweller, altoria_alchemist, altoria_merchant_hall. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Use Shared contract v2 in ../authored-dialogue-contracts/design.md, with condition/disclosure/reading/notice behavior supplied by prerequisites. This is an independently runnable content replacement for `altoria_jeweller`, `altoria_alchemist`, `altoria_merchant_hall`, exactly the existing registry ownership listed below. No production runtime or profile-source changes; author declarations only in the exclusively owned YAML files.

### Per-NPC YAML ownership and discovery

The table below resolves existing dialogue rows through canonical place `host_profile_key` bindings to existing `NpcProfile.key` values. The filename derives the owner; neither display names nor database IDs identify files. Existing topic IDs retain their dialogue-key prefix, including `guild_staff`. Each content slice edits only its own YAML plus its unique test/review files. Profiles, place definitions and old region modules are read-only inputs here; the runtime prerequisite owns their format cutover and deletion of obsolete dialogue modules.

| Existing dialogue row / topic prefix | Existing profile key | Exclusive content file |
| --- | --- | --- |
| `altoria_jeweller` | `altoria_jeweller` | `world/lore/dialogue/content/altoria_jeweller.yaml` |
| `altoria_alchemist` | `altoria_alchemist` | `world/lore/dialogue/content/altoria_alchemist.yaml` |
| `altoria_merchant_hall` | `altoria_merchant_master` | `world/lore/dialogue/content/altoria_merchant_master.yaml` |

Use Shared contract v2 without a local schema fork. Each YAML root is exactly `schema_version: 1`, `greeting` (string or null), and `topics` (list). Required topic fields are `topic_id`, `keyword`, `label`, `fallback`; optional fields are `variants`, `requires`, `unavailable`, `refusal`, `predecessors`, and `disclosure`, with shared defaults. A scene has `scene_id`, `revision`, `lines`; a speech line has `kind: speech`, `speaker: actor|host`, `text`, while narration has `kind: narration`, `text`. A variant has `variant_id`, `priority`, `when`, `scene`. Conditions use the shared tagged snake_case union and authorized canonical references. No YAML owner field, effect field or executable instruction is permitted. Put the rewritten opening in `greeting`; runtime precedence consumes it without editing profile voice data.

The `authored-dialogue-yaml-loader` prerequisite discovers all flat-directory YAML files in sorted order with safe parsing, duplicate mapping-key/unsafe-tag rejection, filename-profile binding checks, and common immutable scene/topic validation. It rejects unknown profile IDs and schema/reference errors before publishing the complete immutable snapshot. Adding these files requires no manual registration and creates no hot-reload behavior. Data-contract tests exercise the discovered snapshot, including the exact owner-file binding. Generated/private package content never belongs in these static files or their global registry; its owner publishes validated immutable database packages separately.

### Mandatory authoring and review gate

BEFORE composing or reviewing ANY dialogue prose, both writer and reviewer MUST read `tmp/story_settings/world_info.md`, skill://npc-dialogue-content, skill://chinese-content-writing-guideline, skill://writing-style-guideline, world/lore/npc_profiles/altoria_trade.py, `world/lore/settlements/places.py`, relevant settlement domain rows, `docs/lore/settlement-locations.md`, and referenced item/religion/race lore. The proposal author deliberately did not read the reserved file. If it is unavailable at implementation, stop content writing/review and report that real prerequisite; no fabricated substitute lore. Explicitly review elves social standing relative to other races, their rarity, and distinctive religious beliefs. Record file/section source references and editorial decisions in this slice's existing content-review convention or new `middle-exchange-dialogue-review.md` under docs/lore; do not quote or commit the private world_info file.

### Complete owned inventory

- `altoria_jeweller.topic_01` through `altoria_jeweller.topic_04`: rewrite all four formal topics, all variants/refusals, and the host opening.
- `altoria_alchemist.topic_01` through `altoria_alchemist.topic_04`: rewrite all four formal topics, all variants/refusals, and the host opening.
- `altoria_merchant_hall.topic_01` through `altoria_merchant_hall.topic_04`: rewrite all four formal topics, all variants/refusals, and the host opening.

The runtime mechanical conversion assigns these stable topic IDs once in existing order. Retain them even when rewriting labels/questions/composition. No old response sentence, label-derived runtime actor prompt, temporary old-speech wrapper or prior greeting paragraph survives as authored scene prose. Labels/keywords may stay recognizable for text discoverability; all four topic scene bodies per host are newly written natural exchanges. Every topic fallback/variant has 3..8 meaningful authored lines starting with a complete actor utterance, at least one actual host response, and no invented player purchase, allegiance, quest acceptance, identity claim or consent. Opening greeting remains a bounded string through the shared runtime precedence; replace it in this owner YAML `greeting` field, leaving profile voice definitions unchanged. Include narration in at least one scene per host and consecutive same-speaker lines in at least one scene in this slice, using explicit line kinds. No LLM rewriting or runtime interpolation from persona.

### Domain-specific acceptance

Twelve topics plus three openings. Jeweller and alchemist stay distinct actual assortments, merchant hall grants no caravan escort commission or trade capability. Add one carried-item wording variant at jeweller topic_02 with a reviewed existing item key; inspecting never consumes or sells it. Use an in-world time-period wording variant at hall topic_01 with canonical dayparts, no business-hours restriction invented by dialogue.

Use conditions only with concrete existing canonical keys reviewed at implementation; no synthetic/absent keys in shipped content. Optional literary decisions are source-bound authoring choices, not unresolved engine interfaces. Variants use explicit distinct priority (20 for specific combined context, 10 for a single trait) and unconditional fallback. Public services and original baseline informational topics remain available; qualification added only to genuinely additional optional personal content and never to service access. This slice may add at most one optional additional formal topic per host when the source gives protected personal material, with visible lock/refusal and canonical hint; no invented quest facts. If no source-backed extra exists, do not fabricate one just to demonstrate a gate. Synthetic behavioral tests cover every condition independently of shipped prose.

### Validation ownership

This slice ships authored data only: no test module and no manifest entry. The change's one
requirement (profile-key discovery and atomic rejection) is established by the existing loader and
source-binding logic tests; editorial quality is recorded line by line in the review document.

Exercise one real constructed owned host through browser manual playback and the identical topic offline via CmdTalk, comparing scene identity/attribution and deterministic effect counts, not exact prose echo. Existing shared synthetic browser mechanics stay in owning engine changes; use a per-slice data-contract smoke/test so simultaneous content workers do not edit the shared browser fixture. Ensure replay gives no second effect and text emission records formal read. Update affected docs/lore review/authoring notes and any command-topic examples changed; preserve command syntax and service settlement. This slice completes only after every owned YAML contains all four rewritten baseline topics, all declared variants/refusals and its rewritten opening. Across the ten slices, acceptance covers all 25 hosts, 100 baseline topics and all 25 openings; no catch-all final prose replacement is deferred.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/lore/dialogue/content/altoria_jeweller.yaml` (exclusive content ownership)
- `world/lore/dialogue/content/altoria_alchemist.yaml` (exclusive content ownership)
- `world/lore/dialogue/content/altoria_merchant_master.yaml` (exclusive content ownership)
- `docs/lore/middle-exchange-dialogue-review.md (new)`

Canonical npc_profiles and settlement sources listed above are read-only authoring prerequisites. Shared manifests are integration-owned as described under validation ownership.

This slice registers no shard label and no ledger entry: `.github/evennia-shards.json` shard 4
already owns `world.lore` recursively, and `tools/test_data_freeze.json` needs no row for a module
that does not exist. Add no test module.

## Risks / Trade-offs

Content slices exclusively own their per-NPC YAML files and a unique review document; they do not edit shared region Python modules, profile definitions, loader code or a registration list. Profiles and place bindings are read-only canonical inputs. No test module or manifest entry belongs to a content slice; the integration owner runs the combined gate, and serializes archive into the shared authored-dialogue-content spec. No manual content registration is added. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_dialogue_assembly world.rules.tests.test_dialogue_sources world.rules.tests.test_authored_dialogue_runtime
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
