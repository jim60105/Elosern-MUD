# Proposal: party-shop-price-contract-alignment

## Why

The synthetic potion buys for 8 copper and sells for 6, while the parent UI design claims a universal half-price ratio. The authoritative shop contract admits separately configured integer prices, so the separable defect is inaccurate design wording.

## What Changes

- Amend the parent UI design to retain authoritative configured prices and one price per page without asserting a ratio.
- Pin an asymmetric synthetic buy/sell pair through real service/trade consumers and the shop view.
- Keep catalog values and economy behavior unchanged; retain the help convention already corrected by the acceptance worker.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-shop-window`

## Impact

`docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md:75`, shop-window/service regression tests and requirement annotations. `shop-economy` and commerce rulebooks remain authoritative and unchanged.

## Non-goals

No change in this batch fixes the ordinary pre-sync unknown-requirement-ID exit of `tools.contract_gate`. No proposal treats unexecuted acceptance steps as established gameplay defects. `party-management-acceptance` remains OPEN on its existing feature branch until fixes land and its exact browser/text journey succeeds; only its task 1.1 is checked in the apply-worker handoff. No migrations or compatibility paths are introduced.

## Evidence

`local://party-management-acceptance-blockers.md` is the complete apply-worker handoff and the source of observed failures. Its findings are accepted without rerunning the reported commands. Each change is bounded to one engineer-day, with focused regression coverage and no unrelated engine redesign.

## Batch:

```yaml
depends-on: []
```

Code-conflict notes: May share shop-window tests and `.github/browser-shards.json` with fixture regressions, and the parent design with other party work. This change owns only the price-authority sentence and focused asymmetric-price regression.

Declared implementation order: browser-console-save-isolation → seeded-lineage-readability → gm-fractional-breakdown-formatting → party-acceptance-deterministic-fixture → party-shop-price-contract-alignment → party-cutover-spec-maintenance → resume party-management-acceptance. The arrows declare serial integration order; only the machine-readable dependencies above are hard prerequisites. `depends-on: []` declares no hard prerequisite. All six changes must land before final acceptance resumes. Secondary GM formatting and pricing fixes remain separable and are included in that integration order.
