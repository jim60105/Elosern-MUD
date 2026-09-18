## Context

Both duplications sit on the deterministic-core side, where the error identity that a
caller observes is part of the contract: `service_view` raises `ServicesViewError` and
`status_query` raises `StatusQueryError`, and the surrounding modules already
catch/translate exactly those types. Any shared implementation must therefore be
error-class-parameterized, not opinionated.

## Decisions

### D1 — `read_wallet(entity, error_cls)` positional error class

```python
# world/rules/wallet.py
from typing import Any

def read_wallet(entity: Any, error_cls: type[Exception]) -> int:
    """Read one integer-copper wallet, following a possession link when absent.

    Refuses (raising ``error_cls("wallet is malformed")``) a non-int, a bool,
    or a negative value — the same fail-closed rule for every reader.
    """
    ...  # byte-for-byte the current body, recursion via read_wallet(owner, error_cls)
```

A positional `error_cls` (not a keyword default) forces every call site to state which
error it raises; a future third reader cannot inherit the wrong default silently. The
deferred imports inside the body (`world.rules.possession._resolve_live_object`,
`typeclasses.characters.PlayerCharacter`) stay deferred — they exist to keep the import
boundary clean and `test_status_query`/`test_service_view` patch neither of them.

`service_view._read_wallet` / `status_query._read_wallet` stay as one-line delegates so
module-global patching of the private name (if a test does it) keeps working and the
docstring pointers in adjacent code stay accurate. Delegates are removed only if grep
shows zero references besides their own definition — checked at implementation time;
prefer deleting the indirection if nothing patches it.

### D2 — Rollback helper lives in `clock.py`, `stage` becomes a parameter

`cast_settlement.py` already imports from `clock.py` (`_restore_clock_tick`,
`_refresh_advance_entity_caches`), so hosting `restore_registry_attribute(obj, key,
category, snapshot, *, stage)` in `clock.py` adds no new cross-module edge. It keeps the
observability exemption comment (`# observability: ignore R2: ...`) verbatim — that comment
is part of the R2 lint contract, and losing it turns the file into a lint violation.
`cast_settlement._restore_attribute_direct` becomes
`functools.partial`-free one-line delegate passing `stage="cast_registry_attribute"`;
clock's own call site passes `stage="advance_registry_attribute"`. The event id
(`rollback_restore_failed`) and every context key except the `stage` value stay identical.

## Risks / Trade-offs

- Placing the money rule in its own module adds a fourth state-reading module to
  `world/rules/`; acceptable because the alternative is two authoritative copies of the
  integer-copper refusal on the single-writer boundary.
- A `stage` parameter could be passed wrong; the focused tests
  (`test_cast_settlement`, `test_clock`) assert the logged context and pin both strings.
