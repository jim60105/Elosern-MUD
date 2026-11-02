# Proposal

## Why

Our tests call `sync_grid()` 119 times across 46 modules, and every call runs on the shipped settlement world. One such test took 2.2 s with the current 31 settlement rooms. Adding the 59 national settlement maps adds roughly 500–700 rooms and their exits. That could multiply the cost of the Evennia suite and push CI shards past their time budgets.

The three nation batch changes should not generate and name about 170–230 rooms each, only to find at the end that the suite has become too slow. The cost has to be measured first, with the real generator, before any batch data lands.

## What Changes

- Add a measurement-only change. Its scope:
  1. In the working tree, temporarily generate every missing national settlement without prose: `generate --missing --nation grandia|altoria|valhalla`.
  2. Regenerate the partition and time the listed settlement-sensitive test modules. Record the timing, the sync time and the room count, before and after.
  3. Revert all the data.
- Commit only one documentation section, `docs/development/settlement-synthesis.md` § "Runtime cost". It holds the measured table and the decision derived from design D2:
  - **proceed:** the batch changes go ahead as planned;
  - **blocked:** the batch changes wait for a mitigation change, which the user then chooses.
- Commit a second section, § "Settlement-sensitive test modules". This is the canonical list of test modules to rerun after any settlement data change. Later changes reference it instead of an archived task list.
- Spec-less. No game data, code or tests are committed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true` is set.

## Impact

- `docs/development/settlement-synthesis.md`: two new sections.
- Temporary local data that is never committed: 59 settlement files and a partition. The task list checks the revert with `git status`.
- If the decision is **blocked**, `altoria-capital-river-rework` can still proceed, because it adds only 7 rooms. `grandia-settlement-maps`, `altoria-settlement-maps` and `valhalla-settlement-maps` must not be applied until a mitigation lands.

## Batch:

- depends-on: settlement-rework-and-prose
- depends-on: unpin-settlement-map-data
- conflicts: `docs/development/settlement-synthesis.md` is also edited by `settlement-terrain-fit`, `settlement-graph-generator` and `settlement-rework-and-prose`. All three come before this change. The partition file is touched only temporarily and is reverted.
