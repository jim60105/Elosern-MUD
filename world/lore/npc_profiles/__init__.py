"""The assembled NPC profile registry: authored, keyed, immutable identities.

The slice order below is fixed and load-bearing (the
``world/lore/settlements/places.py`` assembly precedent): ``altoria_lower``,
``altoria_trade``, ``altoria_guild``, ``altoria_upper``, ``ciaran_homes_a``,
``ciaran_homes_b``, ``companions``. Each slice is owned by exactly one later
content change and exports one ``ROWS: tuple[NpcProfile, ...]`` tuple; this
module is the single place that concatenates them into
``NPC_PROFILE_REGISTRY``.

Profiles carry hidden identities read only through code, so -- unlike every
other lore registry ``world/lore/sync.py`` mirrors into ``lore:`` Scripts --
this registry is deliberately NOT mirrored into persistent lore records.
Do not add it to ``world/lore/sync.py``.
"""

from types import MappingProxyType
from typing import Sequence

from world.lore.npc_card import NpcCard, NpcCardError
from world.lore.npc_profiles.shape import _KEY_RE, NpcProfile

# The content slices in fixed, commented order (altoria-place-slices /
# places.py precedent): the registry a consumer reads is deterministic
# regardless of import history, and each content change edits only its own
# slice module.
from world.lore.npc_profiles.altoria_lower import ROWS as ALTORIA_LOWER_ROWS  # noqa: E402
from world.lore.npc_profiles.altoria_trade import ROWS as ALTORIA_TRADE_ROWS  # noqa: E402
from world.lore.npc_profiles.altoria_guild import ROWS as ALTORIA_GUILD_ROWS  # noqa: E402
from world.lore.npc_profiles.altoria_upper import ROWS as ALTORIA_UPPER_ROWS  # noqa: E402
from world.lore.npc_profiles.ciaran_homes_a import ROWS as CIARAN_HOMES_A_ROWS  # noqa: E402
from world.lore.npc_profiles.ciaran_homes_b import ROWS as CIARAN_HOMES_B_ROWS  # noqa: E402
from world.lore.npc_profiles.companions import ROWS as COMPANIONS_ROWS  # noqa: E402


def assemble_profile_registry(
    slices: Sequence[tuple[str, Sequence[NpcProfile]]],
) -> dict[str, NpcProfile]:
    """Pure assembly: concatenate owned slices into one key -> profile dict.

    Rejects (naming the offending slice and/or key):
    a row that is not an ``NpcProfile``; a key that fails the profile key
    vocabulary (``shape._KEY_RE``); a key declared by two slices (naming the
    key and both slice labels); and a card that fails the compact card
    contract once round-tripped through ``to_record``/``from_record``
    (naming the profile key, its slice, and the card error text).
    """
    registry: dict[str, NpcProfile] = {}
    declared_by: dict[str, str] = {}
    for slice_label, rows in slices:
        for row in rows:
            if not isinstance(row, NpcProfile):
                raise ValueError(
                    f"npc_profiles slice {slice_label!r} declares a non-NpcProfile row: {row!r}"
                )
            if not isinstance(row.key, str) or not _KEY_RE.match(row.key):
                raise ValueError(
                    f"npc_profiles slice {slice_label!r} declares an invalid profile "
                    f"key {row.key!r}"
                )
            if row.key in registry:
                raise ValueError(
                    f"npc_profiles key {row.key!r} is declared by both "
                    f"{declared_by[row.key]!r} and {slice_label!r}"
                )
            try:
                NpcCard.from_record(row.card.to_record())
            except NpcCardError as error:
                raise ValueError(
                    f"npc_profiles profile {row.key!r} in slice {slice_label!r} "
                    f"has a malformed card: {error}"
                ) from error
            registry[row.key] = row
            declared_by[row.key] = slice_label
    return registry


NPC_PROFILE_REGISTRY: MappingProxyType[str, NpcProfile] = MappingProxyType(
    assemble_profile_registry(
        (
            ("altoria_lower", ALTORIA_LOWER_ROWS),
            ("altoria_trade", ALTORIA_TRADE_ROWS),
            ("altoria_guild", ALTORIA_GUILD_ROWS),
            ("altoria_upper", ALTORIA_UPPER_ROWS),
            ("ciaran_homes_a", CIARAN_HOMES_A_ROWS),
            ("ciaran_homes_b", CIARAN_HOMES_B_ROWS),
            ("companions", COMPANIONS_ROWS),
        )
    )
)

__all__ = [
    "ALTORIA_GUILD_ROWS",
    "ALTORIA_LOWER_ROWS",
    "ALTORIA_TRADE_ROWS",
    "ALTORIA_UPPER_ROWS",
    "CIARAN_HOMES_A_ROWS",
    "CIARAN_HOMES_B_ROWS",
    "COMPANIONS_ROWS",
    "NPC_PROFILE_REGISTRY",
]
