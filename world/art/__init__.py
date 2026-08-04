"""Deterministic art-assets backend (change `art-assets`).

The engine's deterministic presentation-asset subsystem: namespaced scene and
portrait subjects, the adult portrait gate, the sole-writer enqueue service,
the serialized subject-keyed queue, the external worker boundary, the asset
store, the settings-configurable scheduler, and the read-only presenter
primitives. ``service.py`` is the only module that writes asset/queue records;
every other module here is read-only with respect to records except through
service-owned helpers.

Module set: ``subjects.py``, ``adult.py``, ``queue.py``, ``store.py``,
``service.py``, ``worker.py``, ``scheduler.py``, ``presenter.py``.
"""
