## 1. Rule table and loader

- [ ] 1.1 Create `world/rules/rulebook/cross_lineage_unlock.yaml` with the three shipped rules per design D1 (`blade_art_mastery` over the explicit nine-key sword line at `min_level` 3; `magic_circle_comprehension` over `elemental_magic` grouped by element at `min_level` 5 / `distinct_groups` 1; `precise_mana_control` at `min_level` 5 / `distinct_groups` 2). Verify the file parses as YAML and its rule ids are unique.
- [ ] 1.2 Create `world/rules/cross_lineage_unlock.py` with the frozen rule/clause dataclasses and a module-level loader that resolves each clause's `scope` into concrete `SKILL_REGISTRY` key groups (declarative `{category, group?}` sampling ACTIVE nodes only and partitioned by `group`; explicit `{keys: [...]}` as one group). Verify the shipped table loads and exposes three rules, and that a declarative `elemental_magic` scope yields eight groups none of which contains a `*_mastery` PASSIVE node.
- [ ] 1.3 Add the load-time validator covering every rejection listed in the spec's fail-closed requirement — unknown key, empty scope, unreachable `min_level` against `proficiency_cap()`, a non-ACTIVE key named by an explicit `keys` scope, non-positive `min_level`/`distinct_groups`, empty `grants`/`requires` — each raising `ValueError` naming the rule id. Verify with synthetic rule tables built in-test, one per rejection branch, including that a declarative scope over a mixed-kind category does NOT raise.
- [ ] 1.4 Add the structural no-cycle check (design D6): intersect the union of all `grants` against the union of all scoped keys and raise `ValueError` naming both rule ids on any overlap. Verify with a synthetic two-rule table where one grants what the other samples, and a synthetic self-referential rule.
- [ ] 1.5 Build the `skill_key → rule ids` reverse index at load (design D4). Verify a key sampled by two rules resolves to both, and a key sampled by none resolves to empty.

## 2. Evaluation and granting

- [ ] 2.1 Implement the clause predicate: count groups holding at least one node whose `skill_proficiency_level()` reaches `min_level`, satisfied when that count reaches `distinct_groups`. Verify with synthetic clauses that a same-group pair fails a two-group clause while a cross-group pair passes, and that a node one level short fails.
- [ ] 2.2 Implement the grant writer: append each missing granted key to `db.skills` under the list matching its `SkillDef.kind` (design D5), leaving already-owned keys untouched and never writing proficiency. Verify idempotence (second call writes nothing, no duplicate entry) and that a granted node reads back at proficiency level 0.
- [ ] 2.3 Implement the entry point that takes an entity and a just-practised `skill_key`, walks only the reverse-indexed rules, skips rules whose grants are already fully owned, and returns the list of newly granted keys. Verify a rule with one unsatisfied clause grants nothing and a fully satisfied rule grants every key it names.

## 3. Wiring into the practice paths

- [ ] 3.1 Call the evaluator from `grant_skill_practice_xp()` immediately after `award_practice_xp()`, and append one `unlock_line()` per newly granted skill into `unlocks_out` when that sink was supplied. Verify an award that crosses a threshold grants within the same call and stages one line per granted skill.
- [ ] 3.2 Call the evaluator from the booked-hourly practice settlement after its `award_practice_xp()` so the two practice entry points cannot diverge (design D3). Verify a booked settlement that crosses a threshold grants the same keys as the per-use path.
- [ ] 3.3 Confirm no read path gained a side effect: verify that querying owned skills, and running an action preview, produce no grant and no write to `db.skills`.

## 4. Traceability and gates

- [ ] 4.1 Annotate the new tests with `@covers_requirement("cross-lineage-unlock::<normalized-name>")` for every requirement in the delta spec, taking the ids from `uv run --locked python -m tools.spec_traceability list` rather than hand-assembling them.
- [ ] 4.2 Verify the new test module names no shipped content beyond the clean-import assertion (`uv run --locked python -m tools.test_data_lint check` passes with no new entry in `tools/test_data_freeze.json`).
- [ ] 4.3 Run `openspec validate cross-lineage-unlock --strict` and the focused test label for `world.rules.tests.test_cross_lineage_unlock`, plus `world.rules.tests.test_progression` for the wiring, and confirm both are green.
