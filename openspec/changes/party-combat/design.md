# party-combat Design

## Context

`party-core` binds companions; `party-follow` keeps them co-located. The combat machinery is
already multi-member shaped: `CombatSessionRecord.player_ids` is a tuple, `reconstruct_battlefield`
builds a two-team `Battlefield` ("party" vs "foes"), `BattlefieldActionContext.relation_to` is
team-derived, the session's non-player action provider routes every non-player through
`monster_behaviour_policy` (team-relative `_living_enemies`), the record already carries
`knocked_out_ids`, and `_team_living` already excludes knocked-out/fled members. The gaps: `engage`
records only the player; the nonlethal policy is session-wide; knockout is only consulted by
`_team_living` — not by initiative, action provision, or target selection — and `_terminal_outcome`
tests the whole party team rather than the player, so a defeated player with living companions
deadlocks the session.

**Preconditions (must be landed first)**: `party-core` (membership binding + safe read API) and
`party-follow` (co-location). This change calls `world/rules/party.py`'s APIs and must not
reimplement membership.

## Goals / Non-Goals

**Goals**

- Companions join `engage` (co-located, living, not knocked out).
- Companion turns via the non-player policy provider; no flee (NPC fallback policy).
- Knockout as persistent battlefield state (marked at commit, persisted, reconstructed, excluded
  from action/targeting/terminal/overwhelm), cleared only by regen above 1 HP.
- Player-centric terminal rules (player defeat ends the session; victory = foes gone).
- Skip-safety cleanup that resolves every persisted participant, even when reconstruction fails.

**Non-Goals**

- Companion perma-loss/death, companion AI dialogue, companion gear/skill UI, quest assistance
  (`party-quest`), changes to settlement/flee/forfeit accounting beyond participant cleanup.

## Decisions

### D-1: Companions are allied-team participants, not a third team

`engage` extends `player_ids` with co-located living non-knocked-out bound companions. The
two-team model then supplies ALLY relations, the `all-allies` shorthand, and team-relative policy
targeting. The player's ENEMY-targeting skills cannot select companions (faction constraint);
opposing-team combatants can target companions — the spec says so explicitly.

### D-2: Knockout is battlefield state, not an HP side effect

`Battlefield` gains `knocked_out: set[str]` beside `fled`:
- Reconstructed from `record.knocked_out_ids` in `reconstruct_battlefield`; persisted at round end
  from the (already existing) `_knocked_out_ids` backfill plus in-round markings.
- Marked at damage-commit time: the per-entity nonlethal floor in `combat.py` adds the target key
  to `battlefield.knocked_out` within the same commit (covered by the extended
  `battlefield-commit-surface` duck-typed snapshot: `fled` AND `knocked_out`).
- Consumed by initiative order, the action providers, `_living_enemies`, the `all-allies`/AREA
  shortcuts, overwhelm classification, and `_team_living` — one shared predicate,
  `is_knocked_out(key)`.
- Cleared only when the companion's HP rises above 1 through clock-driven regen; until then a new
  `engage` excludes the companion (checked in `engage`'s companion collection).

### D-3: Per-entity nonlethal via `nonlethal_keys` in the event context

The session-wide `nonlethal` flag (exam semantics) is untouched. The context gains
`nonlethal_keys: frozenset[str]`; hostile sessions set it to the companion keys. `action.py`'s
knockout emission and `combat.py`'s HP-crossing floor read "target key in `nonlethal_keys` OR
session flag" per damaged target, before event-effect planners. Companions floor at 1 and emit
`target_knocked_out`; monsters stay lethal; exams keep exact existing behavior.

### D-4: Terminal rules are player-centric

`_terminal_outcome` checks the session owner first: the player fled → "fled"; the player is
knocked out or at zero HP → defeat (hostile) / exam failure; only then does the foes team decide
victory. This removes the deadlock where a defeated player with living companions could neither
settle nor act. Companion knockout is a battlefield state, never a terminal condition.

### D-5: Cleanup resolves every persisted participant

`clear_session`/`forfeit`/recovery paths pass the persisted record so every participant dbref is
resolved and unregistered from skip safety even when `reconstruct_battlefield` failed (a missing
participant must not leave other companions registered `IN_COMBAT`).

## Risks / Trade-offs

- [Knocked-out companions could still be targeted if a code path uses raw HP>0] → the shared
  `is_knocked_out` predicate is the single consumer point; every alive-check site listed in D-2 is
  converted and pinned by tests.
- [Per-entity nonlethal drifts from the exam flag] → one decision point reads both sources; exam
  scenarios stay pinned by existing tests.
- [The player-dead, companions-alive deadlock regresses] → a round-to-settlement integration test
  covers it end to end.
- [Skip-safety leaks after a failed reconstruction] → D-5 cleanup; a missing-companion cleanup
  test covers it.
- [Companion fallback policy could flee if NPCs later gain threat tiers] → a test pins the current
  no-flee fallback behavior.

## Migration Plan

Precondition: `party-core` and `party-follow` must be implemented, verified, and archived first —
this change's tasks reference their APIs and must not proceed otherwise. No released users; no
data migration. Rollback is a revert.

## Open Questions

- None blocking. Whether a knocked-out companion should be revived by healing skills is deferred
  (the recovery rule is regen-only for now).
