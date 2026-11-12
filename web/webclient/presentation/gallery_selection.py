"""Transport-and-puppet-owned gallery selection; never persistent game state."""

from dataclasses import dataclass

from evennia.server.signals import SIGNAL_OBJECT_POST_PUPPET, SIGNAL_OBJECT_POST_UNPUPPET

from world.observability import log_info, log_warn

from .gallery_categories import CATEGORY_KEYS, DISABLED_REASONS, GalleryCategoryError, gallery_owner


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
    """Dead version-3 rail selection (deleted by ``gallery-v3-removal``).

    ``gallery.subject.select`` calls ``select_gallery_subject_v4``; nothing
    reaches this function any more.

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
    }


# -- version 4: one category and one subject per category ----------------------
#
# Bound to the owning character rather than to the presentation epoch: real
# possession unpuppets the owner and resets the presentation sequence, yet the
# remembered selection must survive it. The view is therefore retired only when
# the session puppets an object of a different owner (or the session ends), and
# neither ``retire_gallery_selection`` nor a sequence reset touches it.

UNKNOWN_CATEGORY = {
    "outcome": "rejected", "code": "unknown_category", "message": "找不到此圖庫分類",
}
UNKNOWN_SUBJECT = {
    "outcome": "rejected", "code": "unknown_subject", "message": "找不到此圖庫對象",
}


@dataclass(frozen=True)
class GalleryViewSelection:
    """One session's version-4 gallery view, bound to the owning character."""

    owner_id: int
    category: str
    subjects: tuple[tuple[str, str], ...]  # (category, subject_key) pairs


def _owner_id(actor) -> int | None:
    try:
        owner = gallery_owner(actor)
    except GalleryCategoryError:  # observability: ignore R2: an unresolvable owner owns no view; the caller treats it as none
        return None
    return getattr(owner, "pk", None)


def _on_puppet(sender, session=None, **kwargs) -> None:
    # Retire the view when the new puppet belongs to another owner. Possession
    # sets ``possessed_by`` before the puppet transfer and handback puppets the
    # owner itself, so both keep the owner and the view.
    ndb = getattr(session, "ndb", None)
    view = getattr(ndb, "gallery_view", None)
    if view is None:
        return
    try:
        keep = isinstance(view, GalleryViewSelection) and view.owner_id == _owner_id(sender)
    except Exception as exc:  # observability: ignore R2: logged below; a receiver must never break puppeting
        log_warn("gallery_view_retire_failed", context={"puppet": getattr(sender, "pk", None)}, exc=exc)
        keep = False
    if not keep:
        ndb.gallery_view = None


SIGNAL_OBJECT_POST_PUPPET.connect(
    _on_puppet, dispatch_uid="elosern_gallery_view_retirement", weak=False
)


def gallery_view_snapshot(session, actor) -> GalleryViewSelection | None:
    """Copy only a view owned by this session's current owner into the read context."""
    ndb = getattr(session, "ndb", None)
    view = getattr(ndb, "gallery_view", None)
    if (
        isinstance(view, GalleryViewSelection)
        and getattr(session, "puppet", None) is actor
        and getattr(ndb, "elosern_coordinator", None) is not None
        and view.owner_id == _owner_id(actor)
    ):
        return view
    return None


def _session_ready(session, actor) -> bool:
    from .ingress import is_webclient

    return (
        is_webclient(session)
        and getattr(session, "puppet", None) is actor
        and getattr(getattr(session, "ndb", None), "elosern_coordinator", None) is not None
    )


def select_gallery_category(session, actor, category) -> dict:
    """Remember one enabled category; returns action result data without publishing.

    The remembered per-category subjects are kept. Invalid input never alters
    the stored view.
    """
    from .gallery import _resolve_category

    if (
        not _session_ready(session, actor)
        or not isinstance(category, str)
        or category not in CATEGORY_KEYS
        or category in DISABLED_REASONS
    ):
        return UNKNOWN_CATEGORY
    owner_id = _owner_id(actor)
    if owner_id is None:
        return UNKNOWN_CATEGORY
    view = gallery_view_snapshot(session, actor)
    previous = _resolve_category(view)
    session.ndb.gallery_view = GalleryViewSelection(
        owner_id, category, view.subjects if view is not None else ()
    )
    if previous != category:
        log_info("gallery_category_selected", context={"category": category})
    return {
        "outcome": "success", "code": "gallery_category_selected", "message": "已切換圖庫分類",
    }


def select_gallery_subject_v4(session, actor, subject_key) -> dict:
    """Remember one subject of the currently resolved category.

    The subject must be listed in that category's groups; it replaces the
    category's previous entry. Invalid input never alters the stored view.
    """
    from .gallery import _resolve_view

    if not _session_ready(session, actor) or not isinstance(subject_key, str):
        return UNKNOWN_SUBJECT
    owner_id = _owner_id(actor)
    if owner_id is None:
        return UNKNOWN_SUBJECT
    view = gallery_view_snapshot(session, actor)
    try:
        category, current, groups = _resolve_view(actor, view)
    except GalleryCategoryError:  # observability: ignore R2: explicit unknown_subject result reports the unresolvable owner
        return UNKNOWN_SUBJECT
    listed = {ref.subject.full(): ref for group in groups for ref in group.subjects}
    ref = listed.get(subject_key)
    if ref is None:
        return UNKNOWN_SUBJECT
    pairs = tuple(
        pair for pair in (view.subjects if view is not None else ()) if pair[0] != category
    ) + ((category, subject_key),)
    session.ndb.gallery_view = GalleryViewSelection(owner_id, category, pairs)
    if current is None or current.subject.full() != subject_key:
        log_info(
            "gallery_panel_selected",
            context={"subject": subject_key, "kind": ref.subject.kind.value, "category": category},
        )
    return {"outcome": "success", "code": "gallery_selected", "message": "已切換圖庫對象"}
