"""Actual wilderness population read projection (wilderness-monster-population).

Ordinary regional births are owned by ``world.maps.regional_population`` and
the authored site lifecycle by ``world.maps.monster_sites``; both register
living individuals in the wilderness script's ``itemcoordinates``. This module
keeps only the read side that presence consumers share:

- :func:`population_view` projects the actually present living entities of the
  requested cells, under their persistent identity, with their canonical threat
  facts. It creates, reconciles and ticks nothing.
- :func:`threat_label` renders one observation's canonical tier and danger
  grade.

It also keeps the explicit ownership-marker departure primitive the defeat
aftermath contract uses for a living winner that carries a population marker;
no code here generates, replaces or reconciles population.
"""

from dataclasses import dataclass
from typing import Any
from collections.abc import Iterable

from typeclasses.monsters import Monster
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.maps.wilderness_provider import is_valid_wilderness_cell
from world.rules.surfaces import persisted_hp as _persisted_hp


def _stored_hp(monster: Monster) -> float:
    """Read the monster's stored HP without advancing a wall-clock gauge."""
    return _persisted_hp(monster)


@dataclass(frozen=True, slots=True)
class PopulationFact:
    """One actually present entity in the wilderness population view.

    ``threat_tier`` and ``danger_grade`` are the canonical threat facts of a
    living monster observation, read from its registry-derived individual
    identity (wilderness-travel-window-ui); every other observation carries
    ``None``. ``observation_key`` names the persistent dbref of the object
    (``object:<pk>``), never a predicted coordinate slot: a scheduled future
    birth is not an entity, so it has no fact, and a fresh birth is a new ID.
    """

    observation_key: str
    cell: tuple[int, int]
    kind: str
    hostile: bool
    label: str
    threat_tier: str | None = None
    danger_grade: str | None = None


def threat_label(tier: str | None, grade: str | None) -> str | None:
    """The display threat of one observation's canonical tier and grade.

    The tier's registered display name, followed by the guild danger grade
    when one is declared; ``None`` when the tier is unknown, so a consumer
    states an unknown threat instead of guessing one.
    """
    row = MONSTER_TIER_REGISTRY.get(tier) if isinstance(tier, str) else None
    if row is None:
        return None
    return f"{row.display_name_zh} {grade} 級" if isinstance(grade, str) and grade else row.display_name_zh


def _monster_threat(monster: Any) -> dict[str, str | None]:
    """A materialized monster's resolved tier and danger grade (never raises)."""
    from world.rules.monster_individual import individual_danger_grade

    tier = getattr(monster, "threat_tier", None)
    return {
        "threat_tier": tier if isinstance(tier, str) else None,
        "danger_grade": individual_danger_grade(monster),
    }


@dataclass(frozen=True)
class PopulationDepartureTicket:
    """A committed logical departure awaiting its physical deletion.

    ``revert`` undoes the logical departure (marker and bookkeeping back in
    place) both in-process and in the database; it is idempotent for a
    monster whose row no longer exists.
    """

    monster: Monster
    wilderness: Any
    saved_marker: str
    saved_coordinates: tuple[int, int] | None

    def revert(self) -> None:
        """Restore the marker and the bookkeeping entry."""
        if self.monster.pk is None:
            # A deleted settlement is never restored.
            return
        self.monster.db.population_key = self.saved_marker
        if self.saved_coordinates is not None:
            self.wilderness.db.itemcoordinates[self.monster] = (
                self.saved_coordinates
            )


def depart_population_monster(
    wilderness, monster: Monster
) -> PopulationDepartureTicket:
    """In-transaction departure phase for the defeat aftermath (D-C3).

    The defeat writer requests the departure, but this module stays the writer
    of the marker lifecycle: the ownership marker is cleared and the
    bookkeeping entry dropped inside the caller's open transaction, so a
    settlement rollback restores the winner together with every other
    aftermath write. The physical ``delete()`` is deliberately NOT part of
    this primitive: Evennia cannot resurrect a deleted instance in-process (the
    idmapper cache is not transaction-aware), so the caller deletes the
    departed monster only after its transaction commits.

    Only an individual that explicitly carries a population marker is
    departed; regional and site owners record their own presence evidence and
    never rely on this marker.
    """
    if not monster.db.population_key:
        raise ValueError(f"{monster} carries no population marker")
    saved_marker = monster.db.population_key
    saved_coordinates = wilderness.db.itemcoordinates.get(monster)
    monster.db.population_key = None
    wilderness.db.itemcoordinates.pop(monster, None)

    return PopulationDepartureTicket(
        monster=monster,
        wilderness=wilderness,
        saved_marker=saved_marker,
        saved_coordinates=saved_coordinates,
    )


def population_view(
    wilderness,
    cells: Iterable[tuple[int, int]],
) -> tuple[PopulationFact, ...]:
    """Project the actually present population of the requested cells.

    The wilderness script's ``itemcoordinates`` is the single authoritative
    position surface, so this is one index over actual registrations: every
    living ``Monster`` standing on a requested valid cell is projected exactly
    once under its persistent ``object:<dbid>`` identity, with its current
    coordinate and its registry-derived threat facts. Characters and NPCs keep
    their existing observations.

    Presence is evidence only of an actual object. An uninitialized, empty,
    blocked or due habitat, a scheduled future birth, a site's authored state
    and an ecology zone's home ownership are never population facts, and a
    dead (zero stored HP) individual is absent. The read creates nothing,
    reconciles nothing and ticks no gauge.
    """
    from typeclasses.characters import PlayerCharacter
    from typeclasses.npcs import LLMNPC, NPC
    from world.maps.regional_population import coordinate_pair

    target_cells = set(cells)
    if not target_cells:
        return ()

    present: list[tuple[tuple[int, int], int, PopulationFact]] = []
    for obj, registered in (wilderness.db.itemcoordinates or {}).items():
        if obj is None:
            continue
        cell = coordinate_pair(registered)
        if cell is None or cell not in target_cells:
            continue
        if not is_valid_wilderness_cell(cell):
            # Registration never stands on an impassable or invalid cell.
            continue
        pk = getattr(obj, "pk", None)
        if pk is None:
            continue

        if isinstance(obj, Monster):
            if _stored_hp(obj) <= 0:
                continue
            fact = PopulationFact(
                observation_key=f"object:{pk}",
                cell=cell,
                kind="monster",
                hostile=True,
                label=obj.key,
                **_monster_threat(obj),
            )
        elif isinstance(obj, PlayerCharacter):
            fact = PopulationFact(
                observation_key=f"object:{pk}",
                cell=cell,
                kind="character",
                hostile=False,
                label=obj.key,
            )
        elif isinstance(obj, (NPC, LLMNPC)):
            fact = PopulationFact(
                observation_key=f"object:{pk}",
                cell=cell,
                kind="npc",
                hostile=False,
                label=obj.key,
            )
        else:
            continue
        present.append((cell, int(pk), fact))

    present.sort(key=lambda entry: (entry[0], entry[1]))
    return tuple(fact for _cell, _pk, fact in present)
