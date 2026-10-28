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


def publish_shipped_map_world():
    """Adopt the repository's authored map world when nothing is published."""

    from world.maps import runtime

    if not runtime.is_published():
        runtime.adopt()
    return runtime.current()


def publish_geography(snapshot):
    """Install one geography view into the published map bundle."""

    from dataclasses import replace

    from world.maps import runtime

    runtime.ensure_published()
    return runtime.publish(replace(runtime.current(), geography=snapshot))


def publish_settlements(snapshot):
    """Install one settlement view into the published map bundle."""

    from dataclasses import replace

    from world.maps import runtime

    runtime.ensure_published()
    return runtime.publish(replace(runtime.current(), settlements=snapshot))


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
    "publish_shipped_districts",
    "publish_shipped_geography",
    "publish_shipped_interiors",
    "publish_settlements",
    "publish_shipped_map_world",
    "publish_shipped_settlements",
]
