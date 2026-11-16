# Design

## Context

See `proposal.md`. In `world/maps/monster_activity.py` at commit `31c01be0`:

- `read_monster_activity(wilderness)` (line 903) returns the in-flight batch state when a batch is active; otherwise it reads the stored attribute object, raises `_invalid(...)` when the value is missing, and returns the memoized decode `_DECODED_STATE` or a fresh `state_from_dict(raw)`.
- `_write_state(wilderness, state)` (line 934) parks the state in an active batch or assigns `wilderness.db.monster_activity = state_to_dict(state)`.
- Tests reach the stored record directly; find every place with `grep -rn "db\.monster_activity" --include="*.py" world server web commands typeclasses`.

## Goals / Non-Goals

**Goals:**

- Tests write and read the activity record only through the owner's functions.

**Non-Goals:**

- No change to the stored form, to `_write_state`'s behaviour, to `read_monster_activity`'s behaviour, or to any production caller.
- No new test: the migrated tests are the evidence.
- The malformed-record test of `test_monster_journeys.py` and the in-place mutation line of `test_monster_activity.py` keep their direct access (D3); `monster-activity-record-parts` owns them.

## Decisions

### D1. Two public functions

```python
def read_stored_monster_activity(wilderness: Any) -> MonsterActivityState:
    """The stored record, ignoring any in-flight batched state."""


def write_monster_activity(wilderness: Any, state: MonsterActivityState) -> None:
    """Store ``state`` as the complete record (parks it in an active batch)."""
```

- Move the body of `read_monster_activity` after its batch check into `read_stored_monster_activity` (the stored read, the missing-value refusal, the `_DECODED_STATE` memo). `read_monster_activity` keeps `_require_wilderness` and the batch check and then returns `read_stored_monster_activity(wilderness)`. `read_stored_monster_activity` calls `_require_wilderness` itself.
- `write_monster_activity` calls `_require_wilderness`, raises `TypeError(f"expected a MonsterActivityState, got {state!r}")` for any other value, then calls `_write_state(wilderness, state)`.
- Add both names to `__all__`.

### D2. Replacement rules for tests

| Pattern | Replacement |
| --- | --- |
| `X.db.monster_activity = state_to_dict(S)` | `monster_activity.write_monster_activity(X, S)` (use the module alias the file already imports, or add `from world.maps.monster_activity import write_monster_activity`) |
| `X.db.monster_activity = {**state_to_dict(S)}` (`test_monster_journeys.py`) | `write_monster_activity(X, S)` |
| `dict(X.db.monster_activity)` used as a value compared before and after | `state_to_dict(read_stored_monster_activity(X))` |
| `dict(X.db.monster_activity or {})` (`test_field_contact_boundaries.py`, two places) | `state_to_dict(read_stored_monster_activity(X)) if monster_activity.activity_provisioned(X) else {}` |
| `from_stored(wilderness)` helper body in `test_monster_activity.py` | `return activity_owner.read_stored_monster_activity(wilderness)` |

`S` is always a `MonsterActivityState` in these statements (`replace(state, ...)`, `MonsterActivityState(...)`); pass it without `state_to_dict`.

### D3. Statements left as they are

- `test_monster_journeys.py::test_missing_and_malformed_state_refuse_without_reset`: it assigns malformed mappings on purpose.
- `test_monster_activity.py`: `self.wilderness.db.monster_activity["settled_through_tick"] = 777` (an in-place mutation on purpose).
- `wilderness.attributes.remove("monster_activity")` in `test_regional_population_recovery.py`, and every use of the literal key inside an expected surface-key set (`test_regional_population.py`).

## Risks / Trade-offs

- [A migrated before/after comparison becomes weaker than the raw mapping comparison] → `state_to_dict` of the decoded record is the same mapping the raw comparison saw; the decode also validates it.
