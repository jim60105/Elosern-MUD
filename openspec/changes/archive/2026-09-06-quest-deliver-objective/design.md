## Context

Four objective kinds exist: `DEFEAT` (committed action events), `REACH` and `ESCORT` (room arrival),
`ACQUIRE` (committed positive inventory deltas). None expresses "hand this to that person".

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §5.

## Goals / Non-Goals

**Goals:**

- A delivery completes when the parcel reaches the right hands, not the right room.
- Progress is unforgeable and atomic with the item movement.
- The observer is structurally the twin of `acquire.py`, so a reader who knows one knows the other.

**Non-Goals:**

- No player-facing verb (owned by `quest-deliver-action`).
- No change to `ACQUIRE`'s "removal never reverses progress" rule.
- No content authoring a delivery quest yet.

## Decisions

### D1: A new objective kind, not a two-stage `ACQUIRE` → `REACH`

The two-stage encoding was considered and rejected. It cannot express "to that person" (only "to that
room"), and the parcel never leaves the player's inventory, so the fiction and the state diverge:
you arrive, the quest completes, and you are still carrying the thing you supposedly handed over.

### D2: The recipient is a bound identity, not a name or a content key

`objective_target_ids` already exists for exactly this — `DEFEAT` uses it for bound targets, and
`bind_stage_runtime` already preflights that bound entities are live `LivingEntity` instances. Using
it means a renamed recipient stays correct and two same-named characters can never be confused. A
content key would additionally fail for scene-spawned recipients, which have no authored identity.

### D3: Progress from the giver side of a committed transfer

`_transfer_items` already moves items atomically with both parties' inventory, quest-log, and trait
surfaces snapshotted and restored on failure. Hooking the giver side there means delivery progress
inherits that atomicity for free and cannot be asserted independently — matching the existing rule
that "there is no public 'item acquired' assertion that a caller can forge".

The receiver side keeps its existing acquisition handling, so an NPC-to-player gift still advances
`ACQUIRE` as it does today.

### D4: Landing before the player verb

Splitting the objective from the verb keeps each within a workday. The intermediate state is honest:
`DELIVER` works, but the only route to it is the dialogue `take_item` intent, which needs the LLM.
That is precisely why `quest-deliver-action` exists, and the tasks file says no content should author
a delivery quest until it lands.

## Risks / Trade-offs

- **The new kind may be silently skipped by an existing exhaustive branch** → Several modules switch
  on `ObjectiveKind` (`describe`, `planner`, `transitions`, the compiler). Task 1.3 requires sweeping
  each and making the unhandled case raise rather than fall through, so a missed site fails a test
  rather than quietly never advancing.
- **Surplus quantity in one transfer** → Progress caps at the objective quantity with no carry-over,
  the same rule `acquire.py` states. Pinned by a test.
- **`_transfer_items` grows a second quest concern** → It already handles the receiver's acquisition
  pins; adding the symmetric giver-side call keeps the two sides parallel rather than adding a novel
  pattern.
