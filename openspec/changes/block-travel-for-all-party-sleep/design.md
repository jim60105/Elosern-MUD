# Design

## Context

`travel_cost.refuse_sleeping_party` checks only `FORCED`; actual traversal therefore differs from the pure sleep-aware travel policy. `plan_traversal` reads full initial states then retains reserves only, and `_predicted_state` reconstructs `AWAKE`. Source-present preflight already exists in `resolve_traversal_cost` and the movement charge seam; exit types and wilderness gates invoke movement preflight, with skill-based flight/flash-step waivers. The supplied isolated smoke establishes the actual-boundary bug and must not be rerun merely to reconfirm it.

The engine design requires preflight before effect/time writes and atomic movement settlement. The approved fatigue/sleep design §9.4 and main party requirement are currently forced-only; the user explicitly approves broadening them.

## Goals / Non-Goals

**Goals:** make every real travel boundary stationary for any source-present sleeper; retain one exact source roster and truthful prediction without changing all-awake costs.

**Non-Goals:** sleep receipt lifecycle, carrying, split party, remote recovery, map glyph changes, random encounters, alternate travel system or additional flight restrictions unrelated to sleep.

## Decisions

### Broaden the existing gate and migrate every consumer

Keep one authoritative `refuse_sleeping_party` policy using validated actual posture or the existing both-sleep action predicate. Both voluntary and forced sleep refuse with existing `party_sleeping` reason. Do not add independent browser or exit-specific sleep policy. Validate the complete ordered source-present effective travelling set used by follow/charge, including owner when a companion is possessed, before relocation or destination creation.

Run this barrier before distance classification, authored connector pricing, skill waiver and resource/clock/knowledge/arrival writes. Retain a final authoritative check where existing movement transactions revalidate source state. Ordinary/interior exits cannot bypass through NON_DISTANCE; flight cannot bypass through WAIVED. Invalid physiology continues to fail closed rather than being treated awake.

### Consumer boundary matrix

| Consumer | Required barrier position | Acceptance observation |
| --- | --- | --- |
| Ordinary and interior `MovementCostMixin`/`Exit` | Before traverse callback, waived or non-distance return | No actor/follower move or resource/tick change |
| Settlement/grid distance edge | Before route integration and source-follow writes | Same source roster, no map knowledge or arrival hooks |
| Wilderness directional step | Before virtual destination allocation/relocation | No new destination-side effects or discovery |
| Grid-to-wilderness gate | Before `enter_wilderness` and landing-cell creation | Owner and companions remain source-present |
| Wilderness-to-grid gate | Before return relocation and gate reanchor | No home/arrival/knowledge mutation |
| Direct cost/charge/prediction seams | Before successful pricing or mental settlement | Full-reserve voluntary sleep still refuses |
| Flight/flash-step waiver | Before waived outcome | Sleeping-party reason is preserved |

Inspect the exact existing call sites through codegraph during apply, then change the owning preflight seam rather than patching only one route. This is integration work over identified consumers, not an open-ended rediscovery task.

### Prediction keeps posture

Carry immutable initial fatigue states through travel prediction rather than reconstructing posture from reserve alone. Reject any sleeping initial state before distance integration; a reserve of 360000 is no proof of wake. Existing awake threshold calculations, exact-zero arrival allowance, single upward duration rounding and terrain geometry remain unchanged. No travel interval can settle sleeping activity because admission already excludes it.

### Presence and local action boundaries

Use canonical effective membership with source co-location; stale/deleted/corrupt entries grant no membership and remote members are not teleported or globally simulated. Awake members may inspect, organize items, fight or perform other lawful local actions. The gate never relaxes actor action-capability checks for a sleeper. Do not alter ordinary possession release or combat rules.

## Approved Design Amendment

During apply, replace forced-only stationary wording in `docs/superpowers/specs/2026-10-21-party-fatigue-and-sleep-design.md` §9.4 and acceptance §14 item 7 with any present effective voluntary or forced sleeper. State that this user-approved amendment supersedes the forced-only wording; retain §11's no-sleeping-follower integration invariant. Update the stale header/§16 status consistently with the receipt change if already applied. Rename and amend the original `party-system` requirement through this delta, updating its traceability ID and retiring the old forced-only mapping. Do not leave a second contradictory normative requirement. No direct main-spec/design edits are included in this planning commit.

## Risks / Trade-offs

- A gate checked only at charge time can follow relocation -> assert actual preflight order, including fault snapshots and destination knowledge.
- A flight waiver may return early -> test waived owner and possessed traverser, including interior/gate consumers.
- Shared design/manifests conflict with other changes -> integrate serially and preserve unrelated map work.

## Deployment and Rollback

Apply with **gpt-luna**, branch `feat/block-travel-for-all-party-sleep`, worktree `.worktrees/block-travel-for-all-party-sleep`. No runtime dependency on receipt implementation, but serialize shared docs/manifests. No migration or save edit. Keep all runtime consumers and the broadened contract in the same implementation cutover; rollback coherently rather than adding a forced-only compatibility path.
