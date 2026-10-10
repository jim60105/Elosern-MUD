# Approval decisions and pending-change conflict matrix

All pending changes remain untouched. Approval must acknowledge the following consequences, not silently authorize their repair.

## D1: Twelve MODIFIED targets become nonexistent

Each row below occurs in **each** of `ridge-burrow-hare-resource-skill`, `rock-echo-goat-resource-skill` and `fog-mane-lynx-resource-skill`. Thus four broken blocks per proposal, twelve total. REMOVED plus ADDED is deliberate; no compatibility heading is retained.

| Pending delta file (relative to each change) | Exact old MODIFIED requirement | Replacement owner/requirement after cutover | Later owner action |
|---|---|---|---|
| `specs/monster-species-registry/spec.md` | Numeric combat profiles and danger grades are balance-gated slots, never invented values | Authored profile requirements are declared per variant | Rebase onto the generic obligation/complete-record contract; remove old twelve-row and numerical-table restatements |
| `specs/monster-species-registry/spec.md` | Special abilities are narrative boundaries with a named mechanics prerequisite, never fake skills | Narrative and executable monster configurations remain separate | Express new kit delivery in registry data; modify a generic contract only for genuinely new behavior, copying its then-current full block |
| `specs/monster-species-registry/spec.md` | The approved first-batch profiles and grades are user-approved literals | Shipped profile completeness follows authored declarations | Replace literal approval tables with authored rows and independent integrity/band checks; do not resurrect the old name |
| `specs/monster-resource-abilities/spec.md` | Crocodile ecology documents implemented limits | Bestiary documentation covers keyed public content relationships | Update keyed documentation links/status and editorial evidence, not a fixed still-deferred species list or verbatim sentence requirement |

All four target names are removed by this proposal. If these old deltas are applied after the generalization, target lookup is structurally invalid. Independently, their numeric approval tables and named completed/deferred lists are semantically incompatible with the new contract. The current strict failures are deferred and must not be repaired by this proposal.

## Eighteen old-shaped ADDED blocks need later redesign

For each of the three proposals, the species prefix is respectively **築埂兔**, **岩響山羊** and **霧鬃山貓**. Preserve these actual authored spellings; English slugs are not Chinese display-name authorities.

| Pending file | Exact ADDED requirement pattern (substitute each prefix above) | Later owner action |
|---|---|---|
| `specs/monster-action-policy/spec.md` | `<prefix> contact kit uses existing first-owned policy and fallback` | Author behavior binding/owned order as data; exercise generic policy/fallback contract |
| `specs/monster-individual-construction/spec.md` | `<prefix> construction persists both approved contact kits` | Author variant kits; add generic all-variant construction evidence without a per-species requirement |
| `specs/monster-resource-abilities/spec.md` | `<prefix> owns its approved contact resource ability` | Add authored skill/effect/eligibility data and structural checks, not identity/cost pins in spec |
| same | `<prefix> timed modifier follows its authored recipient and lifetime` | Reuse generic audience/lifetime mechanism tests and appropriate representative smoke |
| same | `<prefix> payment and atomicity retain the shared transaction` | Reuse independent shared transaction/rollback tests; add only truly distinct composition evidence |
| same | `<prefix> public ecology reflects the completed contact kit` | Update keyed public sections and kit-backed status; record editorial review without approved sentence comparison |

These eighteen ADDED blocks might parse as new requirements, unlike the twelve broken MODIFIED blocks, but would restore the identity-specific shape and violate this cutover. Owners must remove/recast them when their deferred changes resume. This is an analysis and approval consequence, not edits or implementation tasks assigned to this proposal.

## D2: Completeness survives consolidation

The six exact current slice headings and their current annotations are listed in `scope-inventory.md`. Their replacements must derive actual hosts/tables from live sources independently of the inventory, establish bidirectional source equality, then validate every individual profile/card/age/voice and declared service dialogue. Include persistent qualified people and all existing non-place source kinds. Editorial rewrite completeness is reviewed by current source identity; no missing host is excused by not belonging to the old six slices. Approving removal without these replacements is not this design.

## D3: Traceability retirement is atomic with the contract cutover

All retired IDs must disappear from executable Python/JS annotation sources and metadata at apply completion. Generate new canonical IDs through the project tool against effective specs. Each replacement ID earns direct assertions for the specific general invariant, rather than a mechanical global decorator substitution. MODIFIED IDs remain but their changed assertions must be reviewed. A no-stale-ID scan and no-allowlist traceability validation are acceptance criteria of this change.

## Dependency/conflict matrix

This is one change, so it has no `## Batch:` dependency metadata and no artificially split queue entries. The matrix records external interactions without changing another proposal.

| Other change/state | Dependency/order decision | Shared code/spec surfaces | Disposition |
|---|---|---|---|
| `flexible-game-data-test-design`, archived/merged `afa974d4` | Completed prerequisite and test-role precedent | monster/content tests, traceability and test-data metadata | Build on it; do not reopen it |
| `ridge-burrow-hare-resource-skill`, deferred | Recommend generalization first, then owner refresh; no current hard queue dependency | four old MODIFIED targets; six old-shaped ADDED blocks; species/kit/profile/rulebook/bestiary consumers | User approval D1 required; no edits here |
| `rock-echo-goat-resource-skill`, deferred | Same as above | same contract targets and authored monster consumers | User approval D1 required; no edits here |
| `fog-mane-lynx-resource-skill`, deferred | Same as above | same contract targets and authored monster consumers | User approval D1 required; no edits here |
| `exploration-*`, unrelated separate session | No planned dependency; owner must compare actual apply-time diff | possible service/HUD integration overlap, not an assumed conflict | No edits or speculative resolution; shared HUD change here is only a synthetic-name example |
| Military examiner content | Retained dependency explains named exception | `military-equipment`, `guild-exam-restrictions`, `guild-rank-exams`, authored qualified-person military gear | Keep named pairs and examiner-facing statements unchanged |
| NPC inventory/profile tests | Internal WP4 depends on source equality | actual-source derivation, six slices, roster fixtures | D2 replacement cannot be omitted |
| Traceability consumers | Internal all packages, final WP7 | removed IDs/decorators, Python/JS evidence, freeze metadata and seed reasons | D3 same-change retarget and acceptance |

If a deferred change lands before this one, the applying owner must inspect the new current blocks and request the corresponding proposal update before cutover. Do not infer approval, rewrite their drafts, choose new balance values or add compatibility aliases.
