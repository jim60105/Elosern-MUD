# Design: Spec-owned party cutover wording maintenance

## Context

Handoff issue 4 identifies exactly four residuals in current main specs. The HUD bodies already describe the party window. Requirement names define canonical IDs and must remain unchanged. Existing sync/archive skills explicitly preserve an established main spec's Purpose; putting a Purpose in a requirement delta cannot update it.

## Goals / Non-Goals

Correct the four current-contract residuals with explicit ownership. Preserve runtime action allowlists, historical archives and intentional deletion assertions. No apply-worker direct main-spec edit, wholesale capability rewrite, changed requirement ID or revised gameplay contract is authorized.

## Decisions

The two HUD headings become `The party skill tab states its counts honestly` and `The party skill tab states its skill counts and graphical actions`. Their entire `Reference surfaces render in a bounded workspace drawer with one modal contract` parent requirement is retained in a MODIFIED delta. Change the action-dispatch WHEN phrase from `and SkillBook casting changes` to `and party-window skill casting changes` in the complete `Action registries are allowlisted and duplicate-safe` parent block. Keep all enumerated action IDs, validators and adapters byte-identical.

### Installed CLI scenario-name constraint

Strict validation of the complete renamed HUD block returned: `MODIFIED "Reference surfaces render in a bounded workspace drawer with one modal contract" omits scenario(s) the current spec still has`, naming the two old headings and reporting 16 current and 16 modified scenarios with two additions. The installed `core/validation/validator.js` scenario-loss guard compares names and exposes no scenario-rename operation. This observed CLI constraint refines the handoff's suggested delta-only route; no validator suppression, tool modification or duplicate obsolete scenario is proposed.

The proposal therefore retains the full HUD parent with its original scenario headings, making the initial delta strict-valid. After normal requirement sync, the explicit spec-maintenance owner applies the two heading replacements to both current main HUD and this change's complete HUD delta in one maintenance commit. Bodies and parent requirement names stay byte-identical. Keeping main and delta aligned lets subsequent strict validation and archive comparisons pass without retaining obsolete headings in current specs. The full HUD delta is intentionally behavior-preserving before that metadata step.

### Supported Purpose metadata procedure and owner

Use the metadata-edit procedure documented by `openspec instructions specs --change party-cutover-spec-maintenance --json`: for an established capability's Purpose, directly edit that main spec under the CLI-resolved planning root. This is a dedicated **spec-maintenance-owner** action with explicit authorization from this proposal; it is outside an ordinary apply worker's scope and outside requirement synchronization. It requires no change to sync/archive skills and no new CLI command. Regular sync continues to preserve all established Purpose sections.

Before:

> Provide authoritative graphical skill use from SkillBook through the existing field settlement and combat-initiation rules, with accessible target selection, truthful availability and a verified redesigned browsing surface.

After:

> Provide authoritative graphical skill use from the party window's skill tab through the existing field settlement and combat-initiation rules, with accessible target selection, truthful availability and a verified redesigned browsing surface.

The apply worker prepares the two complete deltas, the before/after metadata patch record and the handoff, and leaves main specs untouched. The archive owner first syncs the complete requirement deltas through the normal workflow. The explicit spec-maintenance owner then applies the single Purpose replacement at `openspec/specs/webclient-skillbook-casting/spec.md` and the two HUD heading replacements in main and delta together in a separate wording-only maintenance commit on primary, outside automatic delta merging. Its changed-line audit must show only that Purpose and those two mirrored scenario headings changed, with no requirement-body, ID or other Purpose change. Record this metadata commit before declaring the fix landed, then validate the aligned change/main specs and finish this change's archive. An archive owner may perform both roles explicitly, but never claim requirement sync changed Purpose or performed scenario renaming.

## Risks / Trade-offs

The long HUD parent block risks omitted scenarios; preserve the full block and compare by requirement/scenario before sync. The still-open acceptance help deltas may touch the same capability file; merge by parent requirement name and retain both changes. The capability key `webclient-skillbook-casting` remains a canonical identifier and is not renamed or forbidden by the residue search.

## Verification and documentation

Prepare a literal active-spec sweep for the four old phrases and compare retired exact/kebab component names across client source, static JS, tests and current specs using the handoff's categories. Distinguish stable capability IDs and intentional negative assertions from obsolete UI wording. The maintenance owner requires zero unexplained active residue, strict change/spec validation, unchanged requirement IDs/action allowlist and post-sync `uv run --locked python -m tools.contract_gate`/traceability. Keep archived evidence unchanged. The pre-sync help requirement-ID failure remains expected and receives no suppression or checker change.
