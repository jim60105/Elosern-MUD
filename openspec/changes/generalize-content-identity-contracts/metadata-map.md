# WP1 same-change retarget rules and freeze/seed metadata map

Baseline `master` = the worktree tip at WP1 start: `fbfd20ab8755a44cf4fc3d12362a70d345d912f0`.
Metadata read points: `tools/test_data_freeze.json` (ledger: `contract` reasons, `debt`),
`tools/test_data_lint_seed.json` (seed classification carrying `contract` reasons and `seedDebtPaths`),
`tools/test_data_lint_deny.json` (rule-bound tokens), and each file's first docstring line
`Data-contract test: <reason>` (JS/TS: `// Data-contract test: <reason>`).

## The same-change retarget rules

1. **Retire and re-attach in the same implementation (D3).** A requirement heading this change
   REMOVES retires its canonical id; every annotation carrying it is retargeted in the same commit
   to the specific general requirement the assertion actually establishes (`cutover-matrix.md`,
   Matrix B). A MODIFIED heading keeps its id and gets its assertions reviewed.
2. **Ids come from the tool only.** `uv run --locked python -m tools.spec_traceability list` for
   current ids, and the same tool against the effective tree for post-cutover ids. Never hand-slug,
   never keep a stale id to make a test pass, never add an allowlist or waiver.
3. **The annotation is a claim, not a substitute.** Retarget a test only when its inputs, action and
   assertions actually establish the new requirement; split a test when one site carries claims for
   requirements with different roles. Never attach an unrelated, skipped or assertion-free test
   (`docs/development/spec-test-traceability.md`).
4. **Role decides what may be rewritten.** `registry-contract` sites may drop roster/prose pins and
   keep validating live registry relationships; `synthetic-mechanism` sites keep independent expected
   outcomes and may not read shipped content; `representative-smoke` sites keep a real consumer
   boundary and may not be mocked. The role is recorded per site in `cutover-matrix.md`.
5. **A `Data-contract test:` line and its ledger reason are one string in three places.** Changing
   the reason means editing the file's first docstring line AND `tools/test_data_lint_seed.json`, then
   regenerating `tools/test_data_freeze.json`; editing one file alone fails `seed-mismatch` /
   `untagged-contract`.
6. **Shrink-only ledgers.** `debt` and `seedDebtPaths` entries are removed in the commit that makes
   the file clean; this change must not add a `debt`, `deny` or new-allowlist entry. A file may
   legitimately move from `debt` to `contract` (as `world/rules/tests/test_buffs.py` already did),
   never the reverse by reason of this cutover.
7. **No new expected-content fixture.** Metadata carries ids, paths, roles and reasons only -- never
   expected prose, item key lists or counts.

## Table A. The 45 annotated files and their ledger metadata

