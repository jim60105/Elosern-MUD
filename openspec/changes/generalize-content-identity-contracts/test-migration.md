# Test migration

## Roles and evidence

Apply the repository's archived test-role disposition. A data-contract test may use current shipped identities only to validate keyed metadata, reference closure, coverage and relationships; it must not duplicate a closed content approval table. Mechanism tests use scoped synthetic immutable registries and independently known outcomes. Production smoke tests use real construction/policy/resolution/persistence for representative composition shapes, never a substituted test-only writer or a mocked successful resolver. Do not add balance snapshots, live LLM calls, allowlists or self-fulfilling assertions.

`scope-inventory.md` inventories every changed current heading/ID and 164 discovered Python annotation sites with exact file, line and test name. That is the per-requirement migration map, not an optional sampling. For every site: classify its assertion role; retain the existing independent assertions where valid; remove obsolete roster/prose expectations; retarget REMOVED IDs to the relevant general ADDED requirement; retain MODIFIED IDs with revised assertions. Discover JS annotations and seed/freeze declarations during WP1 with the existing traceability tooling and expand the same map if needed. No old-ID annotation is allowed to remain merely because its file was not in a hand-written shortlist.

## 1. Monster registry and bestiary

| Actual source inspected | Current pin / behavior | Concrete replacement |
|---|---|---|
| `world/lore/tests/test_monster_species_content.py` | `APPROVED_SPECIES`, `APPROVED_VARIANTS`, six/twelve closed sets, exactly two variants per species, literal ability-limit/contact sentences and normalized bestiary sentence comparison | Derive keys from live registries; validate each typed row, key identity, parent/default membership and required-profile declaration. Remove species/variant maps and `_normalised`/`_sentences` expected-prose helpers after replacing their use. Preserve nonempty Traditional Chinese fields and public projection boundaries |
| same, shipped profile/construction and `AbilitySeamNegativeTests` | Every variant's actual construction and reload; fixed delivered six-row kit map; AST guard against species names in policy | Keep all-variant real construction/reload and independent tier checks; derive executable references/kit presence from registry. Retain generic no-species-branch enforcement. Synthetic missing-kit/invalid-ref/profile-required faults must fail for arbitrary keys |
| `world/lore/tests/test_monster_species_band_invariant.py` | Independent axis bounds/grade checks, including asymmetric values | Retain unchanged numerical contracts and independent oracles; no content-name or approval-value table replaces them |
| `world/skills/tests/test_skill_registry/test_registry_contract.py` | Crocodile/sparrow/crab named skill composition tests | Consolidate structural checks over every authored monster-kit skill, validating typed effects, dependency references, costs and eligibility. Current data may be read but not copied into an approved composition table. Mutation tests use synthetic malformed references |
| `docs/lore/bestiary.md` and content test parser | Chinese display headings and historical prose used as implicit identity | Add bounded stable species/variant/parent/public-field links and structured kit-backed status for current sections; historical appendices are excluded. Test a pure relationship checker with synthetic missing/duplicate/orphan/wrong-owner/missing-field/private-reference/status faults. Rewording valid prose must pass |

The checker must identify the specific broken relationship, not merely fail a total count. Explicitly verify the current ordinary default variant is documented under its actual owning species. Public/private separation tests check projection fields and section boundaries; they do not falsely claim to recognize arbitrary secret prose. Ecology consistency and historic/current narrative distinction receive indexed editorial review, not substring assertions.

## 2. Monster mechanisms and consumers

| Actual source | Migration / independent evidence |
|---|---|
| `world/rules/tests/test_skill_hit_dependencies.py` | Keep synthetic actual-removal arithmetic, partial/zero/cap cases, critical/defeat-crossing and two-species real execution with isolated invocation-local hit evidence. Retarget bite IDs to generic transfer/atomic-action contracts; never replace expected numbers with a call to production resolution |
| `world/rules/tests/test_effect_audiences/test_effect_routing_pipeline_rollback_and_composite_effects.py` | Keep actual post-write composite rollback and audience controls. Replace species payment decorators with generic atomic-action coverage only where the test actually establishes it |
| `world/rules/tests/test_crocodile_resource_skill.py` | Keep proportional production transfer smoke with real session/payment/control/reload. Retarget removed delivery/policy IDs to generic consumer/policy/transfer contracts |
| `world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` | Keep representative real enemy-hit-rider consumer, refresh/control/payment/reload assertions. Use kit-composition discovery or a small explicitly tagged current representative selector; no closed species roster and no duplicate mechanism battery |
| `world/rules/tests/test_tide_lamp_crab_resource_skill.py` | Keep real self-guard miss/ally/refresh/payment/reload evidence, independently distinguishing hit-independent caster effect from enemy hit rider. Retarget generic lifetime/policy/consumer IDs |
| `world/rules/tests/test_monster_flee_decision.py` | Retarget removed crocodile policy ID; retain shared declared-threshold validation, inclusive flee priority and tier defaults without species-specific expectation tables |

