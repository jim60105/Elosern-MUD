"""Process-scoped install (design D2b): idempotent process-wide synthetic swap.
"""

from __future__ import annotations

import importlib
from types import MappingProxyType

from world.tests.synthetic_data.targets import REGISTRY_TARGETS, _CONTENT
from world.tests.synthetic_data.patching import (
    _consumer_bindings,
    _dependency_order,
    _imported_modules,
    _late_binder_sweep,
    _revalidate_skill_lineage,
    _resolve_import_time_derivations,
)

# ---------------------------------------------------------------------------
# Process-scoped install (design D2b).
# ---------------------------------------------------------------------------
_INSTALL_STATE = {"installed": False}
_INSTALLED_ATTRS: list[tuple[object, str, object]] = []
_INSTALL_REPLACEMENTS: dict[str, tuple[object, object]] = {}
_INSTALLED_DICTS: list[tuple[dict, dict]] = []

#: Catalog vocabularies the SHIPPED authored world itself names. The authored
#: settlement and interior documents carry these keys, and the published
#: bundle re-validates them on every synchronization, so an install that keeps
#: that world live (``borrow_authored_world``) keeps the shipped rows under the
#: kit's own instead of replacing them. A plain install still substitutes the
#: whole catalog, and so does every in-process scope.
_BORROWED_VOCABULARY = frozenset({"archetypes"})


def install_synthetic_catalogs(
    logicals: tuple[str, ...] | None = None,
    *,
    borrow_authored_world: bool = False,
) -> bool:
    """Swap the shipped catalogs to synthetic content process-wide.

    Idempotent: the second call is a no-op returning ``False``. Meant for the
    separate managed-browser seed/server processes whose startup world
    bootstrap mirrors catalogs into a private database — in-process patching
    from the Playwright process cannot reach them. Owner-module attributes
    are swapped (frozen targets) or their shipped content replaced in place
    (mutable targets); already-imported consumer bindings of frozen targets
    are swapped through the discovered binding table, and consumers imported
    LATER pick the installed values up naturally. Modules that derive catalog
    state at import are resolved BEFORE the swap, so their module-scope
    projection comes from the shipped catalog rather than from content the
    install is about to replace. Returns ``True`` when this call installed.

    ``borrow_authored_world`` opts a managed-browser process into KEEPING the
    authored map world live beside the kit's content: its settlements, rooms
    and journeys are the ones a browser journey walks, so the shipped scene
    vocabulary and the shipped permanent rooms stay published and the kit's own
    rooms, anchors and placements join them. The default publishes the kit's
    world alone, which is the only self-consistent world for t_-only catalogs.
    """
    if _INSTALL_STATE["installed"]:
        return False
    names = tuple(logicals) if logicals else tuple(
        name for name in REGISTRY_TARGETS if name != "lore_sync"
    ) + ("lore_sync",)
    _INSTALL_REPLACEMENTS.clear()
    _resolve_import_time_derivations(names)
    for logical in _dependency_order(names):
        module_name, attribute = REGISTRY_TARGETS[logical]
        module = importlib.import_module(module_name)
        shipped = getattr(module, attribute)
        content = dict(_CONTENT[logical]())
        if borrow_authored_world and logical in _BORROWED_VOCABULARY:
            content = {**dict(shipped), **content}
        if not isinstance(shipped, MappingProxyType):
            _INSTALLED_DICTS.append((shipped, dict(shipped)))
            shipped.clear()
            shipped.update(content)
        else:
            replacement = MappingProxyType(content)
            _INSTALL_REPLACEMENTS[logical] = (replacement, shipped)
            _INSTALLED_ATTRS.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, replacement)
            for consumer_module, binding_name in _consumer_bindings(logical):
                if consumer_module in _imported_modules():
                    consumer = importlib.import_module(consumer_module)
                    _INSTALLED_ATTRS.append(
                        (consumer, binding_name, getattr(consumer, binding_name, None))
                    )
                    setattr(consumer, binding_name, replacement)
    _INSTALL_STATE["installed"] = True
    _INSTALL_STATE["skills"] = "skills" in names
    if _INSTALL_STATE["skills"]:
        # The kit swap replaces the live skill rows in place; the lineage
        # reverse-edge caches were built for the shipped rows and would make a
        # valid installed graph look cyclic to the topological sort. Rebuild
        # them once here, at the catalog mutation boundary, never per read.
        _revalidate_skill_lineage()
    # Only a place-catalog swap changes what the map world must publish: a
    # partial install of unrelated catalogs leaves the authored world exactly
    # as it is (its places still join its rooms).
    if "places" in names:
        _INSTALL_STATE["map_world"] = _publish_kit_world(
            borrow_authored_world=borrow_authored_world
        )
    return True


