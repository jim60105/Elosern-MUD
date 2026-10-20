# Design: Spec-owned party cutover wording maintenance

## Context

Handoff issue 4 identifies exactly four residuals in current main specs. The HUD bodies already describe the party window. Requirement names define canonical IDs and must remain unchanged. Existing sync/archive skills explicitly preserve an established main spec's Purpose; putting a Purpose in a requirement delta cannot update it.

## Evidence

### Delta reconciliation

Verified against the main specs at primary `67dac400`, the base of the feature branch. Both deltas carry complete parent-requirement blocks.

- `webclient-contextual-hud`: the main spec has 67 requirements; the delta carries the one complete parent `Reference surfaces render in a bounded workspace drawer with one modal contract`. Main and delta have the same 16 scenario headings in the same order, and their non-blank line content is identical. The delta therefore retains the current headings `The skill-book drawer states its counts honestly` (main line 1232) and `The skill-book drawer states its skill counts and cast syntax` (main line 1272), which the installed scenario-loss guard requires.
- `webclient-action-dispatch`: the main spec has 13 requirements; the delta carries the complete parent `Action registries are allowlisted and duplicate-safe` with the same 8 scenario headings. Exactly one line differs: the WHEN phrase changes from `the practice-webclient, gallery management, personal official-art preference, correspondence, NPC author-editor, dream-sleep-surface and SkillBook casting changes` to `... and party-window skill casting changes`. The 67 backticked action IDs in the allowlist scenario are byte-identical and unique, from `account.character.create` through `party.view_member`.

Canonical requirement IDs are unchanged because both requirement names are byte-identical: `webclient-contextual-hud::reference-surfaces-render-in-a-bounded-workspace-drawer-with-one-modal-contract` and `webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe`. Scenario headings are not part of a requirement ID, so the deferred heading replacements do not alter them.

### Active-spec literal residue sweep

Searching `openspec/specs` for the four exact phrases finds exactly four occurrences at preparation time:

1. `openspec/specs/webclient-skillbook-casting/spec.md:3` - the Purpose line starting `Provide authoritative graphical skill use from SkillBook ...`
2. `openspec/specs/webclient-contextual-hud/spec.md:1232` - `#### Scenario: The skill-book drawer states its counts honestly`
3. Same file, line 1272 - `#### Scenario: The skill-book drawer states its skill counts and cast syntax`
4. `openspec/specs/webclient-action-dispatch/spec.md:66` - the WHEN phrase ending `and SkillBook casting changes`

A broader `SkillBook|skill-book|Skill Book|技能書` sweep over active specs adds only intentional or stable references: the governed-deletion assertion in `openspec/specs/webclient-component-showcase/spec.md:613`, where the frozen component wave deletes `SkillBook` among other retired components, and the retained capability directory and key `webclient-skillbook-casting`. The retired exact/kebab component-name sweep over client source, static JS, tests and current specs finds only comments describing replacements, generic panel validator names such as `validateLineagePanel` and `validatePartyInventoryPanel`, and negative-presence or governed-deletion assertions; no surviving retired component file, import, manifest title or production CSS selector. Archived evidence is unchanged.

### Installed CLI heading-rename limitation

OpenSpec 1.14.1. A throwaway copy containing the current main HUD spec and this change's HUD delta, with only the two scenario headings renamed, failed `openspec validate test-cap --strict` with exit 1:

```text
MODIFIED "Reference surfaces render in a bounded workspace drawer with one modal contract" omits scenario(s) the current spec still has: "The skill-book drawer states its counts honestly", "The skill-book drawer states its skill counts and cast syntax". The modified block has 16 scenarios; the current spec has 16 scenarios. It adds 2 scenarios not in the current spec: "The party skill tab states its counts honestly", "The party skill tab states its skill counts and graphical actions". Copy the omitted scenarios into the MODIFIED block (a MODIFIED requirement replaces the whole block, so archive refuses to drop them).
```

The installed `dist/core/validation/validator.js` `findScenarioLossIssues` compares scenario names through `diffScenarioNames` and exposes no scenario-rename operation; `RENAMED` applies only to requirement names. The delta with its original headings passes strict validation.

### Purpose procedure and sync boundary

