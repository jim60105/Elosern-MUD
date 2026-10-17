# Proposal

## Why

A verified real-session possession cycle leaves a party companion at `location = None` after 歸位, while its party membership survives. The same defect affects `release_for_party_change`, making the companion unavailable to possession, following, and combat collection until an operator repairs its location.

## What Changes

- Preserve the companion's pre-release room through the deterministic possession writer for both `handback` and `party_change`. For a co-located pair, release leaves both figures in their shared room and preserves membership at the release boundary.
- Remove the companion's stale logout-location residual after the unpuppet hook, while preserving the verified session handback, lock/cmdset cleanup, rollback, and client epoch ordering.
- Add real-session regressions to the existing registered `world/rules/tests/test_possession_transition.py`, including subsequent possession, following, combat co-location, and failure compensation.
- Explicitly exclude disconnect/link-dead location recovery. Evennia unpuppets before the account disconnect hook, and its maintenance cleanup can invoke the stash hook independently. The named follow-up `fix-disconnected-possession-room-lifecycle` must address those earlier lifecycle points; this proposal makes no safety claim for them and does not create that second change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `companion-possession-transition`: add an observable room-preservation requirement for normal possession release and its failure compensation.

## Impact

Implementation is confined to `world/rules/possession.py`, the existing transition integration test module, and a small observability catalog update. No dependency, command syntax, OOB schema, player-body rendering, or AI-writer change is intended. The release uses the existing `possession_release` info boundary event, augmented with the companion's room identifier.

This is one engineer-day of work. It introduces no migration, compatibility layer, global NPC hook, or automatic repair of already-stranded production objects.

`companion-possession-core` already requires membership removal after successful handback. "Membership survives release" applies to `release_possession` / `release_for_party_change` themselves, before an owning dismissal, auto-leave, or escort terminal operation removes its membership source. Those terminal operations retain their existing policies. Possessed movement can separate the two bodies, so room preservation retains the companion's actual pre-release room and adds no reunion teleport. The co-location acceptance scenarios start with both bodies together.

There were no active changes in `openspec list --json` at proposal creation. The current transition spec's prohibition on a new player unpuppet cleanup branch coexists with the already-landed D4 location guard. This change leaves that guard and the disconnect-only cleanup wiring unchanged. No amendment to the core or webclient presentation contracts is required.
