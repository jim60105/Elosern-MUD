# Proposal: browser-console-save-isolation

## Why

Managed browser console interventions refuse with `snapshot_failed` because browser-only settings omit `GM_SAVES_ROOT`. The apply-worker handoff establishes the missing setting and blocked teleport without evidence of a production save defect.

## What Changes

- Give managed browser runtimes private save roots and production-equivalent save-setting semantics, including retention.
- Prove a real protected teleport creates its pre-intervention snapshot and commits the target location without touching developer persistence.
- Retain refusal-before-mutation when snapshots fail and document the private layout.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-browser-verification`

## Impact

`web/tests/browser/browser_settings.py`, managed runtime environment/lifecycle ownership, save/console integration tests, exact shard manifests and browser-runtime documentation. Production snapshot semantics remain unchanged.

## Non-goals

No change in this batch fixes the ordinary pre-sync unknown-requirement-ID exit of `tools.contract_gate`. No proposal treats unexecuted acceptance steps as established gameplay defects. `party-management-acceptance` remains OPEN on its existing feature branch until fixes land and its exact browser/text journey succeeds; only its task 1.1 is checked in the apply-worker handoff. No migrations or compatibility paths are introduced.

## Evidence

`local://party-management-acceptance-blockers.md` is the complete apply-worker handoff and the source of observed failures. Its findings are accepted without rerunning the reported commands. Each change is bounded to one engineer-day, with focused regression coverage and no unrelated engine redesign.

## Batch:

```yaml
depends-on: []
```

Code-conflict notes: Shares browser runtime documentation and `.github/browser-shards.json` with fixture/lineage changes; serialize manifest hunks. Shares a capability file with the fixture change, whose ADDED requirement is disjoint.

Declared implementation order: browser-console-save-isolation → seeded-lineage-readability → gm-fractional-breakdown-formatting → party-acceptance-deterministic-fixture → party-shop-price-contract-alignment → party-cutover-spec-maintenance → resume party-management-acceptance. The arrows declare serial integration order; only the machine-readable dependencies above are hard prerequisites. `depends-on: []` declares no hard prerequisite. All six changes must land before final acceptance resumes. Secondary GM formatting and pricing fixes remain separable and are included in that integration order.
