"""Explicit shipped map-world publication for game consumer tests.

Production adopts the complete authored map world as its first startup step
(``map_world_adoption``); a game consumer test publishes exactly the same
bundle in its module or class setup, so no test relies on an import-time load.

The four domain views (settlements, continental geography, districts and
permanent interiors) are one bundle because they are one map world: the
geography candidate validates its wilderness gateways against the settlement
candidate, districts validate against both, and every service place joins an
interior room. Nothing here writes persistent state; a test that needs the
materialized world runs the map synchronization itself.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from world.maps.bootstrap import SyncReport


def publish_shipped_map_world():
    """Adopt the repository's authored map world when nothing is published."""

    from world.maps import runtime

    if not runtime.is_published():
        runtime.adopt()
    elif runtime.current().roads is None:
        # A synthetic publication clears the road cells; the shipped world
        # carries the committed network again.
        from dataclasses import replace

        from world.maps import road_network

        runtime.publish(
            replace(runtime.current(), roads=road_network.frozen_network())
        )
    return runtime.current()


def publish_geography(snapshot):
    """Install one geography view into the published map bundle."""

    from dataclasses import replace

    from world.maps import runtime

    runtime.ensure_published()
    return runtime.publish(replace(runtime.current(), geography=snapshot, roads=None))


def publish_settlements(snapshot):
    """Install one settlement view into the published map bundle."""

    from dataclasses import replace

    from world.maps import runtime

    runtime.ensure_published()
    return runtime.publish(replace(runtime.current(), settlements=snapshot, roads=None))


def publish_districts(snapshot):
    """Install one district view into the published map bundle.

    A candidate carrying any diagnostic is rejected and the published world is
    left as it was, exactly like the district domain's own publication contract.
    """

    from dataclasses import replace

    from world.lore import map_districts
    from world.maps import runtime

    if snapshot.diagnostics:
        raise map_districts.DistrictError(snapshot.diagnostics)
    runtime.ensure_published()
    runtime.publish(replace(runtime.current(), districts=snapshot))
    return snapshot


def publish_interiors(snapshot):
    """Install one interior view into the published map bundle."""

    from dataclasses import replace

    from world.maps import runtime

    runtime.ensure_published()
    return runtime.publish(replace(runtime.current(), interiors=snapshot))


def clear_published_map_world():
    """Forget the published bundle for a scope that asserts the not-loaded state."""

    from world.maps import runtime

    return runtime.clear_published_world()


def restore_published_map_world(bundle) -> None:
    """Restore a previously saved bundle."""

    from world.maps import runtime

    if bundle is None:
        runtime.clear_published_world()
    else:
        runtime.publish(bundle)


def publish_shipped_settlements():
    """The published settlement world (adopting the whole map world if needed)."""

    from world.maps import map_data

    publish_shipped_map_world()
    return map_data.current()


def publish_shipped_geography():
    """The published continental geography (adopting the whole world if needed)."""

    from world.maps import geography

    publish_shipped_map_world()
    return geography.current()


def publish_shipped_districts():
    """The published district world (adopting the whole map world if needed)."""

    from world.lore import map_districts

    publish_shipped_map_world()
    return map_districts.current()


def publish_shipped_interiors():
    """The published permanent interiors (adopting the whole world if needed)."""

    from world.maps import interiors

    publish_shipped_map_world()
    return interiors.current()


def sync_test_settlements(settlement_ids: Iterable[str]) -> SyncReport:
    """Materialize exactly the declared settlements through the real synchronizer.

    The declaration is frozen once so a one-shot iterable reaches the
    synchronizer as a stable tuple. Publication of the complete map world is
    still required; only the persistent convergence is bounded.
    """

    from world.maps.bootstrap import sync_grid

    if isinstance(settlement_ids, str):
        raise TypeError("settlement_ids must be an iterable of map ids, not a string")
    ids = tuple(settlement_ids)
    publish_shipped_map_world()
    return sync_grid(settlement_ids=ids)


def sync_test_wilderness(settlement_ids: Iterable[str]) -> None:
    """Provision wilderness gates for exactly the declared settlements."""

    from world.maps.bootstrap import sync_wilderness

    if isinstance(settlement_ids, str):
        raise TypeError("settlement_ids must be an iterable of map ids, not a string")
    ids = tuple(settlement_ids)
    publish_shipped_map_world()
    sync_wilderness(settlement_ids=ids)


@contextmanager
def selected_startup_settlements(settlement_ids: Iterable[str]) -> Iterator[None]:
    """Run real startup code with the two synchronizers bound to one declaration.

    The real ``bootstrap.sync_grid``/``sync_wilderness`` bindings are captured
    before replacement, so startup still executes the production planner,
    writer and rollback journal with the fixed selection. Only those two
    bindings are patched; both are restored on every exit path.
    """

    from unittest.mock import patch

    from world.maps import bootstrap

    if isinstance(settlement_ids, str):
        raise TypeError("settlement_ids must be an iterable of map ids, not a string")
    ids = tuple(settlement_ids)
    # Publish and validate/freeze the declaration before anything is patched.
    publish_shipped_map_world()
    bootstrap._selected_settlement_graphs(ids)
    real_sync_grid = bootstrap.sync_grid
    real_sync_wilderness = bootstrap.sync_wilderness

    def startup_sync_grid(*args, **kwargs):
        return real_sync_grid(*args, settlement_ids=ids, **kwargs)

    def startup_sync_wilderness(*args, **kwargs):
        return real_sync_wilderness(*args, settlement_ids=ids, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(bootstrap, "sync_grid", startup_sync_grid))
        stack.enter_context(
            patch.object(bootstrap, "sync_wilderness", startup_sync_wilderness)
        )
        yield


class GeographyPublicationMixin:
    """Publish the shipped map world once per test class.

    The mixin must precede the Evennia base class so its cooperative
    ``setUpClass`` runs before the fixtures that read map views.
    """

    @classmethod
    def setUpClass(cls):
        publish_shipped_map_world()
        super().setUpClass()


__all__ = [
    "GeographyPublicationMixin",
    "clear_published_map_world",
    "publish_districts",
    "publish_geography",
    "publish_interiors",
    "restore_published_map_world",
    "selected_startup_settlements",
    "sync_test_settlements",
    "sync_test_wilderness",
    "publish_shipped_districts",
    "publish_shipped_geography",
    "publish_shipped_interiors",
    "publish_settlements",
    "publish_shipped_map_world",
    "publish_shipped_settlements",
]