| File | Ledger `contract` reason | In seed `contract` | Ledger kind | Action after the cutover |
| --- | --- | --- | --- | --- |
| `commands/tests/test_talk_turnin_commands.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `web/tests/browser/test_browser_exploration_dialogue.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `web/webclient/actions/tests/test_service_actions.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `web/webclient/presentation/tests/test_exploration_panel/test_wilderness_and_npc_titles.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `web/webclient/tests/test_node_suite_evidence.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/imports/tests/test_batch_all_or_nothing.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/lore/tests/test_assortments.py` | `assortment registry content contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/lore/tests/test_monster_species_content.py` | `shipped bestiary identity, narrative, profile integrity and construction wiring` | yes | — | **align** the first docstring line and both ledgers to: `registry-derived monster identity, profile/kit coverage and bestiary relationship contract` |
| `world/lore/tests/test_monster_species_registry.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/lore/tests/test_npc_profile_slice_content.py` | `per-slice authored NPC profiles and rewritten dialogue content contract` | yes | — | **align** the first docstring line and both ledgers to: `registry-derived NPC host characterization and authored dialogue coverage contract` |
| `world/lore/tests/test_starting_kits.py` | `starting-kit data contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/lore/tests/test_sync.py` | `lore cross-registry sync contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/lore/tests/test_titles_registry.py` | `fixed-title registry content contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/maps/tests/test_service_interiors.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/quests/tests/test_scene_builder/test_characterization.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_crocodile_resource_skill.py` | `crocodile resource skill production combat smoke contract` | yes | — | **align** the first docstring line and both ledgers to: `crocodile representative-composition production smoke over the generic transfer/policy contracts` |
| `world/rules/tests/test_effect_audiences/test_effect_routing_pipeline_rollback_and_composite_effects.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_equipment_effect_rulebook.py` | `equipment effect rulebook contract` | yes | — | **align** the first docstring line and both ledgers to: `equipment effect rulebook and item-lore liturgical-role contract` |
| `world/rules/tests/test_guild_config/test_assortment_shop_rules.py` | `guild/shop config validation contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/rules/tests/test_guild_config/test_commerce_rulebook_slices.py` | `commerce rulebook slice loading contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/rules/tests/test_guild_config/test_item_offer_definitions.py` | `guild/shop config validation contract` | yes | — | unchanged (reason still describes the post-cutover claim) |
| `world/rules/tests/test_guild_config/test_service_host_roster.py` | `guild/shop config validation contract` | yes | — | **align** the first docstring line and both ledgers to: `place-derived service host roster and current place-declaration contract` |
| `world/rules/tests/test_guild_economy_sync/test_altoria_adornments_remedies.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_altoria_crown_watch.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_altoria_hospitality.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_altoria_learning_exchange.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_altoria_sanctum.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_service_content_sync.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_service_host_identity.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_economy_sync/test_service_host_roster_authority.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_guild_rewards.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_human_guild_hosts.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_monster_flee_decision.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_monster_individual.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_npc_identity.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_npc_roster_validation.py` | `shipped NPC persona roster validation contract` | yes | — | **align** the first docstring line and both ledgers to: `registry-derived NPC roster completeness and fault-diagnostic contract` |
| `world/rules/tests/test_shop_economy.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_skill_hit_dependencies.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` | `sparrow resource skill production combat smoke contract` | yes | — | **align** the first docstring line and both ledgers to: `sparrow representative-composition production smoke over the generic rider/lifetime contracts` |
| `world/rules/tests/test_tide_lamp_crab_resource_skill.py` | `crab resource skill production combat smoke contract` | yes | — | **align** the first docstring line and both ledgers to: `crab representative-composition production smoke over the generic self-guard/lifetime contracts` |
| `world/rules/tests/test_titles/test_title_guild_pairing.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/rules/tests/test_titles/test_title_state_collection.py` | — | n/a | — | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/skills/tests/test_equipment.py` | — | n/a | seedDebtPaths | no ledger entry: assertion/role change only; do not register a new `contract` entry |
| `world/skills/tests/test_skill_registry/test_registry_contract.py` | `skill registry content contract` | yes | — | **align** the first docstring line and both ledgers to: `skill registry typed kit/reference contract` |

## Table B. Ledger-registered consumers outside the annotation map

| Path | Current metadata | Disposition |
| --- | --- | --- |
| `world/lore/tests/test_items.py` | item registry content contract | WP6 removes the 123-item expected-key roster: align to `item registry registration/metadata/reference contract` in the commit that removes it. |
| `world/lore/tests/test_npc_profile_inventory.py` | shipped NPC source inventory data contract | WP4 replaces fixed owner labels and 25/3/28 counts with two-way live-source equality: align to `shipped NPC source inventory equality contract`. |
| `world/lore/tests/test_settlements.py` | settlement and place registry content contract | WP4 removes only host-identity and offered-item snapshots; the reason stays, but the file's first docstring line must remain `Data-contract test: settlement and place registry content contract`. |
| `world/lore/tests/test_dialogue_assembly.py` | Altoria dialogue terrace split preserves tables and terrace alignment | WP4's dialogue rewrite may change what the file guards: re-read its first docstring line and realign the ledger reason in that commit if the claim moves. |
| `world/lore/tests/test_registry_index_contract.py` | authored registry index coverage and shipped reference integrity contract | Re-derive after WP2 changes the monster registries' obligation fields; comment count pins (`quantity-pin`) must not be added. |
| `world/ai/tests/test_npc_dialogue_prompts.py` | debt (no contract reason) | Affected starter-epithet consumer. WP5 must replace the starter-looking sample display with an explicit synthetic epithet; the file stays in `debt`/`seedDebtPaths` and must not be promoted to `contract` to hide it. |
| `world/rules/tests/test_item_effects_rulebook.py` | debt (no contract reason) | Listed in `debt`: not an affected-identity consumer of this cutover; leave classification and reason unchanged. |
| `web/tests/browser/seed/titles_fixture.py` | not in the ledger | WP5 makes the seeded starter sample explicitly synthetic and rewrites the fixture docstring accordingly; it must stay unregistered (it is a seed helper, not a data-contract test). |
| `web/browser_support/browser_fixtures_data/titles_fixtures.py` | not in the ledger | Synthetic browser title fixture data (`SYNTH_TITLE_BANKED_KEYS`): the synthetic kit stays the authority; no ledger registration. |
| `tools/test_data_freeze.json` | ledger (not a test path) | Never hand-edit a reason in the ledger alone: edit `tools/test_data_lint_seed.json` and regenerate the ledger, or the `seed-mismatch` rule fails. |
| `tools/test_data_lint_seed.json` | seed classification | Same rule in the other direction: `seed-mismatch` compares `seedDebtPaths` and every seeded contract reason verbatim. |

## Table C. The ledger/seed asymmetry

| Path | Ledger | Seed | Disposition |
| --- | --- | --- | --- |
| `world/rules/tests/test_buffs.py` | `contract: buff rulebook content contract` (94th entry) | absent from `contract`, present in `seedDebtPaths` | Pre-existing, legal: `check_ledger` reports `new-debt` only when a contract path is outside the seeded classification *and* outside `seedDebtPaths`. This change touches neither file; the entry is recorded so no package mistakes the 94-vs-93 difference for drift and regenerates the ledger wholesale. |
| `world/ai/tests/test_npc_dialogue_prompts.py` | `debt` | `seedDebtPaths` | Affected consumer; stays debt (WP5) -- see Table B. |
| `world/imports/tests/test_skill_registry_self_arming.py`, `world/rules/tests/test_item_effects_rulebook.py`, `world/rules/tests/test_traits.py` | `debt` | `seedDebtPaths` | Unaffected by this cutover; leave untouched. |

Counts observed at WP1: ledger `contract` 94, `debt` 14, `seedDebtPaths` 336; seed `contract` 93,
`seedDebtPaths` 336. Reasons must be edited in `tools/test_data_lint_seed.json` and the ledger
regenerated with `uv run --locked python -m tools.test_data_lint check` as the gate.
