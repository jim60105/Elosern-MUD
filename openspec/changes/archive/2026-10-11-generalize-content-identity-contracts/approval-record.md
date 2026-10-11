# WP1 approval record and apply-time monster-spec confirmation (task 1.1)

Baseline `master` = the worktree tip at WP1 start: `fbfd20ab8755a44cf4fc3d12362a70d345d912f0`.
The planning baseline for the main specs is the balance cutover `afa974d4` (`scope-inventory.md`).
Everything below is an observation made at this apply time in the worktree
`.worktrees/generalize-content-identity-contracts`, not a plan.

## Approval record

The user granted D1-D3 as final decisions. Their wording is recorded verbatim; the disposition column
records what the approval concedes, taken from `review-disposition.md` and `pending-couplings.md`.

| Id | User decision (verbatim) | What it approves | What it does **not** approve |
| --- | --- | --- | --- |
| D1 | 「採用提案的處置，三個提案延後重寫」 | Accepting the `pending-couplings.md` disposition: this change removes four requirement names that each deferred monster proposal modifies, so those owners must rewrite their deltas later against the then-current specs. Their 12 broken MODIFIED targets and 18 old-shaped ADDED blocks are recorded obligations of this approval. | No edit, repair, rebase or alias for `ridge-burrow-hare-resource-skill`, `rock-echo-goat-resource-skill` or `fog-mane-lynx-resource-skill`; no compatibility heading retained to keep their stale deltas applicable; no approval to implement them. |
| D2 | 「採用新的完整性檢查」 | Accepting the replacement completeness checks: live-source-derived bidirectional inventory equality plus per-host profile/card/age/voice/table coverage, with a dated editorial ledger in place of expected prose. Removing the six inventory-slice requirements without these replacements is not this design. | No expected-prose fixture, no text pin, no editorial-quality automation claim; the ledger proves coverage of actual sources, not prose quality. |
| D3 | 「採用：退役並同步重掛」 | Accepting atomic retirement-and-re-annotation: removed requirement ids retire their canonical ids and every affected annotation is re-attached inside this same implementation, with zero stale ids. | No mechanical global decorator substitution, no allowlist, no waiver, no stale id kept alive to make a suite pass; each replacement id earns a direct assertion of the specific general invariant. |

Recorded obligations (tracked here, **not** work of this change): the three deferred proposals each
carry four MODIFIED targets whose names this change removes, plus six ADDED blocks shaped around a
species prefix. Their owners re-evaluate all blocks they touch at apply time and copy the complete
then-current replacement blocks; this change performs none of that.

## Apply-time confirmation: no deferred proposal has changed the monster specs

| Check | Command | Observed result |
| --- | --- | --- |
| Main specs untouched since the planning baseline | `git log --oneline afa974d4..HEAD -- openspec/specs` | **empty** |
| Deferred change directories untouched since the planning baseline | `git log --oneline afa974d4..HEAD -- openspec/changes/ridge-burrow-hare-resource-skill openspec/changes/rock-echo-goat-resource-skill openspec/changes/fog-mane-lynx-resource-skill` | **empty** |
| The four monster capabilities' specs unchanged | `git log --oneline afa974d4..HEAD -- openspec/specs/monster-species-registry/spec.md` (and `monster-resource-abilities`, `monster-action-policy`, `monster-individual-construction`) | **no commits** for each |
| The three deferred proposals are still unapplied | `os-phase <name>` for each | `phase=proposed primary=master branch=none worktree=none` for all three |
| Every deferred target still exists in the current specs | id lookup against `uv run --locked python -m tools.spec_traceability list` | all four names present in each case (**see below**) |
| Strict validation baseline | `openspec validate --all --strict` / `--specs --strict` | `315 passed, 3 failed (318 items)` / `311 passed, 0 failed`; the three failures are exactly the deferred proposals |
| No pending change was edited | `git status --porcelain` at the WP1 commits | only this change's own files staged/committed |

Conclusion: the apply-time current monster specs are **byte-identical** to the planning baseline, so the
deferred proposals have neither landed nor moved the target names. The 12/18 inventory below is exact
and current, and D1 remains the correct disposition.

## Exact target inventory

### Twelve broken MODIFIED targets (four per proposal, all present today)

Each of the three deferred proposals contains exactly these four MODIFIED requirement targets, and each
of the four is removed by this change (verified by id lookup, `present_now=true` for all twelve):

| Target requirement (capability :: canonical id) | Removed by this change | Replacement owner |
| --- | --- | --- |
| `monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values` | yes | Authored profile requirements are declared per variant |
| `monster-species-registry::special-abilities-are-narrative-boundaries-with-a-named-mechanics-prerequisite-never-fake-skills` | yes | Narrative and executable monster configurations remain separate |
| `monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals` | yes | Shipped profile completeness follows authored declarations |
| `monster-resource-abilities::crocodile-ecology-documents-implemented-limits` | yes | Bestiary documentation covers keyed public content relationships |

After this cutover these four names no longer exist, so the deferred MODIFIED blocks cannot resolve;
their numeric approval tables and named completed/deferred lists are additionally incompatible with the
new contracts. The exact per-proposal block details stay in `pending-couplings.md` (unchanged).

### Eighteen old-shaped ADDED blocks (six per proposal)

Verified by parsing each deferred proposal's delta specs. The species prefix differs per proposal and is
preserved as authored, because English slugs are not the Chinese display-name authority:

| Proposal | Species prefix | ADDED blocks | Shapes |
| --- | --- | --- | --- |
| `ridge-burrow-hare-resource-skill` | 築埂兔 | 6 | `contact kit uses existing first-owned policy and fallback`; `construction persists both approved contact kits`; `owns its approved contact resource ability`; `timed modifier follows its authored recipient and lifetime`; `payment and atomicity retain the shared transaction`; `public ecology reflects the completed contact kit` |
| `rock-echo-goat-resource-skill` | 岩響山羊 | 6 | same six shapes |
| `fog-mane-lynx-resource-skill` | 霧鬃山貓 | 6 | same six shapes |

These eighteen blocks would re-introduce identity-specific requirements; their owners recast them as
authored data plus generic-contract evidence when their changes resume. Recorded, not edited here.

## What WP1 did to the pending changes

Nothing. No file under `openspec/changes/ridge-burrow-hare-resource-skill`,
`openspec/changes/rock-echo-goat-resource-skill`, `openspec/changes/fog-mane-lynx-resource-skill` or any
`exploration-*` change is staged, edited or reverted by this package; the worktree is clean apart from
this change's own committed artifacts.

## Verification commands used for this record

```sh
git -C .worktrees/generalize-content-identity-contracts log --oneline afa974d4..HEAD -- openspec/specs
os-phase ridge-burrow-hare-resource-skill   # and rock-echo-goat-…, fog-mane-lynx-…
openspec validate --all --strict
uv run --locked python -m tools.spec_traceability list
```

The id-set and 12/18 counts were produced by a throwaway analysis of the change's own delta specs and
the deferred proposals' delta specs, read-only, against the ids returned by the project tool.
