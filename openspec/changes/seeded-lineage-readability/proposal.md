# Proposal: seeded-lineage-readability

## Why

A real seeded member refused `系譜 艾拉`, and a separate commander GM query logged a cycle diagnostic. The relation between those failures is unresolved; valid seeded lineage must be readable through both consumers before acceptance resumes.

## What Changes

- Trace the live prerequisite graph, reverse-edge consumers, synthetic install/graft order and bounded presentation; correct the owning mechanism with a regression.
- Prove matching roots/nodes/edges for member text and panel reads in an isolated managed runtime.
- Preserve deterministic ordering, fail-closed malformed/cyclic handling and non-mutating reads.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-lineage-panel`

## Impact

`world/rules/lineage_query.py`, `world/skills/registry/` prerequisite-consumer ownership, synthetic catalog install/grafting under `web/browser_support/browser_fixtures_data/`, `commands/lineage.py`, `web/webclient/presentation/lineage.py` and their tests as diagnosis requires. Production impact is unproven.

## Non-goals

No change in this batch fixes the ordinary pre-sync unknown-requirement-ID exit of `tools.contract_gate`. No proposal treats unexecuted acceptance steps as established gameplay defects. `party-management-acceptance` remains OPEN on its existing feature branch until fixes land and its exact browser/text journey succeeds; only its task 1.1 is checked in the apply-worker handoff. No migrations or compatibility paths are introduced.

## Evidence

`local://party-management-acceptance-blockers.md` is the complete apply-worker handoff and the source of observed failures. Its findings are accepted without rerunning the reported commands. Each change is bounded to one engineer-day, with focused regression coverage and no unrelated engine redesign.

## Batch:

```yaml
depends-on: []
```

Code-conflict notes: May share synthetic startup/grafting and browser test ownership with the fixture change. Keep fixture composition in the fixture owner; fix graph/index consistency here. Shares `.github/evennia-shards.json` with the GM-reader change only if new modules are introduced.

Declared implementation order: browser-console-save-isolation → seeded-lineage-readability → gm-fractional-breakdown-formatting → party-acceptance-deterministic-fixture → party-shop-price-contract-alignment → party-cutover-spec-maintenance → resume party-management-acceptance. The arrows declare serial integration order; only the machine-readable dependencies above are hard prerequisites. `depends-on: []` declares no hard prerequisite. All six changes must land before final acceptance resumes. Secondary GM formatting and pricing fixes remain separable and are included in that integration order.
