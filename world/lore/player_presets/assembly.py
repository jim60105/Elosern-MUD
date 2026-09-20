"""``PLAYER_PRESET_REGISTRY`` assembly: the card data slices in global order.

The registry is constructed from the verbatim card slices in exactly the order
the single ``PLAYER_PRESET_REGISTRY`` literal in ``world/lore/player_presets.py``
listed its cards (``elysa_snow`` first, ``elosia_shadowmoon`` last). Dict
iteration order is observable (creation card listing, key-order contracts,
data-lint), so the concatenation order below is frozen.
"""

from world.lore.player_presets.vocab import PlayerPreset
from world.lore.player_presets.data_pack_cards import ROWS as PACK_CARDS_ROWS
from world.lore.player_presets.data_story_cards import ROWS as STORY_CARDS_ROWS

PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset] = {
    **PACK_CARDS_ROWS,
    **STORY_CARDS_ROWS,
}
