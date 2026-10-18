"""Transport-and-puppet-owned SkillBook use selection; never persistent game state.

``explore.skill_preview`` records which party member's one owned active skill
(and which scale) the live presentation sequence is previewing. The triple
lives only on ``session.ndb``, is bound to the current coordinator epoch and
puppet, and is copied into the immutable read context as a plain tuple. It
never authorizes a cast: ``explore.cast`` reauthorizes the caster and
revalidates every gate against canonical state.
"""

from dataclasses import dataclass

from evennia.server.signals import SIGNAL_OBJECT_POST_UNPUPPET


@dataclass(frozen=True)
class SkillUseSelection:
    """One preview selection bound to a presentation sequence."""

    owner_actor_id: int
    epoch: str
    actor_id: int
    skill_key: str
    scale: float


def retire_skill_use_selection(session) -> None:
    """Retire a selection on sequence reset, unpuppet, disconnect, or completion."""
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        ndb.skill_use_selection = None


def _on_unpuppet(sender, session, **kwargs) -> None:
    # Evennia's disconnect path unpuppets before dropping the transport.
    retire_skill_use_selection(session)


SIGNAL_OBJECT_POST_UNPUPPET.connect(
    _on_unpuppet, dispatch_uid="elosern_skill_use_selection_retirement", weak=False
)


def skill_use_selection_snapshot(session, actor) -> tuple[int, str, float] | None:
    """Copy only an owned, current-epoch selection into the read context."""
    ndb = getattr(session, "ndb", None)
    selection = getattr(ndb, "skill_use_selection", None)
    coordinator = getattr(ndb, "elosern_coordinator", None)
    if (
        isinstance(selection, SkillUseSelection)
        and getattr(session, "puppet", None) is actor
        and selection.owner_actor_id == getattr(actor, "pk", None)
        and coordinator is not None
        and selection.epoch == coordinator.epoch
    ):
        return (selection.actor_id, selection.skill_key, selection.scale)
    return None


def select_skill_use(
    session, actor, actor_id: int, skill_key: str, scale: float
) -> dict:
    """Validate a SkillBook use selection and record it without publishing.

    The named caster is re-derived through the party boundary for the acting
    purpose and never trusted as identity, so a forged, stale, absent, or
    knocked-out member is refused with its stable party code and the
    authenticated puppet is never substituted. Only that caster's owned
    registered ACTIVE skill is selectable, only in exploration with no active
    combat session, and only for a live WebClient sequence of the
    authenticated puppet. A currently unusable skill is still selectable (its
    panel then explains why). Invalid input never alters an existing selection
    or any game state. The action adapter owns dispatch and publication.
    """
    from web.webclient.presentation.affordances import in_exploration_mode
    from web.webclient.presentation.ingress import is_webclient
    from world.rules.field_cast import owned_active_skill
    from world.rules.party_scope import (
        PARTY_SCOPE_MESSAGES,
        PURPOSE_ACT,
        PartyScopeError,
        authorize_member,
        resolve_commander,
    )

    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None)
    if (
        not is_webclient(session)
        or getattr(session, "puppet", None) is not actor
        or coordinator is None
    ):
        return {
            "outcome": "rejected",
            "code": "no_presentation_session",
            "message": "目前無法預覽技能。",
        }
    if not in_exploration_mode(actor):
        return {
            "outcome": "rejected",
            "code": "not_in_exploration",
            "message": "只有在戰鬥外才能從技能書施放。",
        }
    try:
        caster = authorize_member(
            resolve_commander(actor), actor_id, PURPOSE_ACT, anchor=actor
        )
    except PartyScopeError as error:  # observability: ignore R2: the stable party refusal IS the action result, not a swallowed failure
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": PARTY_SCOPE_MESSAGES.get(error.reason, "目前無法施放。"),
        }
    if owned_active_skill(caster, skill_key) is None:
        return {
            "outcome": "rejected",
            "code": "unknown_skill",
            "message": "你沒有可施放的這項技能。",
        }
    ndb.skill_use_selection = SkillUseSelection(
        int(actor.pk), coordinator.epoch, int(actor_id), skill_key, float(scale)
    )
    return {
        "outcome": "success",
        "code": "skill_previewed",
        "message": "已開啟技能施放預覽。",
    }
