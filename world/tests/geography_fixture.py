"""Explicit shipped map-world publication for game consumer tests.

Production publishes the discovered settlement local maps and then the
continental geography as the first two startup steps; a game consumer test
publishes exactly the same snapshots in its module or class setup, so no test
relies on an import-time load.

The two are published together because they are one map world: the geography
candidate validates its wilderness gateways against the settlement candidate,
and every settlement registry view reads the published settlement snapshot.
"""

from __future__ import annotations


def publish_shipped_settlements():
    """Publish the repository's authored settlement world when nothing is published."""

    from world.maps import map_data

    if not map_data.is_published():
        map_data.publish(map_data.load_settlements())
    return map_data.current()


def publish_shipped_geography():
    """Publish the shipped settlement and geography snapshots when needed."""

    publish_shipped_settlements()
    from world.maps import geography

    if not geography.is_published():
        geography.publish(geography.load_geography())
    return geography.current()


class GeographyPublicationMixin:
    """Publish the shipped map world once per test class.

    The mixin must precede the Evennia base class so its cooperative
    ``setUpClass`` runs before the fixtures that read map views.
    """

    @classmethod
    def setUpClass(cls):
        publish_shipped_geography()
        super().setUpClass()


__all__ = [
    "GeographyPublicationMixin",
    "publish_shipped_geography",
    "publish_shipped_settlements",
]
