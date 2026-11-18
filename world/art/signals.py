"""Project-local Django signals for deterministic art completion (design D5).

``world/art/`` stays a deterministic, web-free package: the completion signal
is emitted by the worker drain path (never by a settle on a worker thread) and
consumed by the presentation package, so the dependency direction and the
repository deterministic-path contract are preserved. The payload carries
exactly the completed full subject key and the settled job's canonical image id
and never exposes output paths, prompts, or worker internals.
"""

from django.dispatch import Signal

# Emitted once per applied gallery-job settlement (success or failure). The
# payload carries exactly two fields: ``subject_key``, the completed full
# subject key (e.g. ``scene:tavern_interior``), and ``image_id``, the settled
# job's canonical UUID image id. A stale/no-op settlement emits nothing, and
# distinct images of one subject are distinct notifications. It is sent on the
# reactor thread (or the calling thread in deterministic ``drain_synchronous``
# tests), never on the worker subprocess thread.
asset_completed = Signal()
