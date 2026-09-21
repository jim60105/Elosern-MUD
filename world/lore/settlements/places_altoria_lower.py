"""聖潔王都 (capital_altoria) LOWER-terrace place rows (settlement-shops design §6.1).

The lower terrace is 南門一帶最老也最擁擠的舊城區, the market belt running
along the cleared wall line — the food trade's ground (docs/lore/
settlement-locations.md). The 南大道 eatery is the capital slice's first row;
the hospitality content change adds this terrace's tavern, lodging and
bathhouse here.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice leads the capital's three, so its rows reach the
derived roster before the middle terrace's.

Merchant rows carry a ``dialogue_key`` beside their ``shop_key``: the merchant
blueprint answers as well as trades (merchant-dialogue), and a merchant place
without the kwarg fails load naming the place. The tables live in
``world/lore/dialogue/altoria.py`` under the same keys.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_eatery",
        settlement_key="capital_altoria",
        kind=PlaceKind.EATERY,
        room_name_zh="聖潔王都餐館",
        room_desc_zh=(
            "The eatery of 聖潔王都, steam rising from its kitchen over "
            "南大道's foot traffic (settlement-shops design §6.1)."
        ),
        exterior_xy=(3, 1),  # 南大道
        doorway_key_zh="餐館",
        doorway_aliases=("eatery", "restaurant", "diner"),
        host_name="西格瑪·庫柏",
        host_title="聖潔王都餐館老闆",
        host_race="human",
        host_subrace="human_plains",
        host_sex="male",
        profession="merchant",
        service_id="altoria_eatery_owner",
        assortment_keys=("staple_meals",),
        authored_kwargs=(
            ("shop_key", "altoria_eatery"),
            ("dialogue_key", "altoria_eatery"),
        ),
    ),
)
