"""Transport-and-puppet-owned gallery selection; never persistent game state."""

from dataclasses import dataclass

from evennia.server.signals import SIGNAL_OBJECT_POST_PUPPET

from world.observability import log_info, log_warn

from .gallery_categories import CATEGORY_KEYS, DISABLED_REASONS, GalleryCategoryError, gallery_owner


# One category and one subject per category, bound to the owning character
# rather than to the presentation epoch: real possession unpuppets the owner and
# resets the presentation sequence, yet the remembered selection must survive
# it. The view is therefore retired only when the session puppets an object of a
# different owner (or the session ends); a sequence reset never touches it.

UNKNOWN_CATEGORY = {
    "outcome": "rejected", "code": "unknown_category", "message": "找不到此圖庫分類",
}
UNKNOWN_SUBJECT = {
    "outcome": "rejected", "code": "unknown_subject", "message": "找不到此圖庫對象",
}
UNKNOWN_GROUP = {
    "outcome": "rejected", "code": "unknown_group", "message": "找不到此分組",
}

#: The categories whose panel expands one group at a time.
PAGED_CATEGORIES = frozenset({"people"})


@dataclass(frozen=True)
class GalleryViewSelection:
    """One session's gallery view, bound to the owning character."""

    owner_id: int
    category: str
    subjects: tuple[tuple[str, str], ...]  # (category, subject_key) pairs
    #: (category, group_key) pairs: the one group the panel expands per
    #: paged category, written by ``select_gallery_group``.
    expanded: tuple[tuple[str, str], ...] = ()


def remembered_group(view, category: str) -> str | None:
    """The group key this session remembers as expanded for ``category``."""
    return next(
        (key for pair_category, key in getattr(view, "expanded", ()) if pair_category == category),
        None,
    )


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

    The remembered per-category subjects and expanded groups are kept. Invalid
    input never alters the stored view.
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
        owner_id,
        category,
        view.subjects if view is not None else (),
        view.expanded if view is not None else (),
    )
    if previous != category:
        log_info("gallery_category_selected", context={"category": category})
    return {
        "outcome": "success", "code": "gallery_category_selected", "message": "已切換圖庫分類",
    }


def select_gallery_subject(session, actor, subject_key) -> dict:
    """Remember one subject of the currently resolved category.

    The subject must be one the panel lists for that category; it replaces the
    category's previous entry. Invalid input never alters the stored view.
    """
    from .gallery import _listed_refs, _resolve_view

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
    listed = {ref.subject.full(): ref for ref in _listed_refs(view, category, groups)}
    ref = listed.get(subject_key)
    if ref is None:
        return UNKNOWN_SUBJECT
    pairs = tuple(
        pair for pair in (view.subjects if view is not None else ()) if pair[0] != category
    ) + ((category, subject_key),)
    session.ndb.gallery_view = GalleryViewSelection(
        owner_id, category, pairs, view.expanded if view is not None else ()
    )
    if current is None or current.subject.full() != subject_key:
        log_info(
            "gallery_panel_selected",
            context={"subject": subject_key, "kind": ref.subject.kind.value, "category": category},
        )
    return {"outcome": "success", "code": "gallery_selected", "message": "已切換圖庫對象"}


def select_gallery_group(session, actor, group) -> dict:
    """Remember the one expanded group of the currently resolved paged category.

    Only a category in ``PAGED_CATEGORIES`` pages by group, and the key must
    name one of its current groups; anything else is ``unknown_group``. The
    category's previous entry is replaced. Invalid input never alters the
    stored view.
    """
    from .gallery import _expanded_key, _resolve_category
    from .gallery_categories import category_groups

    if not _session_ready(session, actor) or not isinstance(group, str):
        return UNKNOWN_GROUP
    owner_id = _owner_id(actor)
    if owner_id is None:
        return UNKNOWN_GROUP
    view = gallery_view_snapshot(session, actor)
    category = _resolve_category(view)
    if category not in PAGED_CATEGORIES:
        return UNKNOWN_GROUP
    try:
        groups = category_groups(actor, category)
    except GalleryCategoryError:  # observability: ignore R2: explicit unknown_group result reports the unresolvable owner
        return UNKNOWN_GROUP
    if group not in {row.key for row in groups}:
        return UNKNOWN_GROUP
    previous = _expanded_key(view, category, groups)
    pairs = tuple(
        pair for pair in (view.expanded if view is not None else ()) if pair[0] != category
    ) + ((category, group),)
    session.ndb.gallery_view = GalleryViewSelection(
        owner_id, category, view.subjects if view is not None else (), pairs
    )
    if previous != group:
        log_info("gallery_group_selected", context={"category": category, "group": group})
    return {"outcome": "success", "code": "gallery_group_selected", "message": "已切換分組"}
