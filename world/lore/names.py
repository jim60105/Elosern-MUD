"""Frozen NPC name-corpus registry (npc-namegen-lore-registry, design §3).

Parses the vendored CC BY 4.0 fantasy-namegen corpus under
``third_party/fantasy-namegen/`` at module import and freezes it into
``NAME_PACK_REGISTRY`` / ``NAME_PACK_BY_RACE``. Three import-time invariants
fail fast on deviating corpus data (translit coverage, pool/mapping
non-emptiness, longest composed display name vs the creation name validator).
Composition constants (``NAME_SEPARATOR``) and the display-name helper live
here so consumers never re-derive the 「名・姓」 shape.

This module is settings-required: invariant 3 reaches the real
``world.rules.character_creation._validate_name`` through a function-local
deferred import (precedent: ``world.lore.titles``), and that rules module pulls
the Django/Evennia import chain. Every consumer (``world.lore.sync`` via
``at_server_startstop``, the lore tests under the Evennia test runner, and the
later rules/UI/quest consumers) imports this module only inside a bootstrapped
Evennia process; settings-free tooling must not import it at top level.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .races import RACE_REGISTRY

# The only composition constant in the registry layer (design D7): 「名・姓」.
NAME_SEPARATOR = "・"  # U+30FB KATAKANA MIDDLE DOT

_GIVEN_POOLS = ("m", "f", "u")

_PACK_KEYS = (
    "fantasy-human",
    "fantasy-elf",
    "fantasy-dwarf",
    "fantasy-orc",
    "fantasy-halfling",
)

# The three playable races bind one pack each (design D3); fantasy-dwarf and
# fantasy-halfling stay registry-only spares with race_key=None.
_RACE_BINDINGS: dict[str, str] = {
    "human": "fantasy-human",
    "elf": "fantasy-elf",
    "beastfolk": "fantasy-orc",
}

_CORPUS_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "fantasy-namegen"


@dataclass(frozen=True)
class NamePart:
    """One corpus component: original spelling, Chinese rendering, etymology."""

    text: str
    zh: str
    meaning_zh: str


@dataclass(frozen=True)
class NamePack:
    """One vendored name pack frozen for deterministic consumption.

    ``given`` is declared ``Mapping`` but holds a concrete ``FrozenDict``
    (a ``dict`` subclass) at runtime: the sync mirror path runs
    ``dataclasses.asdict``, which deepcopies non-dataclass fields, and a
    ``MappingProxyType`` cannot be deepcopied — yet the value must still
    reject mutation so the frozen-registry invariant holds below the top
    level. The declaration type keeps consumers reading it as a Mapping.
    """

    key: str
    race_key: str | None
    surnames: tuple[NamePart, ...]
    given: Mapping[str, tuple[NamePart, ...]]
    naming_note_zh: str


class NameCorpusError(Exception):
    """The vendored corpus violates a registry invariant; import must fail."""


class FrozenDict(dict):
    """A ``dict`` that rejects every mutation after construction.

    ``NamePack.given`` must stay a concrete ``dict`` (the ``dataclasses.asdict``
    mirror path deepcopies it, and a ``MappingProxyType`` cannot be deepcopied)
    while honoring the frozen-lore-registry invariant all the way down: a pool
    emptied after import would silently persist through ``sync_all``.
    ``__reduce__`` routes deepcopy/pickle through the constructor so the
    mirror path rebuilds the type; ``_db_safe`` then stores plain dicts.
    """

    def __init__(self, items: Mapping | None = None) -> None:
        dict.update(self, dict(items or {}))

    def __reduce__(self):
        return (type(self), (dict(self),))

    def _immutable(self, *args, **kwargs):
        raise TypeError("name-corpus mapping is frozen")

    __setitem__ = __delitem__ = setdefault = update = pop = popitem = clear = _immutable


def _read_corpus(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Load the five pack payloads and the translit table from disk."""

    packs = {
        key: json.loads((root / "data" / "packs" / f"{key}.json").read_text(encoding="utf-8"))
        for key in _PACK_KEYS
    }
    translit = json.loads(
        (root / "data" / "translit" / "fantasy.json").read_text(encoding="utf-8")
    )
    return packs, translit


def _parse_parts(
    raw_parts: list[dict[str, Any]],
    source_field: str,
    translit: Mapping[str, str],
) -> tuple[NamePart, ...]:
    """Freeze one source array; translit coverage is pre-validated by caller."""

    return tuple(
        NamePart(
            text=raw[source_field],
            zh=translit[raw[source_field]],
            meaning_zh=raw.get("meaning") or "",
        )
        for raw in raw_parts
    )


