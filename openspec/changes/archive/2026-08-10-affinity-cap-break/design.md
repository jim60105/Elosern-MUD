# affinity-cap-break — Design

## Context

Affinity records hold `value` (initial 0) and `cap` (initial 99); the ladder defines seven stages
with the topmost stage 絕對羈絆 at floor 100. The ladder already renders values at or above 100
correctly ("A future value above the natural cap still renders the topmost stage" is a tested
scenario), but with `cap = 99` no record can ever reach three digits. The affinity-party design A3
reserves cap breaks for "special future events"; this change delivers the first one: a milestone
quest declared in the rulebook.

Constraints:

- Single-writer boundary: `world/rules/affinity.py` owns all affinity state.
- `world/quests/` calls, never writes (A14).
- `cap` is never player-visible; stage-only presentation is unchanged.
- No migration or backward compatibility (unreleased project).

## Goals / Non-Goals

**Goals:**

- A rulebook `cap_breaks` table keyed by quest, matched against then-in-party companions.
- `raise_affinity_cap()` as the sole cap writer: monotonic, idempotent.
- Cap raise commits inside the existing atomic turn-in transaction.

**Non-Goals:**

- Player-visible cap or break notifications (the UI never exposes the field).
- New NPC personal-quest surfaces (the table is pure data).
- Cap lowering or per-record authored caps (the record keeps its single `cap` field).
- Decrease events (owned by `affinity-friendly-fire`).

## Decisions

### D1: The cap writer is a separate sole writer, not part of apply_affinity_change

`raise_affinity_cap(npc, player, new_cap) -> bool` is the only function that mutates a record's
`cap`. It creates a fresh record (value 0, cap 99) when none exists — `join_party` does not create
affinity records, so a bound companion can be recordless, and a silent no-op would lose the
milestone — raises only when `new_cap > current cap` (monotonic), and returns whether the cap
changed. It runs no daily-budget logic and no auto-leave hook.

- Alternatives considered: folding cap breaks into `apply_affinity_change` as a special source.
  Rejected: a cap raise is not a value delta; the daily budget, source semantics, and auto-leave
  hook must not run for it. Also considered: keeping no-record as a no-op. Rejected after
  rubber-duck review: a recordless bound companion would silently never receive the milestone.

### D2: The turn-in hook matches by quest key and companion identity, raising before gains

The guild-quest turn-in path, inside the same atomic transaction as the reward and the +2
`quest_completion` gain, looks up `cap_breaks` by the completed `quest_key`. For every then-in-party
companion matching the entry's `npc_key` (or declared role), it calls `raise_affinity_cap` with the
entry's `new_cap` — and it does so **before** the `quest_completion` gains, so a record sitting at
the old cap cannot clamp the +2 (a record at value 99 / cap 99 ends at value 101 / cap 150, not 99 /
150). Entries matching nothing are no-ops; re-completing the quest is idempotent because the cap
only grows.

- Selector semantics: two entries may not share the same `quest_key`, selector kind, and selector
  value (rejected at load); an `npc_key` and a `role` selector are distinct, so one quest may carry
  both shapes. A companion matching several entries of one quest resolves to the highest
  `new_cap`, so results never depend on YAML order. An NPC matches a `role` selector when its
  stored schedule is a template reference whose template key equals the selector (the schedule
  rulebook's "role templates", e.g. `guard`, `storekeeper`, `resident`); an NPC without a
  template-reference schedule never matches a role selector.
- Referential validation: `quest_key` must resolve in the quest definition registry.
- Alternatives considered: triggering on an affinity threshold reached. Rejected by owner decision
  (dedicated milestone, not a numeric trigger).

### D3: The table is validated like every rulebook value

`world/rules/affinity_config.py` validates `cap_breaks`: each entry has a non-empty `quest_key`
that resolves in the quest definition registry, exactly one of `npc_key`/`role` (decided by key
presence, so a mistyped selector never silently falls back to the other one), an integer `new_cap`
strictly above the natural cap 99, and no duplicate (`quest_key`, selector kind, selector) triples;
loading fails closed on deviation.

## Risks / Trade-offs

- [Role-based matching is coarser than per-NPC keys] → Both shapes are supported; role entries are
  the fallback for generated occupants, keyed entries for named NPCs.
- [A cap break could be perceived as an arbitrary event] → The milestone is explicit quest-bound
  data; authors control which quests break which caps.
- [Values beyond 99 accumulate without a visible target] → Stage-only presentation already covers
  the topmost stage; a future cap-related feature would surface its own contract.

## Migration Plan

No data migration. Existing records keep `cap = 99` until a matching milestone fires.

## Open Questions

- None blocking. Whether `apparent_age`-style divergence ever applies to caps (per-role cap
  variants) is deferred; the table schema is the seam.
