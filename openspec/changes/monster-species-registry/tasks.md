## 1. Registry core

- [ ] 1.1 Create `world/lore/monster_species.py` with frozen `MonsterSpecies` and `MonsterVariant` dataclasses (no inheritance/override fields, no duplicate ability baseline on the species) and the shared stable-key validation on both keys, and verify with `unittest.TestCase` tests that display-name and tier changes never alter key-based identity
- [ ] 1.2 Implement construction-time membership validation — variant's `species_key` must resolve, no cross-species key collision, `default_variant_key` must name an ordinary variant of that species — with a named `MonsterSpeciesRegistryError`, and verify orphan-variant, cross-species-default, stronger-as-default, and name-does-not-classify rejection tests
- [ ] 1.3 Implement the balance-gated slots: frozen complete-value-set `combat_profile` or `None`, optional `danger_grade`, rejecting partial/non-integer/negative profiles at construction, and verify that flavour text with magic-sounding names yields `None` profile rather than inferred nonzero MP/SP/`magic_power`
- [ ] 1.4 Author the six approved bestiary species and twelve named variant records with the canonical zh-TW display/description prose, `combat_profile=None` and `danger_grade=None`, and no skill/behaviour/trait references for the six special abilities; verify with a tagged data-contract test (docstring first line `Data-contract test: <rationale>`, registered in `tools/test_data_freeze.json`) plus a negative test that the registry names no skill or behaviour keys

## 2. Public/private projection

- [ ] 2.1 Implement allowlist projections `published_species_view()` / `published_variant_view()` over the marked public fields only, and verify with a synthetic-fixture test whose distinctive author-private strings prove none of `author_hidden_truth_zh`/`author_explanation_zh`/`author_conjecture_zh` appears anywhere in a serialized published view, that a missing public field is never backfilled from private text, and that published conjecture retains its uncertainty marking

## 3. Compatibility-only habitat

- [ ] 3.1 Document and enforce that `habitat_tags` is read by no spawn/placement logic: verify with an inspection test that the module's public surface exposes no spawn/place/reconcile callable, and that a tag-matching species with no authored placement is resolvable as absent

## 4. Synchronization and observability

- [ ] 4.1 Add an idempotent species/variant mirror step to `world/lore/sync.py` emitting one `startup_step` boundary event via the `world.observability` named-import facade with registry-scoped context, and verify a twice-run no-op test and a database before/after test proving no monster/room/quest/art record is touched; run the observability lint over the new modules

## 5. Verification

- [ ] 5.1 Register `world/lore/tests/test_monster_species_registry.py` (and any further new test module) in exactly one shard of `.github/evennia-shards.json`, run the focused lore tests plus the shard-ownership contract, and run `uv run --locked python -m tools.contract_gate` plus `tools.test_data_lint check`; confirm `docs/game/commands.md` needs no update (no player-command surface change)
