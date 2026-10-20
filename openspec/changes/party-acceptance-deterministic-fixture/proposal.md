# Proposal: party-acceptance-deterministic-fixture

## Why

Existing browser fixture modes cannot supply the exact co-located 艾拉／卡恩 journey and actor-owned skills required by `party-management-acceptance`. The closed GM registry lacks creation, renaming, binding and skill-grant verbs, so its current GM-only setup policy is unexecutable.

## What Changes

- Explicitly authorize one deterministic pre-session acceptance seed in the original acceptance design; retain GM-only runtime interventions after boot.
- Add an opt-in dedicated fixture with exact named companions, actor-owned heal/opening skills, useful bags/equipment, wounded targets, a finishable monster and a traversable exit.
- Leave existing fixture modes unchanged and establish membership, co-location and legal previews through real consumers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-browser-verification`

## Impact

Browser seed runner and fixture helpers, managed runtime option, exact browser/Evennia shard ownership, fixture docs and `openspec/changes/party-management-acceptance/design.md`. The existing acceptance apply owner performs the policy amendment on its feature branch; proposals here never edit that branch.

## Non-goals

No change in this batch fixes the ordinary pre-sync unknown-requirement-ID exit of `tools.contract_gate`. No proposal treats unexecuted acceptance steps as established gameplay defects. `party-management-acceptance` remains OPEN on its existing feature branch until fixes land and its exact browser/text journey succeeds; only its task 1.1 is checked in the apply-worker handoff. No migrations or compatibility paths are introduced.

## Evidence

`local://party-management-acceptance-blockers.md` is the complete apply-worker handoff and the source of observed failures. Its findings are accepted without rerunning the reported commands. Each change is bounded to one engineer-day, with focused regression coverage and no unrelated engine redesign.

## Batch:

```yaml
depends-on: browser-console-save-isolation
depends-on: seeded-lineage-readability
```

Code-conflict notes: Owns acceptance design policy wording, so coordinate with `os-apply-party-management` before implementation. Overlaps lineage synthetic boot helpers and save runtime docs/manifests. Do not check acceptance tasks or replace its real UI journey with fixture assertions.

Declared implementation order: browser-console-save-isolation → seeded-lineage-readability → gm-fractional-breakdown-formatting → party-acceptance-deterministic-fixture → party-shop-price-contract-alignment → party-cutover-spec-maintenance → resume party-management-acceptance. The arrows declare serial integration order; only the machine-readable dependencies above are hard prerequisites. `depends-on: []` declares no hard prerequisite. All six changes must land before final acceptance resumes. Secondary GM formatting and pricing fixes remain separable and are included in that integration order.
