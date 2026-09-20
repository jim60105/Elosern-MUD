"""``ITEM_REGISTRY`` assembly: the domain data slices in global order.

The registry is constructed from the verbatim domain slices in exactly the
order the single ``ITEM_REGISTRY`` literal in ``world/lore/items.py``
listed them (``meal`` first, ``hot_kiss_potion`` last). Dict iteration
order is observable (inventory breakdown, data-lint, presentation order),
so the concatenation order below is frozen.
"""

from world.lore.items.vocab import ItemDefinition
from world.lore.items.data_core_items import ROWS as CORE_ITEMS_ROWS
from world.lore.items.data_armor_accessories_materials import ROWS as ARMOR_ACCESSORIES_MATERIALS_ROWS
from world.lore.items.data_named_equipment import ROWS as NAMED_EQUIPMENT_ROWS
from world.lore.items.data_inspect_only_codex import ROWS as INSPECT_ONLY_CODEX_ROWS
from world.lore.items.data_regional_equipment import ROWS as REGIONAL_EQUIPMENT_ROWS
from world.lore.items.data_intimacy_items import ROWS as INTIMACY_ITEMS_ROWS

ITEM_REGISTRY: dict[str, ItemDefinition] = {
    definition.key: definition
    for definition in (
        *CORE_ITEMS_ROWS,
        *ARMOR_ACCESSORIES_MATERIALS_ROWS,
        *NAMED_EQUIPMENT_ROWS,
        *INSPECT_ONLY_CODEX_ROWS,
        *REGIONAL_EQUIPMENT_ROWS,
        *INTIMACY_ITEMS_ROWS,
    )
}
