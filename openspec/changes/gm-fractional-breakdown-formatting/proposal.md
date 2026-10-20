# Proposal: gm-fractional-breakdown-formatting

## Why

The authenticated GM character reader logged `ValueError: Unknown format code 'd' for object of type 'float'` at `web/gm/readers/characters.py:230`. Its percentage formatter rejects numeric values admitted by the read model, independently of ordinary party status commands.

## What Changes

- Format signed fractional percentage contributions without integer coercion or changed rule arithmetic.
- Cover fractional and integral percentages plus flat and multiplier controls through the reader and protected character-detail API.
- Retain immutable reads and section-level isolation for genuinely invalid sources.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gm-runtime-state`

## Impact

`web/gm/readers/characters.py`, existing GM-reader/API tests, owning test manifest when needed, GM inspection documentation. No party-rule, lineage or pricing change.

## Non-goals

No change in this batch fixes the ordinary pre-sync unknown-requirement-ID exit of `tools.contract_gate`. No proposal treats unexecuted acceptance steps as established gameplay defects. `party-management-acceptance` remains OPEN on its existing feature branch until fixes land and its exact browser/text journey succeeds; only its task 1.1 is checked in the apply-worker handoff. No migrations or compatibility paths are introduced.

## Evidence

`local://party-management-acceptance-blockers.md` is the complete apply-worker handoff and the source of observed failures. Its findings are accepted without rerunning the reported commands. Each change is bounded to one engineer-day, with focused regression coverage and no unrelated engine redesign.

## Batch:

```yaml
depends-on: []
```

Code-conflict notes: Reader code is disjoint from lineage query code; character-detail integration tests and `.github/evennia-shards.json` can overlap. Coordinate those hunks rather than conflating the two errors.

Declared implementation order: browser-console-save-isolation → seeded-lineage-readability → gm-fractional-breakdown-formatting → party-acceptance-deterministic-fixture → party-shop-price-contract-alignment → party-cutover-spec-maintenance → resume party-management-acceptance. The arrows declare serial integration order; only the machine-readable dependencies above are hard prerequisites. `depends-on: []` declares no hard prerequisite. All six changes must land before final acceptance resumes. Secondary GM formatting and pricing fixes remain separable and are included in that integration order.
