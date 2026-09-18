"""One integer-copper wallet read, shared by every read model.

Money is stored as integer copper (a project invariant); this module is the
single authoritative reader of a wallet value, possession recursion included,
so every read model refuses a malformed wallet with the same fail-closed rule.
"""

from typing import Any


def read_wallet(entity: Any, error_cls: type[Exception]) -> int:
    """Read one integer-copper wallet, following a possession link when absent.

    Refuses (raising ``error_cls("wallet is malformed")``) a non-int, a bool,
    or a negative value — the same fail-closed rule for every reader.
    """
    raw = getattr(getattr(entity, "db", None), "wallet", None)
    if raw is None:
        possessed_by = getattr(getattr(entity, "db", None), "possessed_by", None)
        if possessed_by is not None:
            from world.rules.possession import _resolve_live_object
            owner = _resolve_live_object(int(possessed_by))
            if owner is not None:
                return read_wallet(owner, error_cls)
        from typeclasses.characters import PlayerCharacter
        if not isinstance(entity, PlayerCharacter):
            return 0
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise error_cls("wallet is malformed")
    return raw