Preserve cost-tier escalation/modifiers/reactions, no-practice-on-rejection, optional fallback logging and owner load-before-write boundaries. Synthetic unaffordable MP and SP requests, missing/invalid target, miss, fully absorbed hit, expiry and post-write failure are explicit direct coverage, not all inferred from a successful smoke. Current composition representatives need a direct control oracle; selecting a live item by key is not itself integration evidence.

## 3. NPC/merchant inventory and personnel

| Actual source inspected | Concrete migration |
|---|---|
| `world/lore/tests/test_npc_profile_slice_content.py` | Remove six hard-coded owner wrappers and 25-host count. Derive every actual hosted place and dialogue table independently, compare inventory both ways, then validate each individual card, service/profile binding, sole table greeting, misunderstanding reply and local keyword uniqueness. Include qualification-bound people/offline voice. Remove the false globally distinct keyword-tuple assertion; shared service vocabulary is legitimate |
| `world/lore/tests/test_npc_profile_inventory.py` | Replace nine fixed owner labels and 25/3/28 counts with assembled-owner resolution and actual-source equality. Retain the closed source-kind vocabulary and all existing companion/template/import/persistent-person coverage |
| `world/rules/tests/test_npc_roster_validation.py` | Retarget guild-slice IDs to generic characterization coverage. Preserve missing qualified-person profile and valid no-scripted-home-table cases; add a new-owner host/table positive case and missing profile/card/age/voice/table/owner plus stale-row negatives, with specific diagnostics and no DB writes |
| `world/rules/tests/test_guild_config/test_service_host_roster.py` | Remove `FORMER_YAML_ROWS`, historical two-host equivalence, `ASSEMBLED_ROSTER_ORDER` personnel count/name pins and personal portions of `PRE_CHANGE_BASELINE`. Replace fixed per-place capital/village personnel tables with generic current-place-to-derived-roster identity/anchor/component assertions. Keep named place/exterior/doorway assertions and all-or-none hostless structure tests using synthetic hostless records, not a frozen palace/stalls/shelter staffing choice |
| `world/lore/tests/test_settlements.py` | Split `PRE_SPLIT_CONTENT_CAPTURE` and neutrality snapshots: retain excluded place keys/order/topology/description assertions; remove only host identity and offered-item snapshots. Keep invalid race/subrace/sex, host all-or-none, assortment references and no-shop/no-goods validation |
| `world/rules/tests/test_human_guild_hosts.py` | Existing synthetic co-located qualification, normal lineage, age/gear rejection, locked-route, collision, reuse and rollback tests already match generic behavior; retain independent assertions and IDs. Add current-person data closure checks without copying Hok/Cassandra/Augustine names/visit cadence |
| NPC identity/import/SceneBuilder and stage actor tests associated in `scope-inventory.md` | Use synthetic authored names/titles for formatting, collision and missing-portrait initial; retain actual consumer expectations and whole-batch/materialization rollback |

D2 acceptance: add a valid host/table/profile/inventory owner outside the six old slices and prove it is checked automatically; remove each required relationship in isolation and prove a named failure. No complete inventory-only loop can satisfy this test. Editorial ledger entries cover every affected actual host's greeting/responses/card/voice, including rewrite completeness; no expected dialogue corpus is stored in tests.

## 4. Starter epithet and claim surfaces

| Actual source | Concrete migration |
|---|---|
| `world/lore/tests/test_titles_registry.py` | Retain frozen starter-data and fixed registry validation. Replace any shipped starter literal assertion with nonempty/bounded display and origin integrity. Keep clergy and fixed guild title literal contracts unchanged |
| `world/rules/tests/test_guild_rewards.py` | Replace assertions for 「南門新客」 with a scoped synthetic `STARTER_EPITHET` display/origin. Keep first arbitrary-definition claim, later claim, dedupe, occupied-slot behavior, title snapshot and failure-after-affinity-write rollback. Independently assert banked/equipped synthetic values and notification text |
| `commands/tests/test_guild_economy_commands.py`, `commands/tests/test_talk_turnin_commands.py` | Patch the same synthetic declaration at the actual import seam; verify committed first-claim result and exact prefix plus synthetic display on both CLI paths |
| `web/webclient/actions/tests/test_service_actions.py` | Existing synthetic starter fixture is the correct pattern; preserve its web claim assertions and ensure it matches shared first-claim semantics without a live shipped-string oracle |
| `world/rules/tests/test_titles/_support.py`, `world/rules/tests/test_title_view.py` | Existing `T_STARTER` scoped synthetic values remain; do not replace them with live data |
| `world/ai/tests/test_npc_dialogue_prompts.py`, `world/ai/tests/test_title_nomination.py` | Replace starter-looking sample display with an explicit synthetic epithet where it claims starter provenance; retain rendering/nomination behavior and no live LLM calls |
| `web/static/webclient/js/tests/protocol_title_codex.test.js` and related protocol character/core fixtures | Use a synthetic display/basis with the existing schema shape, keeping independent composition/validation/protocol expectations; fixed category-tab and guild-title expectations remain untouched |
| `web/tests/browser/test_browser_title_codex.py`, `web/tests/browser/seed/titles_fixture.py` | Make matching browser/seed starter sample explicitly synthetic, not a shipped starter contract. Preserve successful title/codex behavior and align seed freeze reasons |

