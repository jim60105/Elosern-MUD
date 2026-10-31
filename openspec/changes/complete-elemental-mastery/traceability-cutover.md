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
