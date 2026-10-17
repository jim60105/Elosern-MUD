"""Transport-and-puppet-owned combat actor selection; never persistent state.

``combat.actor_choices`` records which allied member's catalog, resources and
stock the live presentation sequence is showing. The selection lives only on
``session.ndb``, is bound to the current coordinator epoch, the puppet, the
combat session and its round revision, and is copied into the immutable read
context as one plain actor identity. It can never mutate the draft, authorize a
command, or invoke possession: every command is reauthorized against canonical
state at the rules boundary, and a selection that no longer matches the live
session/round/epoch simply falls back to the panel's own default actor.
"""

from dataclasses import dataclass

from evennia.server.signals import SIGNAL_OBJECT_POST_UNPUPPET


@dataclass(frozen=True)
class PartyActorSelection:
    """One requested combat actor bound to a presentation sequence."""

    owner_actor_id: int
    epoch: str
    session_id: str
    round_revision: int
    actor_id: int


def retire_party_actor_selection(session) -> None:
    """Retire a selection on sequence reset, unpuppet, disconnect, or replacement."""
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        ndb.party_actor_selection = None


def _on_unpuppet(sender, session, **kwargs) -> None:
    # Evennia's disconnect path unpuppets before dropping the transport.
    retire_party_actor_selection(session)


SIGNAL_OBJECT_POST_UNPUPPET.connect(
    _on_unpuppet, dispatch_uid="elosern_party_actor_selection_retirement", weak=False
)


def select_party_actor(
    session,
    actor,
    session_id: str,
    round_revision: int,
    actor_id: int,
) -> bool:
    """Record one authorized actor choice for the live sequence.

    Only a live WebClient sequence of the authenticated puppet with an attached
    coordinator records a selection; anything else (a direct call without a
    presentation sequence, a retired sequence) records nothing and answers
    ``False``. The caller has already reauthorized ``actor_id`` through the
    shared party boundary; recording never authorizes anything by itself.
    """
    from web.webclient.presentation.ingress import is_webclient

    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None)
    if (
        ndb is None
        or coordinator is None
        or not is_webclient(session)
        or getattr(session, "puppet", None) is not actor
    ):
        return False
    ndb.party_actor_selection = PartyActorSelection(
        int(actor.pk),
        coordinator.epoch,
        str(session_id),
        int(round_revision),
        int(actor_id),
    )
    return True


def party_actor_selection_snapshot(session, actor) -> int | None:
    """Copy only an owned, current-epoch, current-session selection into the context.

    A selection bound to a retired epoch, another puppet or another owner is
    discarded, and one whose combat session or round revision has moved on is
    dropped so the panel returns to its own default actor for the new round.
    """
    from world.rules.combat_session import read_session

    ndb = getattr(session, "ndb", None)
    selection = getattr(ndb, "party_actor_selection", None)
    coordinator = getattr(ndb, "elosern_coordinator", None)
    if (
        not isinstance(selection, PartyActorSelection)
        or getattr(session, "puppet", None) is not actor
        or selection.owner_actor_id != getattr(actor, "pk", None)
        or coordinator is None
        or selection.epoch != coordinator.epoch
    ):
        return None
    try:
        record = read_session(actor)
    except Exception:  # observability: ignore R2: an unreadable session cannot keep a selection; the panel falls back to its own default actor
        return None
    if (
        record is None
        or record.session_id != selection.session_id
        or record.round_revision != selection.round_revision
    ):
        return None
    return selection.actor_id
