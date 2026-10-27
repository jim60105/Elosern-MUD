"""Explicit shipped-geography publication for game consumer tests.

Production publishes the continental geography as the first startup step; a
game consumer test publishes exactly the same snapshot in its module or class
setup, so no test relies on an import-time load.
"""

from __future__ import annotations


def publish_shipped_geography():
    """Publish the repository's authored geography when nothing is published."""

    from world.maps import geography

    if not geography.is_published():
        geography.publish(geography.load_geography())
    return geography.current()


class GeographyPublicationMixin:
    """Publish the shipped geography once per test class.

    The mixin must precede the Evennia base class so its cooperative
    ``setUpClass`` runs before the fixtures that read map views.
    """

    @classmethod
    def setUpClass(cls):
        publish_shipped_geography()
        super().setUpClass()


__all__ = ["GeographyPublicationMixin", "publish_shipped_geography"]
