# affinity-friendly-fire — Design

## Context

`world/rules/affinity.py::apply_affinity_change()` is the sole affinity writer. It already accepts
negative deltas (uncapped downward, floor 0, never resetting the daily budget) and always runs the
party auto-leave recheck after a negative delta — a hook that currently has no real caller. The
combat session (`world/rules/combat_session.py`) resolves each player-selected action into one
complete round; companions fight as allies on the player's side (`party-combat`), and targeting
allows ally-side targets (`TargetSpec` AREA/all-target shorthand), so a player action can damage a
companion NPC. `engage()` rejects non-hostile targets
(`SessionReason.NOT_HOSTILE`), so friendly fire is the only real player-to-NPC damage path.

Constraints:

- Single-writer boundary: every affinity write goes through `world/rules/affinity.py`.
- `world/ai/` never writes; the scan and penalty are fully deterministic.
- The adult invariant and nonlethal companion knockout rules must not change.
- No migration or backward compatibility (unreleased project).

## Goals / Non-Goals

**Goals:**

- Give the auto-leave recheck its first real decrease caller: friendly fire.
- -1 per hit, per rulebook, no per-battle cap; negative-delta semantics unchanged.
- Scope the scan to player actions only; non-companion targets write nothing.

**Non-Goals:**

- Other decrease sources (theft, refusal, quest failure) — future seams.
- Direct NPC attack (engage keeps rejecting non-hostile targets).
- Cap breaks or any cap change (owned by `affinity-cap-break`).
- Any UI or command surface change.

## Decisions

### D1: The penalty is a new closed-set source, not a new writer

`friendly_fire` joins the `AffinitySource` closed set; the penalty is one
`apply_affinity_change(npc, player, FRIENDLY_FIRE, -1)` call per qualifying hit. The writer's
existing negative-delta behavior — no budget interaction, auto-leave recheck in the same
transaction — is reused verbatim.

- Alternatives considered: a bespoke `apply_friendly_fire_penalty()` wrapper. Rejected: it would
  duplicate the writer's transaction logic and create a second affinity-write path.

### D2: The scan runs after each resolved player action round, atomically

After the player action round resolves, the session inspects the round's damage events produced by
that player action against ally-side participants. A hit qualifies when the target is a companion
NPC (`player.db.party` member present on the battlefield). Companion-vs-companion damage, enemy
behavior, and buff-tick damage never qualify because they are not player actions.

- The once-per-hit semantics mean a single AREA spell hitting two companions applies two -1
  penalties, and a self-selected single-target misfire still applies -1 (the criterion is "player
  action → NPC damage", not intent).
- **Atomicity**: the scan, every penalty write, and any resulting auto-leave run inside the
  player action round's transaction boundary; a failure rolls the whole round's affinity effects
  back, and the auto-leave notification is delivered after commit (never mid-transaction).
- **Membership snapshot**: qualifying membership is snapshotted when the scan starts, so a
  companion that leaves because of an earlier hit in the same round still qualifies for every hit
  that round; each round re-snapshots.
- Alternatives considered: per-battle once-only penalty (rejected by owner decision, -1 per hit)
  and live membership checks per event (rejected — makes the penalty count depend on iteration
  order).

### D3: Non-companion targets write nothing

The scan checks membership in `player.db.party` before calling the writer; a non-member NPC gets no
call, so no negative record is created and `has_record` stays false.

### D4: The penalty value lives in the rulebook

`rulebook/affinity.yaml` gains `friendly_fire_penalty_per_hit: 1`, validated by
`affinity_config.py` (positive integer, bounded) like the other affinity balance values.

## Risks / Trade-offs

- [A single AREA spell can drain affinity fast] → Owner decision; the value is rulebook-tunable.
- [The scan could miss damage paths if the session's event shapes change] → The scan keys off the
  round's damage events; the OpenSpec tests pin the event shapes for player-action damage.
- [Auto-leave during combat settlement could surprise] → It runs inside the writer's existing
  transaction with the established notification contract; tests cover the drop-below-threshold
  path.

## Migration Plan

No data migration. The YAML gains one key; existing records are unaffected (negative deltas never
created records).

## Open Questions

- None blocking. Whether a per-battle penalty cap is ever wanted is a future balance decision; the
  rulebook value is the seam.
