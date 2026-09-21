"""聖潔王都 (capital_altoria) UPPER-terrace place rows (settlement-shops design §6.1).

The upper terrace is the higher ground of the noble quarter, the great temple
and the academy (docs/lore/settlement-locations.md). No place row has been
authored here yet: the slice exists so the terraces own the assembly before
the content changes do — the sanctum change adds this terrace's rows, and
crown-and-watch and learning-and-exchange each append one here.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice follows the capital's lower and middle terraces,
so its rows reach the derived roster after them and before the village's.

Merchant rows here will carry a ``dialogue_key`` beside their ``shop_key``
like every other capital merchant (merchant-dialogue); the tables live in
``world/lore/dialogue/altoria.py`` under the same keys.
"""

from world.lore.settlements.places import PlaceDefinition

ROWS: tuple[PlaceDefinition, ...] = ()
