# Tasks

Ground rules:
- Commit only `docs/development/settlement-synthesis.md`.
- Every data file this change creates or edits must be reverted before the commit.
- Run one test module per standalone command, with no pipes or redirects.

## 1. Baseline

- [ ] 1.1 Run each D1 module once on the clean tree with `uv run evennia test --keepdb --settings settings.py <label>`. Check: you recorded each module's `Ran N tests in X s` line, and the room and exit counts from the D1 command.

## 2. Temporary full generation

- [ ] 2.1 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation grandia`, then the same command with `altoria`, then with `valhalla`. Check: the new settlement files exist, and you recorded every location whose generation failed together with its error. A failure does not stop this change.
- [ ] 2.2 Run `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`. Check: `check_map_sources.py` reports `district partition: current`. If regeneration is refused, record the reason and use the counts only. Skip the after-timings in that case.
- [ ] 2.3 Rerun each D1 module and the D1 count command. Check: you recorded every after-value.

## 3. Revert and document

- [ ] 3.1 Revert the data:
  - delete every settlement file listed as created in 2.1;
  - restore the partition with `git checkout -- world/maps/data/district_partition.json`.

  Check: `git status --porcelain content world/maps/data` prints nothing.
- [ ] 3.2 Add the section "Runtime cost" to `docs/development/settlement-synthesis.md`. It holds:
  - a table with columns module, before seconds, after seconds and ratio;
  - the room and exit counts, before and after;
  - the list of failed locations;
  - the D2 decision word, **proceed** or **blocked**, with the rule.

  Add the section "Settlement-sensitive test modules" with the D3 list, notes and "Residual pin rule", verbatim.

  Check: `git status --porcelain` lists only that doc. `grep -c "test_travel_plan" docs/development/settlement-synthesis.md` prints at least 1.
- [ ] 3.3 Run `openspec validate settlement-sync-cost-probe --strict`. Check: it is valid. The hand-off states the decision word, and when it is **blocked** it explicitly says that the nation batch changes must not be applied yet.
