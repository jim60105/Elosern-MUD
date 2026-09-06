# Proposal: DA5 — defeat-aftermath-companion-victims

Change ID: **DA5** (parent design §8 archive order).

## Why

The owner's design pool is "player + knocked-out companions" — a party
wiped by a pack of aroused goblins should not have its NPC companions
miraculously spared while the player alone pays. The violation change ships
the mechanics against the player pool alone (its own scoping requirement
names this extension); this change widens the pool without touching the
sequence engine's rails.

## What Changes

- **Pool extension**: violation target selection draws from non-fled allied
  participants (player + companions in the knocked-out set), every attempt
  deterministically targeted per the state-derived dice helper — the
  companion's own `SexualState`, counters, and EventLog entries, never
  proxied through the player.
- **Symmetric crediting on the defeat path**: companion victims credit the
  shared `participant` counters per the
  `sexual-counter-symmetric-crediting` convention, so the violator's
  counters see companion victims exactly as the player's do (species-gate
  semantics from that change apply unchanged).
- **Companion wake observations**: a knocked-out companion "wakes" with its
  own digest line at settlement (the digest change consumes the widened
  `ViolationOutcome` pool); no new companion state kinds.
- **Pool edge cases**: companions that fled are excluded; a party where the
  only allied participant is the player behaves exactly as the violation
  change's pinned player-only pool; a party with all allies fled/knocked-out
  yet winners alive settles without error.
- **BREAKING** (unreleased): the violation change's player-only targeting
  requirement is MODIFIED to the full-pool requirement.

## Capabilities

### New Capabilities

_None — this change modifies the young capability its parent change
introduced._

### Modified Capabilities

- `defeat-aftermath-violation-sequence`: "Violation attempts select victims
  from the target pool" is modified to the full-pool requirement (non-fled
  allied participants, deterministic selection, per-victim own-state
  writes), and one ADDED requirement gives each companion victim its own
  per-participant digest observation + wake line.

## Impact

- `world/rules/defeat_aftermath.py` (pool selection + per-victim writes
  beside the sequence loop), `world/rules/player_messages.py` (companion
  wake template lines), `.github/evennia-shards.json` unchanged (tests land
  in the existing new modules).
- Tests: extends `test_defeat_aftermath_violation.py` with pool cases; the
  violation change's player-only scenario is rewritten, not deleted
  (solo-party equivalence stays pinned).
- **Depends on**: `defeat-aftermath-violation-sequence` (mechanics) and
  `sexual-counter-symmetric-crediting` (crediting semantics). **Blocks**:
  `defeat-aftermath-digest-narrative` (its digest consumes per-companion
  outcomes).
