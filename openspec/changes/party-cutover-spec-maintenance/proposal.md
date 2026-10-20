# Proposal: party-cutover-spec-maintenance

## Why

Four active-spec references retain obsolete skill-book surface wording after the component cutover. This residue keeps acceptance task 2.1 open despite no surviving retired runtime components in the handoff sweep.

## What Changes

- Carry complete HUD and action-dispatch MODIFIED parent-requirement blocks, preserving canonical requirement IDs and action IDs; correct dispatch wording through normal sync.
- Assign the standalone casting Purpose correction and two exact HUD heading replacements to explicit spec-maintenance ownership outside ordinary apply. The installed CLI treats renamed scenario headings as dropped scenarios, so the complete HUD block retains its old headings until coordinated maintenance updates main and delta together.
- Record before/after metadata text and run the active-spec residue and post-sync traceability checks under the maintenance/archive owner.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`
- `webclient-action-dispatch`

## Impact

Two complete requirement deltas plus wording-only maintenance of the casting Purpose and HUD scenario headings by the spec-maintenance/archive owner. No runtime code, requirement bodies, intentional deletion assertions or archived evidence changes.

## Non-goals

No change in this batch fixes the ordinary pre-sync unknown-requirement-ID exit of `tools.contract_gate`. No proposal treats unexecuted acceptance steps as established gameplay defects. `party-management-acceptance` remains OPEN on its existing feature branch until fixes land and its exact browser/text journey succeeds; only its task 1.1 is checked in the apply-worker handoff. No migrations or compatibility paths are introduced.

## Evidence

`local://party-management-acceptance-blockers.md` is the complete apply-worker handoff and the source of observed failures. Its findings are accepted without rerunning the reported commands. Each change is bounded to one engineer-day, with focused regression coverage and no unrelated engine redesign.

## Batch:

```yaml
depends-on: []
```

Code-conflict notes: Shares `webclient-contextual-hud` with the still-open acceptance delta, but modifies the existing reference-workspace parent while acceptance owns separate help requirements. Merge by requirement name; never copy an old whole capability over its current contents. Purpose maintenance is a separate authorized metadata step, never an apply-worker edit.

Declared implementation order: browser-console-save-isolation → seeded-lineage-readability → gm-fractional-breakdown-formatting → party-acceptance-deterministic-fixture → party-shop-price-contract-alignment → party-cutover-spec-maintenance → resume party-management-acceptance. The arrows declare serial integration order; only the machine-readable dependencies above are hard prerequisites. `depends-on: []` declares no hard prerequisite. All six changes must land before final acceptance resumes. Secondary GM formatting and pricing fixes remain separable and are included in that integration order.
