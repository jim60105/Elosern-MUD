# party-quest Design

## Context

`party-core` binds companions and `party-combat` gives them battlefield presence with a persistent
knockout state. The quest planner's DEFEAT credit is currently owner-only ("Another character's
action grants no ordinary kill credit"), and reward settlement is a closed surface set (wallet,
inventory, merit, acquire, claims). This change opens both: bound-companion kills and co-presence
advance the owner's objectives, and turn-in pays the party through the `quest_completion` affinity
source that `affinity-system` already declared cap-exempt. Constraints: the quest planner commits
inside the action transaction; reward settlement is all-or-nothing with cache restoration; the
single-writer rule — quest code calls `world/rules/affinity.py`, never writes affinity itself;
companions never gain XP/items/merit.

## Goals / Non-Goals

**Goals**

- Companion DEFEAT credit for the quest owner, with the same cap/one-transition rules and
  commit-time placement; knocked-out companions excluded.
- Companion co-presence satisfies REACH/ESCORT arrival; ESCORT's protected-entity rule unchanged.
- +2 `quest_completion` affinity per then-in-party companion, atomically with the reward
  transaction and its cache restoration.

**Non-Goals**

- Companion quest logs, companion XP/items/merit, quest delegation/auto-accept, affinity decrease
  events, cap breaks, changes to the owner-only credit for unbound entities.

## Decisions

### D-1: Companion credit rides the existing commit-time planner

The DEFEAT planner already runs pre-commit (inside the action's pipeline, before the outer
`transaction.atomic()` of `_commit()`) with the request actor in hand. The companion rule is added
at the same decision point: when the request actor is a bound companion of a record owner —
validated bidirectionally through the party module's safe resolver (the actor appears in the
owner's valid party list AND the actor's back-reference points to the owner) — and the actor is
not knocked out per `party-combat`'s shared `Battlefield.is_knocked_out(str(actor.key))`
predicate over the request context's battlefield, the planner plans the owner's stage with
identical aggregation/cap/one-transition semantics. A credit decision without an active
battlefield or without a valid bidirectional binding fails closed (no credit). No new write path —
the same commit guarantees atomicity.

### D-2: Co-presence is a read at the arrival hook, re-run after follow

Arrival semantics are co-presence, not companion-alone: a REACH/ESCORT stage advances when the
player is the arriving object and at least one bound companion is present in the destination room.
Because `party-follow` moves companions in `at_post_traverse` — after the player's
`at_object_receive` observation — the follow flow SHALL re-run the quest arrival observation
(`world/quests/room_observation.py::observe_room_entry`) for the player once after the companions'
moves complete; the one-transition rule makes the repeated observation idempotent. No companion-
alone arrival entry point is added (the observer only accepts a `PlayerCharacter`). Wilderness
rooms are untouched (no arrival hook, per the existing requirement).

### D-3: The affinity bonus joins the reward transaction

Turn-in lives in `world/rules/guild.py::turn_in_quest()`. It precomputes the then-in-party
companion list through the safe party read from `world/rules/party.py` and calls
`apply_affinity_change(npc, player, "quest_completion", 2)` for each inside the existing reward
transaction. The reward snapshot/restore gains a per-NPC map: before any write, snapshot every
affected companion's `relations_data` attribute (and any relation-handler cache the affinity API
relies on); on failure, restore each NPC's attribute and rebuild/invalidate its relation cache so
the in-process affinity value never diverges from the rolled-back database. `quest_completion` is
cap-exempt, so the daily budget never blocks the bonus. Companions receive nothing else.

## Risks / Trade-offs

- [Companion kills inflate DEFEAT progress] → the credit is bounded by the objective quantity and
  the one-transition rule; the binding must be valid in both directions and the actor
  non-knocked-out at planning time, or the decision fails closed.
- [Knockout state drifts from the planner's view] → the planner reads `Battlefield.is_knocked_out`
  from the request context at planning time; a credit decision without a battlefield fails closed.
- [The reward transaction grows a surface] → a per-NPC `relations_data` snapshot map joins the
  existing snapshot/restore; the fault-injection scenarios cover every affinity write position.
- [Follow ordering hides first-arrival co-presence] → the post-follow re-observation (D-2) makes
  it visible; the one-transition rule keeps it idempotent.

## Migration Plan

Precondition: `party-core`, `party-follow`, and `party-combat` must be implemented and archived
first (this change reads their APIs). No released users; no data migration. Rollback is a revert.

## Open Questions

- None blocking. Whether a completed-but-never-turned-in quest should still pay the party is
  settled: the bonus applies at turn-in only, matching the reward surface.
