"""Deterministic art-assets backend (change `art-assets`).

The engine's deterministic presentation-asset subsystem: namespaced scene and
portrait subjects, the canonical-age subject check, the sole-writer enqueue
service, the serialized subject-keyed queue, the external worker boundary, the
asset store, the settings-configurable scheduler, and the read-only presenter
primitives. ``service.py`` is the only module that writes asset/queue records;
every other module here is read-only with respect to those records except
through service-owned helpers. ``gallery.py`` owns the separate gallery
records and is their only writer.

Module set: ``subjects.py``, ``queue.py``, ``store.py``,
``service.py``, ``worker.py``, ``scheduler.py``, ``presenter.py``,
``paths.py``, ``gallery.py``.
"""
