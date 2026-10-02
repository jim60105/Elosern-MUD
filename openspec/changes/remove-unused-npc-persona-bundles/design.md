## Context

The authoritative approved decision is Superpowers design §13c, committed by the parent as 030fa18c. §§13a/13b continue to require preserved single-source official companions and development DB reset instead of migration. This change removes dead infrastructure, not NPC functionality.

Static source/caller inventory:

| Area | Current evidence | Retirement/preservation decision |
|---|---|---|
| `world/lore/npc_profiles/bundles.py` | `NpcPersonaBundle`, `NpcBundlePool`, `_validate_bundle_pools`, `offline_pool_for`, `select_offline_bundle`, `_AUTHORED_POOLS`, `NPC_PERSONA_BUNDLE_POOLS`, module `__all__`; 22 cards across 11 pools | Delete the complete subsystem module, cards, exports and coverage validation |
| Production caller search | Selector/resolver references occur only in this module and its owned tests, not any production producer | No caller migration, fallback integration or new producer |
| `world/lore/npc_card.py` | `PROVENANCE_KINDS` includes `offline_bundle`; `validate_provenance:391–395` validates pool/bundle ids | Remove only bundle kind and branch; retain generic card/greeting normalizers and all live provenance |
| `world/lore/tests/test_npc_persona_bundles.py` | Sole selector/pool tests and offline-bundle traceability decorators | Delete whole owned test module; no replacement tests asserting deleted source text |
| `world/lore/tests/test_npc_card.py:178` | `offline_bundle` accepted in valid provenance cases | Remove positive case; add meaningful rejection/no-write behavior for retired provenance through existing lifecycle seam |
| `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json:68` | Exact owned test path and bundle-data-contract reason | Remove both exact entries, preserving every unrelated record |
| `.github/evennia-shards.json:223–231` | `world.lore` package label owns all lore tests; no explicit bundle-test label | Keep broad label and remaining lore coverage unchanged; no invented shard deletion |
| `npc_profiles/__init__.py` | Assembles only six authored host/examiner slices; no bundle export/import | Preserve assembly; remove exports only if actual references emerge before apply |
| `world/rules/npc_roster_validation.py` | Validates place/rank/companion/quest-template/import sources; no bundle gate/import | Preserve entire live roster validation; never confuse QUEST_TEMPLATE_POOL with persona bundle pools |
| Current adding-NPC/roster review docs | No bundle-specific usage contract discovered | No fabricated removals; record KISS retirement in appropriate authoring/changelog notes only |
| Current main specs | Three offline-bundle requirements plus `NPC persona metadata is a separate record` permits `offline_bundle` | Exact REMOVED deltas for all three; narrow MODIFIED metadata delta |
| Historical archived proposals | Record formerly approved/implemented functionality | Preserve historical evidence, not live runtime requirements |

## Goals / Non-Goals

**Goals:** Complete clean deletion of exclusively owned subsystem plus its provenance acceptance and validation/test ownership, retaining actual creation behavior.

**Non-Goals:** No alternative persona generator, placeholder cards, backup code, alias, compatibility decoder, migration or cutover service. Do not touch generic NPC tier/race registries, complete generated cards, quest template occupant cards, official companion presets, host/examiner profiles, imports/editor/greetings except separate approved fixes.

## Decisions

### Delete the owned subsystem rather than integrate it

Delete the whole module and owned tests. The hypothetical caller was the cancelled cutover; retaining pools or selector wrappers would preserve the same maintenance burden. No production consumer currently needs redirection. Git history is the only recovery source; any future use must justify a new design/proposal rather than stubs or dormant runtime contracts.

### Closed provenance rejects the retired kind

The supported set becomes `profile`, `companion`, `import`, `generated_quest` with all existing shape/bounds unchanged. `offline_bundle` becomes an ordinary invalid provenance before writes; metadata carrying it is unavailable under the existing read validator, without repair. Do not translate it to `profile` or generated provenance, accept it in a decoder, or auto-generate a replacement card. Preserve current transaction/version/cache guarantees for live kinds. Shared normalization is owned by the preceding Unicode fix; this change modifies provenance only.

### Retire all current owned requirements and keep live guarantees

The actual `npc-persona-offline-bundles` main spec has three requirements, not five: whole-card pools; tier/race resolution; stable selection/persist-once. Remove all exact headers with reasons and reset/no-replacement migration notes. Amend only the cross-capability provenance requirement. No new capability promises a replacement mechanism. At eventual spec synchronization the retired capability must no longer contain active requirements; do not leave generic pool requirements in another spec or reintroduce speculative producer obligations. Archival mechanics are not performed in this proposal phase.

### Preserve online/offline creation boundaries

Generated quest characters still use the existing online model and validated complete-card pipeline, unchanged prompt inputs/outputs and call count. Never add a candidate-card list, post-generation replacement, extra call, or offline LLM generation. Offline quest templates already carry complete authored cards and remain the supported deterministic source. Host/examiner sources and companion derivation remain independent and unchanged; import/editor paths retain exact raw card behavior. No extra runtime operation replaces the selector because none was consumed.

## Risks / Trade-offs

- [A future caller arrives before apply] → Repeat static caller inventory during apply; remove only subsystem-exclusive code while preserving real consumers. An actual newly introduced required consumer is a scope decision, not permission to invent a fake replacement.
- [Bundle pools mistaken for quest-template pools] → Explicit preservation inventory and fresh-template compile/restore/materialization smoke ensure the live offline path is untouched.
- [Legacy bundle metadata] → Fail closed under existing validator; reset unsupported disposable development DB per §13b, never migrate or decode compatibility.
- [Manifest/shard accidental coverage loss] → Delete exact owned entries from both manifests and retain broad world.lore label; verify remaining test discovery/traceability.
- [Current specs demand deleted work] → Exact three requirement retirements plus live-kind metadata amendment; keep archived history untouched.

## Migration Plan

Clean source/spec cutover only. No DB migration, legacy alias or backup tree. Existing disposable development data uses the approved reset runbook; no supported producer wrote bundle provenance. Restore code via Git history only if separately approved, with its own current design. Parent-owned Superpowers amendment is already committed and is not staged by this proposal.

## Integration ordering

Run this fifth after `npc-authored-canonical-ages` and the visible-target → greeting-output → Unicode chain. Shared files are `npc_card.py`/card tests/spec (normalization versus provenance hunks), exact data manifests, and potentially roster-related synthetic fixtures; no roster-validator edit is required by retirement itself. Preserve the four fixes' new tests/docs and age profile fields rather than deleting surrounding shared content.
