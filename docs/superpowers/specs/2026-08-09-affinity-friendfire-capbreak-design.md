# Affinity Friendly Fire and Cap Break — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The first affinity-decrease event (friendly fire on companion NPCs) and the milestone
cap break that unlocks three-digit affinity values.

This document is a slice of `docs/superpowers/specs/2026-08-08-affinity-party-design.md` §8
("decrease events, cap breaks ... deliberately deferred seams, each with an explicit hook built
and tested now"). Where this document conflicts with the affinity-party design or the master
design, those documents win unless this document explicitly amends them.

---

## 1. Product Context

`world/rules/affinity.py` is the sole affinity writer. `apply_affinity_change()` already accepts
negative deltas (they never clamp upward and never reset the daily cap), and the auto-leave recheck
(A10) is built and unit-tested through a direct negative-delta call — but no real decrease event
calls it. The natural `cap = 99` keeps the topmost ladder stage (絕對羈絆, floor 100) unreachable;
A3 reserves it for "special future events" that raise a record's cap.

This change supplies the two deferred callers:

1. **Friendly fire**: a player combat action that damages an ally-side companion NPC reduces that
   NPC's affinity. `engage()` only accepts hostile `Monster` targets
   (`world/rules/combat_session.py`, `SessionReason.NOT_HOSTILE`), so direct NPC attack is
   impossible; friendly fire through AREA/all-target skills is the only real damage path.
2. **Milestone cap break**: completing a designated quest while the matching companion is in the
   party raises that record's cap to 150, making 100+ values reachable.

Both paths preserve the single-writer boundary: every affinity write goes through
`world/rules/affinity.py`; `world/quests/` only calls.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| F1 | **Friendly fire is the only decrease event in this change.** A player combat action (skill, AREA, or all-target shorthand) that damages an ally-side companion NPC reduces that NPC's affinity by 1 per hit. | Owner decision; direct NPC attack is impossible today, so friendly fire is the one real damage path. |
| F2 | **-1 per hit, no per-battle cap** (configurable in the rulebook); negative deltas never reset the daily cap and the auto-leave recheck runs as designed. | Owner decision; repeated hits drain affinity visibly, and the A10 hook finally has a live caller. |
| F3 | **Cap break is a dedicated milestone table.** `rulebook/affinity.yaml` gains `cap_breaks` entries `{npc_key \| role, quest_key, new_cap: 150}`; turn-in of the matching quest with a matching then-in-party companion raises the cap once, idempotently. | Owner decision; no new NPC personal-quest surface is needed — the table is pure data on top of the existing turn-in path. |
| F4 | **All writes stay in `world/rules/affinity.py`.** A new `friendly_fire` source flows through `apply_affinity_change()`; a new `raise_affinity_cap()` is the sole cap writer. `world/quests/` calls, never writes. | Preserves A2/A14 single-writer invariants. |
| F5 | **Friendly-fire detection is scoped to player actions.** Only damage caused by the player's own combat actions counts — not companion-vs-companion, not enemy behavior, not buff-tick damage. Knockout remains nonlethal and does not change the count. | The penalty is a consequence of the player's behavior, not battlefield noise. |

---

## 3. System Design

### 3.1 Friendly fire

`world/rules/combat_session.py` + `world/rules/affinity.py`:

- After each resolved player action round, scan the round's damage events for targets that are
  ally-side companion NPCs (`player.db.party` members present on the battlefield).
- For each damage event from a player action against such an NPC,
  `apply_affinity_change(npc, player, AffinitySource.FRIENDLY_FIRE, -1)`.
- The source fires even when the NPC was the player's explicitly selected target (self-selected
  misfire); the criterion is only "player action → NPC damage".
- After each negative delta the existing auto-leave recheck runs: a companion NPC dropping below
  70 (the 羈絆 floor) leaves the party with `reason="affinity_below_threshold"` and the player is
  notified.
- `rulebook/affinity.yaml` gains `friendly_fire_penalty_per_hit: 1`.

### 3.2 Cap break

`rulebook/affinity.yaml`:

```yaml
cap_breaks:
  - { npc_key: "ciaran_librarian", quest_key: "library_restoration", new_cap: 150 }
```

`world/rules/affinity.py` gains:

```python
def raise_affinity_cap(npc, player, new_cap: int) -> bool:
    """Raise a record's cap monotonically; no-op when new_cap <= current cap."""
```

- `world/quests/`'s turn-in path, in the same transaction as the +2 `quest_completion` gain, looks
  up `cap_breaks` for the completed `quest_key` and calls `raise_affinity_cap` for every
  then-in-party companion matching `npc_key` (or the declared role).
- Idempotent: re-completing the quest or re-raising does nothing (`cap` only grows).
- After the break, values above 99 are reachable and map to the topmost stage (絕對羈絆) exactly as
  the ladder already defines; no player-facing cap display is added.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/rules/affinity.py` | `friendly_fire` source; `raise_affinity_cap()`; auto-leave recheck unchanged |
| `world/rules/combat_session.py` | Player-action damage scan against ally-side companion NPCs |
| Quest turn-in (`world/quests/`) | Calls `raise_affinity_cap`; never writes affinity itself |
| `rulebook/affinity.yaml` | `friendly_fire_penalty_per_hit` + `cap_breaks` (validated through the rulebook mechanism) |
| `world/rules/party.py` | Auto-leave hook unchanged; gains its first real decrease caller |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| Friendly-fire target is not a companion NPC (not in `player.db.party`) | No record, no penalty — no negative record is created |
| `cap_breaks` matches no in-party NPC/role | Entry is a no-op; the turn-in otherwise proceeds unchanged |
| Transaction interruption | Snapshot/rollback, same guarantee as existing affinity/quest transactions |
| LLM / art services offline | Irrelevant — the change is fully deterministic |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Friendly fire | `EvenniaTest`: AREA skill hitting a companion → -1 per hit; single-target self-selected misfire → -1; companion-vs-companion, enemy behavior, and buff-tick damage never penalize; negative delta never resets the daily cap; dropping below 70 triggers auto-leave with reason + notification |
| Cap break | Matching quest + in-party companion → cap 150 and 100+ values reachable; idempotent repeat; non-matching NPC no-op; `cap` only grows |
| Rulebook | YAML validation; one test per rule ID (project convention) |
| Regression | Existing affinity/party/combat suites stay green |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `affinity-friendly-fire` | 8/9/16 (combat session), affinity-system, party-core/combat | Damage scan, `friendly_fire` source, -1 per hit, live auto-leave tests |
| 2 | `affinity-cap-break` | 1, quest turn-in (party-quest) | `cap_breaks` table, `raise_affinity_cap()`, turn-in hook, idempotency tests |

---

## 8. Out of Scope

- Other decrease sources (theft, repeated invitation refusal, quest failure) — documented future
  seams; the write API and auto-leave hook already serve them.
- Direct attack on NPCs (`engage` continues to reject non-hostile targets).
- Any player-visible cap field or break notification (the UI never exposes `cap`).
- An NPC personal-quest surface (`cap_breaks` covers the milestone need as data).

---

## 9. Open Questions Carried Forward

- None blocking. Whether further decrease sources should be gated (e.g., once-per-day negative
  deltas) is a future balance decision; the current design intentionally leaves negative deltas
  uncapped per the affinity-party design.
