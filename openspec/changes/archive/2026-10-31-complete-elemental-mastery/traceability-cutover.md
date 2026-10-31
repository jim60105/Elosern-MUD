# Traceability cutover

## Current canonical IDs

These identifiers were obtained from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/mud-mastery-proposal-requirements.json` during proposal discovery. New requirement IDs must be obtained from the same tool against a merged-equivalent main-spec tree during implementation; no guessed future ID is authorized.

| Alias in this document | Current canonical ID |
| --- | --- |
| graph | `skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed` |
| gate | `skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate` |
| seed | `skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly` |
| mastery | `element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells` |
| panel | `skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free` |
| cast | `freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step` |

## Authored topology requirements to retire

The four `skill-lineage` requirements named below become REMOVED in this change. Their content remains in registry/lore data. They must not acquire compatibility IDs or tests that copy shipped edge lists.

| Retired heading | Current canonical ID suffix after `skill-lineage::` |
| --- | --- |
| The fire lineage ships as the authored branching tree with a two-parent canopy | `the-fire-lineage-ships-as-the-authored-branching-tree-with-a-two-parent-canopy` |
| The wind lineage ships as the authored two-root branching tree with a two-parent canopy | `the-wind-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy` |
| The ice lineage ships as the authored two-root branching tree with a two-parent canopy | `the-ice-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy` |
| The lightning lineage ships as the authored two-root branching tree with a two-parent canopy | `the-lightning-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy` |

## Assertion-role map

All affected production catalog assertions currently live in `world/skills/tests/test_spell_catalogs.py`. Update that existing module and its existing entry in `tools/test_data_freeze.json`; do not add a module or shard.

| Existing test(s) | Role and defect detected after cutover | Target requirement |
| --- | --- | --- |
| `LightningLineageTreeCatalogTests.test_lightning_tree_edges_are_as_designed`, `IceLineageTreeCatalogTests.test_ice_tree_edges_are_as_designed`, `FireLineageTreeCatalogTests.test_fire_tree_edges_are_as_designed`, `WindLineageTreeCatalogTests.test_wind_tree_edges_are_as_designed` | Registry-contract. Replace copied node/edge/child lists with generic reference, positive-threshold, acyclicity and reverse-cache consistency assertions over the current catalog. Detect a dangling/reversed/missing cached edge without approving authored topology | graph |
| The two `test_mastery_passives_stay_out_of_the_graph` methods, `test_lightning_passives_stay_out_of_the_graph`, and `test_wind_passives_stay_out_of_the_graph` | Registry-contract. Replace obsolete mastery isolation assertions with generic ordinary-terminal coverage and cap-preservation relationships. Keep independent enhancement isolation by category/role rather than a copied mastery roster | new `Elemental mastery prerequisites cover every ordinary branch`; temporarily mastery |
| New cases in existing `world.rules.tests.test_skill_lineage` | Synthetic-mechanism. A disconnected branch/side leaf prevents grant or entitlement until every declared edge qualifies; no production node keys | new whole-tree requirement; temporarily mastery |
| New cases in existing `world.rules.tests.test_progression.test_derived_and_cross_lineage_unlocks` and `world.rules.tests.test_cast_settlement` | Synthetic-mechanism and real settlement integration. Both award paths grant, exactly-once notices, identity denial, raw/cache rollback and lawful retry | new `Practice acquires a newly qualified elemental mastery atomically`; temporarily mastery plus existing substantive settlement/notification requirement IDs obtained from the tool |
| Existing freeform fixture consumers | Synthetic-mechanism or representative-smoke, retaining their existing classification. Give positive cases lawful owned closure; keep separate bare-key/conferred negative controls. Preserve actual payment/resolution/reload in smoke | mastery / cast / gate / seed, according to the assertions |
| Existing lineage query completion cases | Synthetic-mechanism. ACTIVE XP cap plus PASSIVE usable ownership determines completion, with no passive XP | panel |

Use one discoverable test per distinct mechanism where consolidation removes duplicate data-echo checks. Preserve parser vocabulary tests and unrelated registered content contracts in `test_spell_catalogs.py`.

## Cutover timing and gates

During implementation record the exact method-to-ID assignments before changing decorators. For ADDED requirements use the documented nearest current mastery ID until spec synchronization. The archive integration owner must synchronize the REMOVED/ADDED main requirements and reassociate retired annotations/new tests using tool-generated merged-tree IDs in the same integration commit. No retired decorator may survive that synchronized tree, and no future-only ID may be inserted into a current-only tree.

Pre-sync `contract_gate` checks the still-current main contract and cannot certify the proposed requirements. Also run the traceability checker against a disposable merged-equivalent spec/test tree before archive to establish that the cutover map covers every surviving and new requirement. Do not edit primary main specs during proposal or use an allowlist/flag to suppress a missing association. If current-only annotations would become invalid when replacing data-echo tests, keep that replacement and its decorator reassociation together with the synchronized spec cutover, while landing the new independent generic tests with behavior implementation first.

## Applied cutover (implementation record)

The synchronized main-spec cutover and the decorator reassociation landed with
the behavior in the implementation commits, so this branch is a synchronized
tree: no future-only ID is used anywhere and no retired ID survives. Canonical
IDs below were read from `uv run --locked python -m tools.spec_traceability list`
after the sync.

### Main-spec changes applied

| Capability | Requirement | Operation | Canonical ID |
| --- | --- | --- | --- |
| `skill-lineage` | SkillPrerequisite declares registry edges and load validation fails closed | modified | `skill-lineage::skillprerequisite-declares-registry-edges-and-load-validation-fails-closed` |
| `skill-lineage` | can_use_skill is the single shared use-eligibility predicate | modified (closure + 2 scenarios) | `skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate` |
| `skill-lineage` | The freeform scale ladder is anchored to proficiency | modified (lawful entitlement) | `skill-lineage::the-freeform-scale-ladder-is-anchored-to-proficiency` |
| `skill-lineage` | Import and scene-build auto-seed prerequisite proficiency exactly | modified (2 scenarios; caller-count heading retained) | `skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly` |
| `skill-lineage` | The fire / wind / ice / lightning lineages ship as the authored trees | REMOVED (4 requirements) | retired: `…the-fire-lineage…`, `…the-wind-lineage…`, `…the-ice-lineage…`, `…the-lightning-lineage…` |
| `element-mastery` | Mastery ownership entitles freeform scaling of the element's eligible spells | modified (3 scenarios) | `element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells` |
| `element-mastery` | Elemental mastery prerequisites cover every ordinary branch | ADDED | `element-mastery::elemental-mastery-prerequisites-cover-every-ordinary-branch` |
| `element-mastery` | Practice acquires a newly qualified elemental mastery atomically | ADDED | `element-mastery::practice-acquires-a-newly-qualified-elemental-mastery-atomically` |
| `skill-lineage-panel` | The lineage read model is pure, derived, and side-effect-free | modified (completion, readiness, 2 scenarios) | `skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free` |
| `freeform-casting` | The resolver gates scaled casts at the ownership step | modified (lawful closure + 1 scenario) | `freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step` |

The obsolete `element-mastery` Purpose was replaced with the lawful learned-mastery
description during the same sync.

### Retired annotations and their replacements

| Retired annotation (deleted) | Replacement assertion | Replacement annotation |
| --- | --- | --- |
| `LightningLineageTreeCatalogTests.test_lightning_tree_edges_are_as_designed` | `LineageGraphContractTests.test_every_declared_edge_references_a_registered_row_at_a_positive_level` | graph |
| `IceLineageTreeCatalogTests.test_ice_tree_edges_are_as_designed` | `LineageGraphContractTests.test_reverse_cache_matches_the_declared_edges_exactly` | graph |
| `FireLineageTreeCatalogTests.test_fire_tree_edges_are_as_designed` | `LineageGraphContractTests.test_prerequisite_graph_is_acyclic_and_drains_completely` | graph |
| `WindLineageTreeCatalogTests.test_wind_tree_edges_are_as_designed` | the same catalog-wide generic graph-contract assertions | graph |
| `test_mastery_passives_stay_out_of_the_graph` (fire + ice) and `test_lightning_passives_stay_out_of_the_graph` | `ElementalMasteryCoverageContractTests.test_each_mastery_declares_exactly_its_elements_ordinary_terminals` | new whole-tree requirement |
| those same isolation methods | `ElementalMasteryCoverageContractTests.test_mastery_edges_leave_every_ordinary_terminal_cap_unchanged` | new whole-tree requirement |
| those same isolation methods | `ElementalMasteryCoverageContractTests.test_restricted_and_unrelated_rows_are_never_mastery_prerequisites` | new whole-tree requirement |
| `WindLineageTreeCatalogTests.test_wind_passives_stay_out_of_the_graph` | `ElementalMasteryCoverageContractTests.test_independent_passives_are_never_prerequisites` | new whole-tree requirement |

No test in the module approves a node roster, a display label or a balance
magnitude. The parser-vocabulary contract stays, and the module's
`Data-contract test:` tag, the `tools/test_data_freeze.json` reason and the
`tools/test_data_lint_seed.json` reason now read identically: "closed
spell-parser vocabulary plus generic lineage-graph and mastery-coverage
relationships".

### New-mechanism assertions and their recorded targets

| Mechanism | Test | Annotation |
| --- | --- | --- |
| whole-tree closure, disconnected branches, side leaf, cap preservation, no passive prerequisite | `test_skill_lineage.MasteryWholeTreeTests` (5 cases) | new whole-tree requirement |
| lawful freeform entitlement: bare key, conferred ancestor, identity-ineligible ancestor, restricted ancestor, low internal edge, purity | `test_freeform_casting…FreeformMasteryClosureTests` (7 cases) | element-mastery ownership requirement |
| acquisition on use and study, optional sink, repeats, repaired ancestor, simulated award, passive practice | `test_progression.test_derived_and_cross_lineage_unlocks.MasteryAcquisitionTests` (6 cases) | new acquisition requirement |
| acquisition inside the settlement transaction, rollback and retry | `test_cast_settlement.MasteryGrantSettlementTests` (2 cases) | new acquisition requirement |
| passive completion, usable/unusable passive, unowned capped ACTIVE, readiness, genuine XP facts | `test_lineage_query.PassiveCompletionTests` (5 cases) plus the rewritten completion case | panel read-model requirement |
| restricted-ancestor passive submission | `test_action_pipeline_rejections.ActionPipelineRejectionTests.test_a_restricted_ancestor_rejects_a_passive_without_dereferencing_an_edge` | gate requirement |
| preset/import parity for a mastery-declaring kit | `test_preset_lineage_and_npc_policy.PresetLineageParityTests` (2 added cases) | seed requirement |

### Verification

- `uv run --locked python -m tools.spec_traceability check`: 2663 requirements,
  12148 associations, 2663 covered, 0 uncovered, 0 errors.
- `uv run --locked python -m tools.contract_gate`: passed (reference-context,
  traceability, observability, test-data, manifests, contracts).
- Documentation limits: only `docs/lore/skill-trees/fire.md` and
  `docs/lore/skill-trees/light.md` carried a mastery statement before this
  change; both were rewritten along with `docs/lore/skill-trees/index.md`,
  `docs/lore/magic-system.md` and the progression design (§9.1, §9.2, §12). The
  other six element pages carry no mastery statement, so no stale claim exists
  there to correct.
