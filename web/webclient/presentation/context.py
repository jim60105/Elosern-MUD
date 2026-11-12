"""Immutable read-only context handed to presenters.

A presenter receives only session-derived facts: the authenticated puppet and a
few read-only session observations. It never receives the raw Session, the
dispatcher, or the coordinator, so it cannot mutate presentation or game state.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from world.rules.unlock_notices import MemberUnlocks

#: The immutable empty unlock snapshot every context without session marks
#: shares.
_EMPTY_UNLOCKS: Mapping[int, MemberUnlocks] = MappingProxyType({})


@dataclass(frozen=True)
class ProposalSnapshot:
    """One immutable read of the session's transient concept proposal slot.

    Copied from ``session.ndb.concept_proposal`` wherever a presentation
    context is built; the creation presenter renders only this snapshot, never
    the raw session. ``revision`` is the session-monotonic transient sequence
    number the browser compares against its last applied revision; the four
    content keys are deep-copied plain data with no live object reference.
    The five transient-fill fields are optional: ``None`` means the proposal
    never carried a value and the wire object omits the key entirely (never
    null); a carried ``affinity_elements`` is stored as a copied tuple so a
    later mutation of the session slot can never alter this frozen snapshot.
    """

    revision: int
    race: str
    subrace: str | None
    allocations: Mapping[str, Any]
    persona: Mapping[str, Any]
    display_name: str | None = None
    age: int | None = None
    apparent_age: int | None = None
    background: str | None = None
    affinity_elements: tuple[str, ...] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize the proposal into its exact wire object."""
        wire: dict[str, Any] = {
            "revision": self.revision,
            "race": self.race,
            "subrace": self.subrace,
            "allocations": dict(self.allocations),
            "persona": dict(self.persona),
        }
        # Absent transient-fill values are expressed as the key not existing;
        # a carried affinity tuple serializes to a freshly allocated list
        # (bump-creation-panel-proposal-v3 D1).
        for key in ("display_name", "age", "apparent_age", "background"):
            value = getattr(self, key)
            if value is not None:
                wire[key] = value
        if self.affinity_elements is not None:
            wire["affinity_elements"] = list(self.affinity_elements)
        return wire


@dataclass(frozen=True)
class PresentationContext:
    """One authenticated, read-only snapshot of presentation inputs.

    Attributes:
        actor: The active puppet object resolved from ``session.puppet``.
        protocol_version: The server protocol schema version in use.
        session_tag: An opaque ephemeral label for diagnostics only; it is
            never a client-controlled value and never persisted.
        proposal: The immutable session concept-proposal snapshot (or
            ``None``); the creation panel renders it as the optional
            ``proposal`` key only while the slot holds a proposal for the
            rendering puppet.
        combat_round: The completing combat action's frozen ``RoundRecord``
            (or ``None``). Only the dispatcher's completion publication for an
            admitted action that settled an ordinary round supplies it; every
            other publication path builds its context without one, so the
            beats panel is available exactly once per settled round.
        skill_use: The copied ``(actor_id, skill_key, scale)`` SkillBook use
            selection of the current transport-and-puppet epoch (or
            ``None``). Only the ``skill_use`` presenter reads it; it never
            authorizes a cast.
        party_actor: The copied requested-combat-actor identity of the current
            transport-and-puppet epoch (or ``None``). Only the ``combat``
            panel's choices read it, and only while the named member is still a
            commandable party member of the same session and round; it never
            authorizes a command.
        unlocks: The copied session unlock state, keyed by member dbid: the
            unread dot and the recent-unlock set. Session-scoped and
            non-persistent — a reconnect starts empty, and clearing the dot
            keeps the recent set.
        party_view: The copied viewed-member selection of this session (a
            ``party_view_selection.PartyViewSelection``, or ``None``).
            Session-scoped and non-persistent; it survives a possession
            transition because it is bound to the commander, and it never
            authorizes anything.
        gallery_view: The copied version-4 gallery view of this session (a
            ``gallery_selection.GalleryViewSelection``, or ``None``): one
            category and one subject per category, bound to the owning
            character so it survives possession. Only the registered gallery
            presenter reads it; it never authorizes anything.
        travel_events: The immutable travel notices
            (``world.rules.travel_events.TravelEvent``) of the causal group
            being published, or of the latest published batch on a replay.
            Only the coordinator supplies it, at its publication boundary;
            only the ``travel_log`` presenter reads it.
    """

    actor: Any
    protocol_version: int
    session_tag: str | None = field(default=None)
    proposal: ProposalSnapshot | None = field(default=None)
    # Dead version-3 rail selection, read only by the unregistered
    # ``gallery_presenter_v3``; ``gallery-v3-removal`` drops it.
    gallery_subject: str | None = field(default=None)
    combat_round: Any = field(default=None)
    skill_use: tuple[int, str, float] | None = field(default=None)
    party_actor: int | None = field(default=None)
    unlocks: Mapping[int, MemberUnlocks] = field(default=_EMPTY_UNLOCKS)
    party_view: Any = field(default=None)
    gallery_view: Any = field(default=None)
    travel_events: tuple[Any, ...] = field(default=())


__all__ = [
    "ProposalSnapshot",
    "PresentationContext",
]
