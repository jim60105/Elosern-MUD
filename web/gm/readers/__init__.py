"""Read-only runtime state readers for the GM portal (gm-portal-s3-runtime-state).

Nothing in this package writes. Every reader projects authoritative read
models and stored values: it never recomputes a rule the game owns, never
autocreates an Attribute (``AttributeProperty`` descriptors autocreate on
access, so readers use ``attributes.get(..., default=...)``), never provisions a
component or a Script, and never calls a narrative writer or
``build_dialogue_context``.

The layout is one module per entity kind — ``accounts``, ``characters``,
``npcs``, ``monsters``, ``rooms``, ``quests``, ``narrative``, ``art`` — plus
``raw`` (the universal Evennia object dump), ``search`` (global search),
``errors`` (the lookup/filter error matrix) and ``registry`` (the kind dispatch
the transport calls).
"""

from __future__ import annotations

__all__: list[str] = []