def _validate_bindings(
    race_bindings: Mapping[str, str], pack_keys: set[str]
) -> None:
    for race_key, pack_key in race_bindings.items():
        if race_key not in RACE_REGISTRY:
            raise NameCorpusError(f"race binding key {race_key!r} is not a RACE_REGISTRY key")
        if pack_key not in pack_keys:
            raise NameCorpusError(f"race binding {race_key!r} targets unregistered pack {pack_key!r}")


def _validate_compositions(packs: list[NamePack]) -> None:
    """Invariant 3: every pack's longest composed display name is creatable.

    The validator is the real rules-layer gate, reached by function-local
    deferred import so ``lore`` keeps no top-level ``rules`` dependency
    (design D5; precedent: ``world.lore.titles``).
    """

    from world.rules.character_creation import CharacterCreationError, _validate_name

    for pack in packs:
        given_parts = [part for pool in pack.given.values() for part in pool]
        longest_given = max(given_parts, key=lambda part: len(part.zh)).zh
        longest_surname = max(pack.surnames, key=lambda part: len(part.zh)).zh
        composed = f"{longest_given}{NAME_SEPARATOR}{longest_surname}"
        try:
            _validate_name(composed)
        except CharacterCreationError as exc:
            raise NameCorpusError(
                f"pack {pack.key!r} longest composed name {composed!r} "
                f"fails the creation name validator: {exc}"
            ) from exc


def _build_registry(
    pack_payloads: Mapping[str, dict[str, Any]],
    translit: Mapping[str, str],
    race_bindings: Mapping[str, str],
) -> tuple[Mapping[str, NamePack], Mapping[str, str]]:
    """Parse, validate, and freeze the corpus (pure; injectable for tests)."""

    if sorted(pack_payloads) != sorted(_PACK_KEYS):
        raise NameCorpusError(
            f"corpus must carry exactly the packs {list(_PACK_KEYS)}, "
            f"got {sorted(pack_payloads)}"
        )

    texts: set[str] = set()
    for payload in pack_payloads.values():
        texts.update(raw["s"] for raw in payload["surnames"])
        for pool_key in _GIVEN_POOLS:
            texts.update(raw["g"] for raw in payload["given"].get(pool_key, []))
    missing = sorted(texts - set(translit))
    if missing:
        raise NameCorpusError(
            f"translit table is missing {len(missing)} corpus word(s): "
            + ", ".join(missing)
        )

    _validate_bindings(race_bindings, set(pack_payloads))
    bound_race = {pack_key: race_key for race_key, pack_key in race_bindings.items()}

    packs: list[NamePack] = []
    for key in _PACK_KEYS:
        payload = pack_payloads[key]
        # Invariant 2: surnames and every given pool are non-empty, and the
        # pool set is exactly m/f/u.
        if not payload["surnames"]:
            raise NameCorpusError(f"pack {key!r} has no surnames")
        given_payload = payload["given"]
        if sorted(given_payload) != sorted(_GIVEN_POOLS):
            raise NameCorpusError(
                f"pack {key!r} given pools must be exactly {list(_GIVEN_POOLS)}, "
                f"got {sorted(given_payload)}"
            )
        for pool_key in _GIVEN_POOLS:
            if not given_payload[pool_key]:
                raise NameCorpusError(f"pack {key!r} given pool {pool_key!r} is empty")
        packs.append(
            NamePack(
                key=key,
                race_key=bound_race.get(key),
                surnames=_parse_parts(payload["surnames"], "s", translit),
                # Concrete dict subclass, never MappingProxyType: see
                # NamePack docstring (asdict deepcopy) and FrozenDict.
                given=FrozenDict({
                    pool_key: _parse_parts(given_payload[pool_key], "g", translit)
                    for pool_key in _GIVEN_POOLS
                }),
                naming_note_zh=payload["rules"]["naming"]["note"],
            )
        )

    _validate_compositions(packs)

    registry = {pack.key: pack for pack in packs}
    return MappingProxyType(registry), MappingProxyType(dict(race_bindings))


_PACK_PAYLOADS, _TRANSLIT = _read_corpus(_CORPUS_ROOT)
NAME_PACK_REGISTRY, NAME_PACK_BY_RACE = _build_registry(
    _PACK_PAYLOADS, _TRANSLIT, _RACE_BINDINGS
)


def compose_display_name(given: NamePart, surname: NamePart) -> str:
    """The player-visible display name: 「名・姓」, Chinese renderings only."""

    return f"{given.zh}{NAME_SEPARATOR}{surname.zh}"
