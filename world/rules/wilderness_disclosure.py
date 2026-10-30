"""The wilderness disclosure policy: which wilderness map facts may be published.

A wilderness cell's terrain, place name and destination identity are only
public once the character can see the ground or has actually been there
(wilderness-sight-and-fog-reveal design §5; wilderness-map-disclosure design
D1). This module is the one read-only decision every wilderness publication
consults -- the eager local map, the exploration move rows and, later, the area
map -- so no surface can disagree about what one observer already knows.

Two predicates compose here:

- **Permanent reveal.** ``world.rules.map_knowledge.revealed_in_bounds`` owns
  the reveal projection (a lit district, or the stored sight disc of a visit).
  A ``wild:`` destination is disclosed only when its cell is revealed.
- **Actual visitation of a hidden place.** Elven villages and dungeons are
  hidden point entries: their names and canonical identities appear only after
  the character has visited them, even when the surrounding district is lit.
  The visited predicate is the exact gate room's canonical node ID, because the
  node a wilderness gateway publishes *is* that room's identity.

Nothing here writes state, advances the clock, or reads a live entity: the
decision is a pure projection of the character's map-knowledge record.
"""

from typing import Any, Iterable

from world.rules.map_knowledge import (
    KnowledgeError,
    NodeVisit,
    decode_node,
    parse_knowledge,
    revealed_in_bounds,
)

#: The canonical direction words a withheld wilderness direction publishes
#: instead of a terrain, settlement or exit-derived label. They are the same
#: words the exit compass normalizes to a bearing, so an opaque direction keeps
#: its target angle without disclosing what lies at its end.
DIRECTION_LABELS: dict[str, str] = {
    "n": "north",
    "ne": "northeast",
    "e": "east",
    "se": "southeast",
    "s": "south",
    "sw": "southwest",
    "w": "west",
    "nw": "northwest",
}

#: Anchor kinds whose location identity stays hidden until visited (the
#: detailed sight design §5.3: "Hidden point entries and elven villages still
#: appear only after the character visits them").
HIDDEN_ANCHOR_KINDS = frozenset({"elven_village", "dungeon"})


def generic_direction_label(direction: str | None) -> str | None:
    """The generic compass-direction word for one normalized wilderness direction.

    Returns ``None`` for anything that is not a canonical direction, so a caller
    can never publish a non-direction string as a direction label.
    """
    if not isinstance(direction, str):
        return None
    return DIRECTION_LABELS.get(direction)


def anchor_is_hidden(anchor_key: str | None) -> bool:
    """Whether one registered anchor's location identity is visit-gated.

    Fails closed: an unknown or unreadable anchor is treated as hidden, because
    an identity that cannot be classified must never be disclosed.
    """
    if not isinstance(anchor_key, str) or not anchor_key:
        return True
    try:
        from world.lore.anchors import anchors

        anchor = anchors().get(anchor_key)
    except Exception:  # observability: ignore R2: an unpublished geography keeps the fail-closed answer (hidden), and the caller's panel degrades to the withheld form instead of raising
        return True
    if anchor is None:
        return True
    kind = getattr(anchor, "kind", None)
    value = getattr(kind, "value", kind)
    return value in HIDDEN_ANCHOR_KINDS


def _neighbourhood(centre: tuple[int, int]) -> tuple[int, int, int, int]:
    x, y = centre
    return (x - 1, y - 1, x + 1, y + 1)


class WildernessDisclosure:
    """One read-only disclosure decision around a wilderness observer.

    ``revealed`` is the reveal projection over the observer's adjacent cells
    (the bounded query the eight-neighbour publications need); ``visited`` is
    the set of canonical node IDs the knowledge record holds.
    """

    def __init__(
        self,
        revealed: frozenset[tuple[int, int]],
        visited: frozenset[str],
    ) -> None:
        self._revealed = revealed
        self._visited = visited

    @classmethod
    def around(
        cls,
        actor: Any,
        centre: tuple[int, int],
        visits: Iterable[NodeVisit] | None = None,
    ) -> "WildernessDisclosure":
        """Build the projected decision for the cells adjacent to ``centre``.

        A corrupt or absent knowledge record reveals nothing and visited
        nothing: the reveal read already emits the corrupt-record diagnostic,
        and this projection must never turn a presentation read into an
        exception or an invented fact.
        """
        revealed = revealed_in_bounds(actor, _neighbourhood(centre))
        if visits is None:
            try:
                visits = parse_knowledge(actor)
            except KnowledgeError:  # observability: ignore R2: revealed_in_bounds above already emits the corrupt-record diagnostic, and a presentation read degrades to "nothing known"
                visits = ()
        visited = frozenset(visit.node_id for visit in visits)
        return cls(frozenset(revealed), visited)

    def reveals(self, cell: tuple[int, int]) -> bool:
        """Whether one adjacent wilderness cell's facts may be disclosed."""
        return (int(cell[0]), int(cell[1])) in self._revealed

    def gateway_disclosed(self, anchor_key: str | None, gate_node: str | None) -> bool:
        """Whether a registered gateway's identity may be disclosed.

        A non-hidden settlement's gateway is disclosed once its own approach
        cell is part of the publication (the current cell, a revealed
        neighbour, or an actually visited remembered boundary). A hidden
        anchor's gateway requires the exact gate room's canonical node to be in
        the visit record, so its name and identity never leak from a lit
        district or a neighbouring cell.
        """
        if not isinstance(gate_node, str) or not gate_node:
            return False
        if not anchor_is_hidden(anchor_key):
            return True
        return gate_node in self._visited

    def destination_disclosed(
        self, destination_node: str, anchor_key: str | None = None
    ) -> bool:
        """Whether one resolved wilderness destination may be disclosed.

        ``wild:`` destinations follow permanent reveal; ``grid:`` destinations
        are gateway rooms and follow the gateway rule. Any other prefix is
        outside this slice's wilderness disclosure scope.
        """
        decoded = decode_node(destination_node)
        prefix = decoded["prefix"]
        if prefix == "wild":
            return self.reveals((decoded["x"], decoded["y"]))
        if prefix == "grid":
            return self.gateway_disclosed(anchor_key, destination_node)
        return True


__all__ = [
    "DIRECTION_LABELS",
    "HIDDEN_ANCHOR_KINDS",
    "WildernessDisclosure",
    "anchor_is_hidden",
    "generic_direction_label",
]
