# Causal publication settlement groups

## Why

Independent text and graphical Deferreds can overlap on one session, and one committed domain operation can notify several watcher sessions. Publication grouping must preserve those command semantics and prevent an ordinary push from escaping before its checkpoint fact.

## What Changes

- Add bounded ephemeral causal commit groups, captured across synchronous deterministic owners and their on-commit callbacks, with per-watcher final publication.
- Preserve independent overlapping command execution; never hold a session-wide publication token across a pending domain Deferred.
- Integrate B's exact always-Deferred queue contract with group promotion, action-result completion and explicit sync ordering.

## Capabilities

### New Capabilities

- `webclient-publication-settlements`: Causal grouping and safe publication under overlapping ingress and multiwatcher commit callbacks.

### Modified Capabilities

- None. B owns the existing completion/text requirement amendments.

## Impact

One engineer-day for grouping and caller integration, separated from movement identity/hooks in M. Tests and docs accompany this slice. No command rejection/queue, persistent group state, general game event bus, compatibility path or performance verification. All files and exact callback registrations are specified in design.md.

## Batch:

depends-on: webclient-publication-baseline

Code conflicts: coordinator/dispatcher/ingress, shared push helpers, NPC lifecycle and callback registration sites serialize with movement/settlement and active authored-dialogue-refresh-lifecycle, availability, reading-server and unread-notices. Preserve their domain authority and capture the same publication group at their existing on-commit registrations. No semantic dependency on those unimplemented active changes. Read the shared matrix in ../webclient-delta-contract/design.md. This corrective split resolves the final independent review's overlapping-ingress and out-of-token publication findings; planning only.
