"""聖潔王都 (capital_altoria) UPPER-terrace place rows (settlement-shops design §6.1).

The upper terrace is the higher ground of the noble quarter, the great temple
and the academy (docs/lore/settlement-locations.md). The sanctum change
altoria-sanctum lands this terrace's first rows: 聖潔王都光明神殿 and its
attached 聖潔王都聖所, two place records sharing the one 大神殿前 exterior
under two doorway names — worship, the sanctum's open ministry and the shop
that supplies it are one building's three counters, and the map shows that
as one square with two doors. Learning-and-exchange appends its row here
later.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice follows the capital's lower and middle terraces,
so its rows reach the derived roster after them and before the village's.

Merchant rows here carry a ``dialogue_key`` beside their ``shop_key``
like every other capital merchant (merchant-dialogue); the tables live in
``world/lore/dialogue/altoria.py`` under the same keys. The 主祭's row is the
capital's second ``attendant`` host — her service is conversation, so she
authors a ``dialogue_key`` and no goods.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_temple",
        settlement_key="capital_altoria",
        kind=PlaceKind.TEMPLE,
        room_name_zh="聖潔王都光明神殿",
        room_desc_zh=(
            "The light of the 光明神殿 arrives before the room does: tall "
            "windows up the whole height of the nave, and the morning "
            "through them in bars you could lay hands on. Benches face the "
            "raised dais where the 主祭 reads, blesses and answers; the "
            "air holds a little of the day's incense. Along the near "
            "wall, the nave opens without partition or curtain into the "
            "聖所's own hall — the sanctum where the church's ministry of "
            "love is carried out, its shop counter visible from the "
            "benches. Blessing, ministry and trade are three counters of "
            "one faith, side by side in the same light; nobody in this "
            "city would think to lower their voice about any of them."
        ),
        exterior_xy=(4, 4),  # 大神殿前
        doorway_key_zh="光明神殿",
        doorway_aliases=("temple", "cathedral", "church"),
        host_name="艾莉安娜·寒水",
        host_title="聖潔王都光明神殿主祭",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="attendant",
        service_id="altoria_high_priestess",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_temple"),),
    ),
    PlaceDefinition(
        key="altoria_sanctum",
        settlement_key="capital_altoria",
        kind=PlaceKind.SANCTUM_SHOP,
        room_name_zh="聖潔王都聖所",
        room_desc_zh=(
            "The 聖所 opens off the nave under the same roof and the same "
            "windows: warm light, clean linen, warm water ready in basins, "
            "and along one wall a shop counter fitted out like any other "
            "in the capital — shelves of ritual and comfort ware, glass "
            "bottles, folded vestments of soft cloth, priced and stocked "
            "the way a general store prices and stocks. Attendants move "
            "between the counter and the guest rooms down the hall with "
            "ledgers under their arms, calling the deacon's name in the "
            "same voice they use for blessings. Worship, ministry and "
            "trade in one building, in the open: this is how the Church "
            "of Light keeps house, and everyone on the continent knows it "
            "the way they know a tavern sells wine."
        ),
        exterior_xy=(4, 4),  # 大神殿前
        doorway_key_zh="聖所",
        doorway_aliases=("sanctum", "church sanctum"),
        host_name="羅海西亞·芬威克",
        host_title="聖潔王都聖所執事",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="merchant",
        service_id="altoria_sanctum_deacon",
        assortment_keys=("sanctum_wares",),
        authored_kwargs=(
            ("shop_key", "altoria_sanctum_shop"),
            ("dialogue_key", "altoria_sanctum"),
        ),
    ),
)
