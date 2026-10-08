"""Transport-and-puppet-owned SkillBook use selection; never persistent game state.

``explore.skill_preview`` records which one owned active skill (and which
scale) the live presentation sequence is previewing. The pair lives only on
``session.ndb``, is bound to the current coordinator epoch and puppet, and is
copied into the immutable read context as a plain tuple. It never authorizes
a cast: ``explore.cast`` revalidates every gate against canonical state.
"""

from dataclasses import dataclass

from evennia.server.signals import SIGNAL_OBJECT_POST_UNPUPPET


@dataclass(frozen=True)
class SkillUseSelection:
    """One preview selection bound to a presentation sequence."""

    owner_actor_id: int
    epoch: str
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


def skill_use_selection_snapshot(session, actor) -> tuple[str, float] | None:
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
        return (selection.skill_key, selection.scale)
    return None


def select_skill_use(session, actor, skill_key: str, scale: float) -> dict:
    """Validate a SkillBook use selection and record it without publishing.

    Only an owned registered ACTIVE skill is selectable, only in exploration
    with no active combat session, and only for a live WebClient sequence of
    the authenticated puppet. A currently unusable skill is still selectable
    (its panel then explains why). Invalid input never alters an existing
    selection or any game state. The companion action adapter owns dispatch
    and publication.
    """
    from web.webclient.presentation.affordances import in_exploration_mode
    from web.webclient.presentation.ingress import is_webclient
    from world.rules.field_cast import owned_active_skill

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
    if owned_active_skill(actor, skill_key) is None:
        return {
            "outcome": "rejected",
            "code": "unknown_skill",
            "message": "你沒有可施放的這項技能。",
        }
    ndb.skill_use_selection = SkillUseSelection(
        int(actor.pk), coordinator.epoch, skill_key, float(scale)
    )
    return {
        "outcome": "success",
        "code": "skill_previewed",
        "message": "已開啟技能施放預覽。",
    }
