## Batch order (dark wave — integration contract in ./design.md)

0. Predecessors (ALL must be merged before this change starts; this change authors data only over their shipped vocabulary):
   1. `dark-erosion-leech` (the `caster_share` rate clause)
   2. `dark-self-recovery-missing-fraction` (the `self_heal:missing_fraction:<f>` grammar)
   Both are archived-and-merged prerequisites; neither constrains the other (file-disjoint), this change is strictly after both.

## 1. Registry swap + rulebook data (data only)

- [x] 1.1 Confirm both predecessor contracts in design.md D3 are merged and inspect current source/exported references (codegraph/LSP) for the dark registry block, the dev-era buff keys (`dark_atk_down`, `dark_curse`, `dark_corrosion`, `fear`) and every dev-era registry key before editing; if any mechanic from the D1 coverage table is missing, STOP and fix it in its owning behavior change — do not bolt code onto the catalog.
 [x] 1.2 Author the 13-node tree exactly per design.md D1 (keys/labels/targets/MP costs/prerequisites/coefficient+policies/effect bindings), deleting `dark_atk_down`'s binding and adding `curse_spread`/`shadow_blight`/`abyssal_apotheosis` wholesale without aliases; verify the two-parent capstone (冥界審判 Lv.10 + 虛空湮滅 Lv.10) validates at registry load through the existing lineage validator and tip caps derive unchanged.
 [x] 1.3 Author the dark rulebook rows per D1/D2: `dark_weaken` (−3 atk/15 s), `dark_curse` re-home (−5×3/20 s), `dark_spread` (−8 atk/def/30 s), `dark_apotheosis` (−25 atk/def/90 s), `dark_corrosion` re-home (−12/10 s, 300 s, `caster_share: 1.0`), `dark_corrosion_deep` (−18/10 s, 300 s, `caster_share: 1.0`), `fear` duration 60→40, and the one `fear_locks_actions` modifier row (`actions_per_turn: 0`) — every row ordinary vocabulary, no new grammar beyond the predecessors' shipped clauses.
 [x] 1.4 Sync `world/rules/rulebook/status_display.yaml` per design.md D2b (delete `dark_atk_down`; add `dark_weaken`/`dark_spread`/`dark_apotheosis`/`dark_corrosion_deep`/`fear_locks_actions` rows at the table's label/severity conventions) — the shipped import-time coverage check fails closed on any drift between the file and the live buff keys ∪ modifier rule IDs.
 [x] 1.5 Buff-key census: no dangling `buff_apply:`/`self_buff_apply:` target; `dark_atk_down` gone from buffs.yaml, registry and status_display.yaml with no alias; `fearless_brooch`'s `immune: [fear]` row untouched (key unchanged); `test_buffs.py`'s dev-era numeric assertions updated to the re-homed values (behavior assertions kept, no row mirroring added); `world/rules/tests/test_status_display.py` green (set equality against the post-change displayable set).

## 2. Echo-test retirement and docs hygiene

- [ ] 2.1 Remove the dark `DARK_SPELL_CATALOG` table and its test class from `world/skills/tests/test_spell_catalogs.py` and the dark rows from the tier-correspondence table in the cost-tier test, in-file; adjust a `tools/test_data_lint.json` per-file entry only where its file stops naming shipped content as that linter's output decides; verify remaining suites' substantive coverage is untouched (no waivers).
- [ ] 2.2 Docs check under the node-data authority rule: `docs/lore/skill-trees/dark.md` untouched; `docs/lore/magic-system.md` §3 dark row edited ONLY if a real contradiction surfaces (none found at authoring — record the check); `tests/test_command_docs.py` untouched (no command surface changes); the 2026-08-12 design doc is frozen history — never edited.

## 3. Behavioral evidence and integration

- [ ] 3.1 Disposable offline engine scenario exercising each distinct D1 composition through real casts (debuff ladder read-back at authored values + expiry; fear action-lock incl. key-independence from an ice still marker; erosion → full-HP leech incl. area per-victim origins and dead-origin silence; execution bypass vs high defense; devastation rider; missing-fraction recovery at 10 %/15 %; capstone's three-component settlement; branch/convergence gates + two-parent capstone through the lineage engine): observe HP/stats/buffs/locks/practice and delete only after full proof.
- [ ] 3.2 Synthetic behavior tests for settlement paths not pinned by the sibling suites in a new module `world/rules/tests/test_dark_curse_erosion.py` (mixed-composition capstone settlement incl. leech-plus-self-heal non-double-pricing; fear lock + cleanse independence; family prerequisite/capstone gates on dark-shaped synthetic data). No catalog-row equality, key-set, cost/tier table or skill-tree-table echo assertions anywhere (ratified NON-GOAL).
- [ ] 3.3 Finalize `.github/evennia-shards.json` (this change owns the wave's last manifest edit): register new non-browser modules in exactly one shard; verify the ownership optimization contract test.
- [ ] 3.4 Run the focused labels below after editing stops; `tools.observability_lint check` in the same batch; `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate dark-spell-catalog --strict`. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; annotate exactly the tests establishing them (the removed 暗-element ID leaves the ledger with its requirement).

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_spell_catalogs world.rules.tests.test_cost_tiers world.rules.tests.test_skill_lineage world.rules.tests.test_dark_curse_erosion world.rules.tests.test_buffs world.rules.tests.test_combat_modifiers world.rules.tests.test_status_display
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate dark-spell-catalog --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. `world.rules.tests.test_dark_curse_erosion` is the intended synthetic settlement module owned by this change, not an existing-test claim. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
