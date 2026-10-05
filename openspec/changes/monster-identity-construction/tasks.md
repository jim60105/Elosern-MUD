## 1. Typeclass identity

- [ ] 1.1 Add persistent `species_key` / `variant_key` attributes to `typeclasses/monsters.py` plus guarded read/write for threat tier (read-through to the variant record for species-backed individuals; a contradicting write raises a named error; tier-only individuals keep the plain attribute), and verify with `EvenniaTest` cases covering the species-backed and tier-only shapes side by side, including a registry display-name edit that leaves identity unchanged

## 2. Construction entry point

- [ ] 2.1 Create the species-backed individual construction entry point in `world/rules/` that validates species key, variant key, and their registry membership before persistence and applies the approved combat configuration through the existing trait path, and verify unknown-key, cross-species, and failed-validation cases leave no individual behind (database before/after comparison)
- [ ] 2.2 Extend `world/rules/traits.py` with variant-aware configuration resolution: approved complete profile when present, otherwise the existing tier-band construction at the variant's declared tier, with one `world.observability` boundary info event naming individual/species/variant and `numeric_source`, and verify (a) flavour-named variants still resolve the interim source's zero MP/SP/`magic_power` literally, (b) an authored synthetic complete profile replaces the source with no signature change, (c) two constructions for differently progressed players are identical, (d) stored traits carry no multiplier
- [ ] 2.3 Verify existing tier-only callers (`world/maps/wilderness_population.py`, `world/quests/scene_builder.py`, combat initiation) are behaviourally unchanged by a focused run of their current tests

## 3. Kill accounting

- [ ] 3.1 Make the step-7 `target_defeated` entry in `world/rules/action/event_log.py` carry registered species/variant keys for species-backed monsters and omit them for tier-only targets, and verify with an integration test through `ActionResolver` that a species-backed defeat carries the keys and a tier-only defeat is byte-identical to today
- [ ] 3.2 Extend `world/quests/planner.py` counting to persist per-record already-counted individual identities (cleared on stage transition like existing bindings), so a duplicate or redelivered defeat entry for a counted identity advances nothing, and verify with planner tests using synthetic fixtures: duplicate-event idempotence, two same-name individuals counting separately, and a fresh newcomer not satisfying an old counted set or binding

## 4. Verification

- [ ] 4.1 Register every new/moved test module in exactly one shard of `.github/evennia-shards.json` and run the shard-ownership contract locally per AGENTS.md (single-token `--env-file` form)
- [ ] 4.2 Run the focused typeclass, rules, and quest planner tests plus `uv run --locked python -m tools.contract_gate` and the observability lint for the changed modules; confirm no player-command docs update is required and `tools.test_data_lint check` passes with synthetic species only
