# Tasks

## 1. Complete deltas and maintenance handoff

- [ ] 1.1 Reconcile the two complete MODIFIED parent blocks with the then-current main requirements without dropping unrelated scenarios, preserving requirement names and action IDs; verify the initial HUD block retains original headings for the installed scenario-loss guard and only dispatch WHEN wording changes, and record the active-spec literal residue sweep in task evidence.
- [ ] 1.2 Prepare the exact before/after Purpose patch plus two mirrored HUD heading replacements and maintenance commit instructions from design.md for the explicit spec-maintenance/archive owner; verify `openspec instructions specs --change party-cutover-spec-maintenance --json` documents direct Purpose editing at the resolved root, capture the installed CLI heading-rename limitation, confirm ordinary sync preserves Purpose and no apply-worker main-spec edit has occurred.
- [ ] 1.3 Run `openspec validate party-cutover-spec-maintenance --strict`, compare canonical IDs and action allowlist against the full requirement blocks, and record the predicted merged active-spec residue/traceability result plus retained stable capability IDs and intentional deletion assertions; deliver the maintenance handoff without altering archived evidence.

## Workflow follow-up

- The archive owner first performs normal requirement synchronization. A dedicated spec-maintenance owner on primary then applies the documented casting Purpose replacement and both HUD heading replacements in main and delta together in one wording-only maintenance commit, records its SHA and changed-line audit, and validates aligned main/delta before completing this change's archive. An ordinary apply worker may not perform this step.
- The maintenance/archive owner verifies all four old phrases absent from current specs, no unexplained retired component residue, unchanged canonical IDs/action allowlist, strict spec/change validation and the ordinary post-sync `uv run --locked python -m tools.contract_gate` plus traceability. The coordinated metadata commit and these results are required before declaring this fix landed.
- Preserve the independent, still-open acceptance help deltas when synchronizing; never archive `party-management-acceptance` merely because wording maintenance is complete.
