"""Transport-and-puppet-owned gallery selection; never persistent game state."""

from dataclasses import dataclass

from evennia.server.signals import SIGNAL_OBJECT_POST_UNPUPPET

from world.observability import log_info


@dataclass(frozen=True)
class GallerySelection:
    """One selection bound to a presentation sequence."""

    owner_actor_id: int
    epoch: str
    subject_key: str


def retire_gallery_selection(session) -> None:
    """Retire a selection on sequence reset, unpuppet, or disconnect."""
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        ndb.gallery_selection = None


def _on_unpuppet(sender, session, **kwargs) -> None:
    # Evennia's disconnect path unpuppets before dropping the transport.
    retire_gallery_selection(session)


SIGNAL_OBJECT_POST_UNPUPPET.connect(
    _on_unpuppet, dispatch_uid="elosern_gallery_selection_retirement", weak=False
)


def gallery_selection_snapshot(session, actor) -> str | None:
    """Copy only an owned, current selection into the immutable read context."""
    ndb = getattr(session, "ndb", None)
    selection = getattr(ndb, "gallery_selection", None)
    coordinator = getattr(ndb, "elosern_coordinator", None)
    if (
        isinstance(selection, GallerySelection)
        and getattr(session, "puppet", None) is actor
        and selection.owner_actor_id == getattr(actor, "pk", None)
        and coordinator is not None
        and selection.epoch == coordinator.epoch
    ):
        return selection.subject_key
    return None


def select_gallery_subject(session, actor, subject_key) -> dict:
    """Validate a rail selection and return action result data without publishing.

    The companion action adapter owns dispatch and publication. Invalid input
    never alters an existing selection or any gallery record.
    """
    from .gallery import gallery_subjects, validate_gallery_subject_key
    from .ingress import is_webclient
    from .protocol import ProtocolValidationError

    rejected = {
        "outcome": "rejected", "code": "unknown_subject", "message": "找不到此肖像圖庫",
    }
    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None)
    if (
        not is_webclient(session)
        or getattr(session, "puppet", None) is not actor
        or coordinator is None
    ):
        return rejected
    try:
        subject = validate_gallery_subject_key(subject_key)
    except ProtocolValidationError:  # observability: ignore R2: explicit unknown_subject result is the validation report
        return rejected
    rail = gallery_subjects(actor)
    if subject_key not in {row["subject_key"] for row, _subject, _entity in rail}:
        return rejected
    previous = gallery_selection_snapshot(session, actor) or rail[0][0]["subject_key"]
    ndb.gallery_selection = GallerySelection(actor.pk, coordinator.epoch, subject_key)
    if previous != subject_key:
        log_info("gallery_panel_selected", context={"subject": subject_key, "kind": subject.kind.value})
    return {
        "outcome": "success", "code": "gallery_selected", "message": "已切換肖像圖庫",
        "affected_panels": ("gallery",),
    }