Inspect remaining starter references across code/tests/docs at apply to distinguish user-facing authored data from behavior assertions; do not indiscriminately rename existing stored lore or clergy/guild strings. Data ownership is the change, not a new epithet.

## 5. Equipment, kits and shop memberships

| Actual source inspected | Concrete migration |
|---|---|
| `world/lore/tests/test_items.py` | Remove the 123-item expected-key roster; validate complete typed metadata for every registered item and all references. Retain small independent schema/slot/immutability negatives |
| `world/rules/tests/test_guild_config/test_item_offer_definitions.py` | Remove fixed item/shop counts and starter-item/shop-key snapshots. Preserve keyed numeric coverage, complete immutable metadata, valid current offers and independent synthetic presentation/mechanics separation |
| `world/lore/tests/test_assortments.py` | Remove `PRE_SPLIT_OFFERED_KEYS`, twelve sanctum additions, fixed assortment roster, fixed village shared-item tuple and fixed two accessory bundle tables. Compare each resolved shop to its current authored union/additions/removals; validate explicit slot/kind eligibility; permit cross-shop duplicate item membership while rejecting ambiguous within-shop duplication. Retain numerical/price-band checks |
| same, `MILITARY_ADDED_KEYS` | Keep only the explicit E-S pair membership contract as a separate tagged military test, with examiner dependency in its rationale. Do not retain the historical whole-capital union merely because it contains military items |
| `world/rules/tests/test_equipment_effect_rulebook.py` | Replace ten-key `NEW_ITEM_KEYS` stocking assertions with every-item registration/bijection/reference checks and synthetic offered/unoffered behavior. Replace `CHURCH_VESTMENTS_AND_EMBLEMS`/`CHURCH_SANCTUARY_DEVICES` approval tuples with frozen item-lore role discovery; retain independent negative exposure/pleasure/healing and vestment-cannot-borrow-exemption tests |
| same, generic effect presentation/slot cases | Replace accidentally live named utilities with synthetic fixtures when touched; keep independent adjustment/prose order, immunity, budget and gauge checks. Retain the named military data-contract test and all independent arithmetic |
| `world/lore/tests/test_starting_kits.py` | Replace five human item tuples and named rejected-item blacklist with current kit reference closure, authored eligibility and independent synthetic incompatibility cases. Preserve subrace key coverage, equipment-only/wearability, commoner rarity equality and noble inherited-arm quality |
| Trade/load and place-price-scaling tests discovered from affected annotation/source references | Exercise non-sellable and keepsake candidates through assortment, addition and override routes. Buy/sell must reject before wallet/inventory/stock/progress/affinity mutation; keepsakes remain grantable/inspectable. Keep all prices, scales and balance bounds unchanged |

The selected personnel/stock fields embedded in settlement fixtures must be separated without deleting excluded location/settlement coverage. Tests for military examiner kit members remain named. Existing equipment mechanics, clergy ladders and sexual acts remain their current owner contracts.

## 6. Same-change traceability and metadata acceptance

1. Generate the effective post-cutover canonical requirement catalog. Use heading destinations in delta specs and the current per-ID inventory to map each retired annotation to exactly the invariant asserted. Generate IDs with the project tool, not hand-normalization.
2. Cover every new generic requirement directly, including fault cases. A test that only reads a registry must not claim cost ordering or rollback; a representative smoke does not replace all-row reference coverage.
3. Scan Python and JS annotations for all retired IDs and confirm none remain. Run the existing traceability check without allowlists; review unchanged requirement coverage after removed slice tests are consolidated.
4. Update `tools/test_data_freeze.json`, seed freeze reasons and module/class docstring `Data-contract test:` rationales so every shipped-content exception has the right role. Remove obsolete fixture builders and approval constants after their last caller is migrated.
5. Execute integrated project-required suites and CI evidence recording once after implementation is complete. Distinguish planning validation from runtime evidence; this proposal does not claim tests have run.
6. Prove wording-only bestiary edits, new-owner NPC addition, valid starter replacement and valid registry item/monster membership edits do not require spec edits. Prove corresponding broken relationships fail. Preserve exact E-S military pairs, all excluded contract assertions and committed state semantics.