`openspec instructions specs --change party-cutover-spec-maintenance --json` resolves `planningHome.root` to the checkout running the command (this worktree during apply, primary for the maintenance owner's run) and states that changing an existing capability's Purpose means editing `<planningHome.root>/openspec/specs/<capability-path>/spec.md` directly; a delta must not carry `## Purpose` for an existing capability. The installed sync and archive implementation (`dist/core/specs-apply.js` and the sync-specs template) preserves an established main Purpose untouched and warns that a delta Purpose is ignored. No apply-worker main-spec edit has occurred: `git diff --stat master...HEAD -- openspec/specs` is empty on the feature branch.

### Traceability prediction

Observed pre-sync baseline in this worktree: `uv run --locked python -m tools.spec_traceability check` reports `2349 requirements, 10156 associations, 2349 covered, 0 uncovered, 0 errors`. [INFERENCE] If no concurrent change adds, removes or renames a requirement or invalidates an association before synchronization, the merged active specs produce the same totals, because this change carries only two existing complete parent requirements and changes one WHEN phrase. This is a conditional prediction, not a post-sync observation; the maintenance and archive owner records the actual post-sync and post-maintenance results.

### Staged merged residue prediction

- After ordinary requirement synchronization only: three of the four old phrases remain (the casting Purpose and the two HUD headings); the dispatch WHEN phrase is absent because the complete MODIFIED block applies it.
- After the coordinated primary wording-only maintenance commit: all four old phrases are absent from active specs. The retained stable capability IDs are `webclient-contextual-hud`, `webclient-action-dispatch` and `webclient-skillbook-casting`; the intentional `SkillBook` deletion assertion in `webclient-component-showcase` stays. Archived evidence is not modified.

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

## Maintenance handoff

### Ownership and order

1. The archive owner first performs ordinary requirement synchronization for this change. Synchronization preserves the established Purpose and the current HUD headings; it applies only the dispatch WHEN phrase.
2. The explicit spec-maintenance owner then makes one wording-only commit on primary, before archiving, while the delta is still active. Do not amend archived copies afterward.
3. An archive owner may perform both roles explicitly, but may not describe requirement synchronization as having changed the Purpose or renamed scenarios.

### Exact replacements: 3 logical replacements, 5 changed lines across 3 files

Purpose target: `openspec/specs/webclient-skillbook-casting/spec.md`, the single line under `## Purpose`.

Before:

> Provide authoritative graphical skill use from SkillBook through the existing field settlement and combat-initiation rules, with accessible target selection, truthful availability and a verified redesigned browsing surface.

After:

> Provide authoritative graphical skill use from the party window's skill tab through the existing field settlement and combat-initiation rules, with accessible target selection, truthful availability and a verified redesigned browsing surface.

HUD heading replacement 1: `#### Scenario: The skill-book drawer states its counts honestly` becomes `#### Scenario: The party skill tab states its counts honestly` in both:

- `openspec/specs/webclient-contextual-hud/spec.md` (current main line 1232 before synchronization)
- `openspec/changes/party-cutover-spec-maintenance/specs/webclient-contextual-hud/spec.md`

HUD heading replacement 2: `#### Scenario: The skill-book drawer states its skill counts and cast syntax` becomes `#### Scenario: The party skill tab states its skill counts and graphical actions` in both files above.

Do not touch the dispatch WHEN phrase in this maintenance commit: ordinary synchronization already applied it. Do not change any requirement body, requirement heading or ID, other Purpose, enumerated action ID, validator or adapter.

### Changed-line audit

The maintenance commit diff must contain exactly five changed line occurrences: one Purpose line in `webclient-skillbook-casting`, and the two heading lines mirrored in the main HUD spec and this change's HUD delta. No requirement or scenario body may be added or removed. Confirm with `git show --stat` plus a word-level audit such as `git diff --word-diff=porcelain`. Record the maintenance commit SHA and the changed-line audit in this change's workflow evidence before archiving.

### Validation and post-sync checks

Before declaring the fix landed, the maintenance owner runs and records:

1. `openspec validate party-cutover-spec-maintenance --strict`
2. `openspec validate webclient-contextual-hud --strict` and `openspec validate webclient-skillbook-casting --strict`, or `openspec validate --all --strict`
3. The four-phrase active-spec sweep above, with zero occurrences
4. `uv run --locked python -m tools.contract_gate`, recording the actual result
5. `uv run --locked python -m tools.spec_traceability check`, recording the actual result
6. Confirmation that canonical requirement IDs and the 67-ID action allowlist are unchanged, the `webclient-component-showcase` deletion assertion remains, and no archived evidence or `party-management-acceptance` artifact changed

The pre-sync unknown-requirement-ID exit from the still-open acceptance delta remains expected and receives no suppression or checker change.

### Maintenance commit record (archive owner)

Ordinary requirement synchronization ran in the feature worktree first (commit `8fc97a89`): only the `Action registries are allowlisted and duplicate-safe` WHEN phrase changed, because the HUD delta matched its main requirement line for line, so synchronization touched no HUD block.

The wording-only spec-maintenance commit then landed on primary:

- Commit: `54b612e1aab3b26cd562a356b0a385f6d7cac646`
- Files: 3; insertions 5 / deletions 5, confirmed with `git diff --numstat` and `git diff --word-diff=porcelain`:
  - `openspec/specs/webclient-skillbook-casting/spec.md` 1/1 - the Purpose line changes `SkillBook` to `the party window's skill tab`.
  - `openspec/specs/webclient-contextual-hud/spec.md` 2/2 - the two `skill-book drawer` scenario headings become the `party skill tab` headings, and `cast syntax` becomes `graphical actions`.
  - `openspec/changes/party-cutover-spec-maintenance/specs/webclient-contextual-hud/spec.md` 2/2 - the same two heading replacements mirrored in this change's delta.
- No requirement name, requirement ID, scenario body, enumerated action ID, validator, adapter or other Purpose line changed.

Observed results after that commit and the feature rebase:

- Four-phrase sweep over `openspec/specs` and this change's delta: 0 occurrences.
- `openspec validate --all --strict`: 358 passed, 0 failed (primary and feature worktree).
- `openspec validate party-cutover-spec-maintenance --type change --strict`: valid.
- Requirement names are byte-identical to the pre-change base: `webclient-contextual-hud` 67, `webclient-action-dispatch` 13, `webclient-skillbook-casting` 10; only the two HUD scenario headings differ.
- The action allowlist still holds 67 unique backticked IDs, `account.character.create` through `party.view_member`, identical to the base.
- `webclient-component-showcase` retains its `SkillBook` deletion assertion.
- `uv run --locked python -m tools.contract_gate` passed: traceability, observability (0 violations), test-data (0 violations), manifests and 18 contract tests.
- `uv run --locked python -m tools.spec_traceability check`: 2349 requirements, 10156 associations, 2349 covered, 0 uncovered, 0 errors.
- No archived evidence and no `party-management-acceptance` artifact changed.
