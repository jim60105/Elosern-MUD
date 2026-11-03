# Proposal

## Why

The interactive battlefield keys participants by display name and rejects repeated labels. Regional mixed groups require identity to remain stable throughout the existing resolver and session pipeline.

## What Changes

- **BREAKING** Replace combat name identity with persistent individual identity across every affected caller, pure fixture, event consumer and session reconstruction.
- Keep labels presentation-only and preserve duplicate-dbref rejection, targeting, effects, AI state, death credit and designated examination policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `battlefield-action-context`: Revise the behavior contract in this change's delta.
- `player-combat-session`: Revise the behavior contract in this change's delta.
- `disengage-action`: Revise the behavior contract in this change's delta.

## Impact

`Battlefield.__post_init__` equates roster keys with `entity.key`. `reconstruct_battlefield` rejects duplicate labels although records already persist integer dbrefs. `stable_actor_id` and monster-AI `stable_identity` already use dbrefs for real entities but fall back to names for synthetic ones. `RoundRecord.identities` already maps roster keys to dbrefs.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: none

Code conflicts:
- whole-cell-field-engagement: combat_session, combat_initiation and shared fixtures; land this first.
- regional-population-recovery: combat_session/rounds.py; recovery edits follow this identity cutover.
- Shared shard manifest changes must be serialized across the batch.
