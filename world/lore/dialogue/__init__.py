"""Authored scripted-dialogue rows, split by domain (place-attendant-profession).

``DIALOGUE_TABLE`` is authored prose keyed by a stable identifier — immutable
identity, which the repo puts under ``world/lore/``. The rows move out of
``world/rules/dialogue.py`` (which keeps its lookup surface, the
``DialogueDefinition``/``KeywordResponse`` re-exports and the frozen
``DIALOGUE_TABLE`` read) and arrive already split by domain: ``shape.py`` owns
the two dataclasses, ``guild.py`` carries the guild hall's row, and the
per-settlement slices (``altoria.py``, ``ciaran.py``) carry the capital's and
the village's hosts as the content changes land them.

The assembly mirrors how ``world/lore/settlements/places.py`` assembles its
settlement slices: the slice order below is fixed and commented, and every
slice exports one ``ROWS`` tuple of ``(dialogue_key, DialogueDefinition)``
pairs. This package must never import ``world/rules/`` — the lore side is
registry-only.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# The rows are assembled from the domain slices in fixed, commented order (the
# world/lore/settlements/places.py assembly precedent): the table a consumer
# reads is deterministic regardless of import history, and the content changes
# that each add tables never edit the same slice.
from world.lore.dialogue.guild import ROWS as GUILD_STAFF_ROWS  # the guild hall counter
from world.lore.dialogue.altoria import ROWS as ALTORIA_ROWS  # 聖潔王都's hosts
from world.lore.dialogue.ciaran import ROWS as CIARAN_ROWS  # 暗影谷村's hosts

DIALOGUE_ROWS: dict[str, DialogueDefinition] = {
    key: definition
    for rows in (GUILD_STAFF_ROWS, ALTORIA_ROWS, CIARAN_ROWS)
    for key, definition in rows
}

__all__ = [
    "ALTORIA_ROWS",
    "CIARAN_ROWS",
    "DIALOGUE_ROWS",
    "DialogueDefinition",
    "GUILD_STAFF_ROWS",
    "KeywordResponse",
]
