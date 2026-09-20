"""暗影谷村 (ciaran) authored dialogue rows.

Empty until the village content changes land their attendant hosts: every
place row naming a ``dialogue_key`` must ship its table in the same change
(load-time resolution rejects an authored host that cannot speak), so each
village content change appends its rows to ``ROWS`` here.
"""

from world.lore.dialogue.shape import DialogueDefinition

ROWS: tuple[tuple[str, DialogueDefinition], ...] = ()
