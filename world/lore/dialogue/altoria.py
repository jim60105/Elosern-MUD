"""聖潔王都 (capital_altoria) authored dialogue rows.

Empty until the settlement content changes land their attendant hosts: every
place row naming a ``dialogue_key`` must ship its table in the same change
(load-time resolution rejects an authored host that cannot speak), so each
capital content change appends its rows to ``ROWS`` here.
"""

from world.lore.dialogue.shape import DialogueDefinition

ROWS: tuple[tuple[str, DialogueDefinition], ...] = ()