def _publish_kit_world(*, borrow_authored_world: bool):
    """Publish the map world the installed catalogs describe.

    A place row only joins an authored interior room, so an install that
    replaced the place catalog must publish the kit's permanent rooms too;
    otherwise the first synchronization rejects every kit place. Kit quest
    definitions also name kit anchors, so the kit's anchors and anchor
    placements must resolve.

    ``borrow_authored_world`` decides whether the authored world stays beside
    the kit's content. Managed browser processes walk the authored settlements
    and rooms, so their scenery and settlements join it; the default publishes
    the kit's world alone, because a t_-only catalog set and the authored rooms
    cannot both be live (the authored rooms carry the authored scene
    vocabulary).

    Borrowed mode adds the kit's anchors and anchor placements, which is what
    quest-definition validation reads. It deliberately does NOT synthesize a
    continental geography for those kit anchors (``anchor_geography`` and the
    local frames stay the authored ones): the kit's stand-in anchors exist to
    validate kit quest destinations, and the world map is unavailable under the
    synthetic install by its own contract.

    The remaining map views are never merged. A kit wilderness entry borrows a
    shipped destination node, so merging it would register two gates into one
    room (the shared core map diagnostics reject exactly that), and a kit gate
    row is keyed by the settlement identity it borrows, so merging it would
    rename the authored world's starting-room exits. Regions need no merge
    either: the browser harness widens the authored partition for the kit's
    terrain keys in its own graft.

    Returns the bundle the publication replaced so
    :func:`uninstall_synthetic_catalogs` can restore it.
    """
    from dataclasses import replace

    from world.maps import runtime
    from world.maps.interiors import build_interiors
    from world.tests.synthetic_data.interiors import interior_documents

    def merged(view, attribute):
        return replace(
            view,
            **{
                attribute: MappingProxyType(
                    {**getattr(view, attribute), **dict(_CONTENT[attribute]())}
                )
            },
        )

    previous = runtime.ensure_published()
    geography = previous.geography
    settlements = previous.settlements
    documents = {}
    if borrow_authored_world:
        geography = merged(geography, "anchors")
        settlements = merged(settlements, "anchor_placements")
        documents = dict(previous.interiors.documents)
    for document in interior_documents():
        documents[document.identity] = document
    runtime.publish(
        replace(
            previous,
            geography=geography,
            settlements=settlements,
            interiors=build_interiors(
                MappingProxyType(documents),
                fingerprints={
                    document.relative_path: document.fingerprint
                    for document in documents.values()
                },
            ),
        )
    )
    return previous


_INSTALLED_DICTS: list[tuple[dict, dict]] = []


def uninstall_synthetic_catalogs() -> bool:
    """Restore the shipped state a previous :func:`install_synthetic_catalogs`
    changed: frozen attribute bindings are rebound and mutable catalogs are
    refilled with their pre-install content. Returns ``True`` when restored."""
    if not _INSTALL_STATE["installed"]:
        return False
    for holder, attribute, original in reversed(_INSTALLED_ATTRS):
        setattr(holder, attribute, original)
    _INSTALLED_ATTRS.clear()
    # Modules imported AFTER install bound the installed replacement at
    # their own import; sweep every discovered binding still pointing at it
    # back to the pre-install shipped object.
    for logical, (replacement, shipped) in _INSTALL_REPLACEMENTS.items():
        _late_binder_sweep(logical, replacement, shipped)
    _INSTALL_REPLACEMENTS.clear()
    for target, original in reversed(_INSTALLED_DICTS):
        target.clear()
        target.update(original)
    _INSTALLED_DICTS.clear()
    if _INSTALL_STATE.pop("skills", False):
        # Restore the caches to the shipped rows that are live again.
        _revalidate_skill_lineage()
    previous_world = _INSTALL_STATE.pop("map_world", None)
    if previous_world is not None:
        from world.maps import runtime

        runtime.publish(previous_world)
    _INSTALL_STATE["installed"] = False
    return True

