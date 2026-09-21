"""聖潔王都 (capital_altoria) MIDDLE-terrace place rows (settlement-shops design §6.1).

The middle terrace is the city's civic and crafting ground between the old
lower town and the noble upper heights (docs/lore/settlement-locations.md):
the adventurer guild, the general store, and the craft alley where 鍛造鋪 and
裁縫坊 share one exterior under two doorway names (altoria-capital-replan).

The guild hall and general store are transcribed from the constants in
``world/maps/bootstrap.py`` and the roster rows removed from
``world/rules/rulebook/guild_economy.yaml``, so the derived shops and
service-host roster reproduce the pre-change shipped identities exactly. The
two specialist shops (聖潔王都鍛造鋪 / 聖潔王都裁縫坊) are authored content:
their interiors, hosts and assortments exist only here and in
``world/rules/rulebook/commerce/altoria.yaml``.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice follows the lower terrace and precedes the upper,
so its rows reach the derived roster between them.

Merchant rows carry a ``dialogue_key`` beside their ``shop_key``: the merchant
blueprint answers as well as trades (merchant-dialogue), and a merchant place
without the kwarg fails load naming the place. The tables live in
``world/lore/dialogue/altoria.py`` under the same keys.

altoria-learning-and-exchange appends the capital's last two middle-terrace
rooms: 聖潔王都商會公所 off 東市 — the document's designated future source
of escort commissions, landed here as an attendant host who talks caravans
and trade routes and offers no work, because the escort quest type the
commissions need does not exist — and 聖潔王都市集棚 off 市場街, the
capital's second host-less place, host-less on the document's authority
rather than on an unwritten story: 「市場街本身不需要一位固定的街長型功能性
NPC，遊戲性功能都掛在各個攤販身上」 (docs/lore/settlement-locations.md
line 374). 市場街 now carries three doors (雜貨店、首飾坊、市集棚) and 東市
two (鍊金坊、商會公所); the registry's doorway-name rule keeps them honest.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_guild_hall",
        settlement_key="capital_altoria",
        kind=PlaceKind.GUILD_HALL,
        room_name_zh="阿爾托利亞冒險者公會大廳",
        room_desc_zh=(
            "阿爾托利亞的冒險者公會大廳，屋裡的兩樣主角是一面向著門的大任務板，"
            "與一半鋪成環場的訓練地。"
        ),
        exterior_xy=(4, 3),  # 公會前
        doorway_key_zh="冒險者公會大廳",
        doorway_aliases=("guild hall", "hall"),
        host_name="葛里安·衛登",
        host_title="阿爾托利亞分會會長",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="guild_staff",
        service_id="altoria_guild_master",
        assortment_keys=(),
        authored_kwargs=(
            ("branch_key", "guild_branch_altoria"),
            ("dialogue_key", "guild_staff"),
        ),
    ),
    PlaceDefinition(
        key="altoria_general_store",
        settlement_key="capital_altoria",
        kind=PlaceKind.GENERAL_STORE,
        room_name_zh="阿爾托利亞雜貨店",
        room_desc_zh=(
            "阿爾托利亞的雜貨店，貨架總留著幾格空位，像在任何一支商隊趕來之前"
            "先替它們留好位置。"
        ),
        exterior_xy=(2, 3),  # 市場街
        doorway_key_zh="雜貨店",
        doorway_aliases=("general store", "store", "shop"),
        host_name="瑪爾特·金秤",
        host_title="阿爾托利亞雜貨商店老闆",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="merchant",
        service_id="altoria_merchant",
        # The 58-item monolith split along the specialist axis
        # (commerce-assortment-registry): the general store keeps the
        # sundries shelf, the specialists take weapons, food and armour.
        assortment_keys=("general_sundries",),
        authored_kwargs=(
            ("shop_key", "altoria_general_store"),
            ("dialogue_key", "altoria_general_store"),
        ),
    ),
    PlaceDefinition(
        key="altoria_forge",
        settlement_key="capital_altoria",
        kind=PlaceKind.WEAPONSMITH,
        room_name_zh="聖潔王都鍛造鋪",
        room_desc_zh=(
            "聖潔王都的鍛造鋪，砧聲在屋簷下響著，替這座王都的兵器生意一聲聲"
            "定了價。"
        ),
        exterior_xy=(1, 3),  # 工匠巷
        doorway_key_zh="鍛造鋪",
        doorway_aliases=("forge", "smithy"),
        host_name="維爾登·黑潭",
        host_title="聖潔王都鍛造鋪鐵匠",
        host_race="human",
        host_subrace="human_plains",
        host_sex="male",
        profession="merchant",
        service_id="altoria_blacksmith",
        assortment_keys=("common_arms",),
        authored_kwargs=(
            ("shop_key", "altoria_forge"),
            ("dialogue_key", "altoria_forge"),
        ),
    ),
    PlaceDefinition(
        key="altoria_tailor",
        settlement_key="capital_altoria",
        kind=PlaceKind.OUTFITTER,
        room_name_zh="聖潔王都裁縫坊",
        room_desc_zh=(
            "聖潔王都的裁縫坊，一卷卷布匹擱在案邊，等著北大道那些貴族的訂單。"
        ),
        exterior_xy=(1, 3),  # 工匠巷
        doorway_key_zh="裁縫坊",
        doorway_aliases=("tailor", "tailor shop"),
        host_name="妮絲塔·狐溪",
        host_title="聖潔王都裁縫坊坊主",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        profession="merchant",
        service_id="altoria_tailor",
        assortment_keys=("common_outfits",),
        authored_kwargs=(
            ("shop_key", "altoria_tailor"),
            ("dialogue_key", "altoria_tailor"),
        ),
    ),
    # altoria-adornments-and-remedies: the last two specialists of the
    # forge/eatery/tailor family. The jeweller shares 市場街 with the general
    # store — one exterior, two doors, distinguished by their authored
    # doorway names (雜貨店 vs 首飾坊).
    PlaceDefinition(
        key="altoria_jeweller",
        settlement_key="capital_altoria",
        kind=PlaceKind.JEWELLER,
        room_name_zh="聖潔王都首飾坊",
        room_desc_zh=(
            "聖潔王都的首飾坊，展示櫃裡打著光，為市場街的飾品交易而亮。"
        ),
        exterior_xy=(2, 3),  # 市場街
        doorway_key_zh="首飾坊",
        doorway_aliases=("jeweller", "jewelry shop"),
        host_name="艾蓮娜·鴉丘",
        host_title="聖潔王都首飾坊主",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        profession="merchant",
        service_id="altoria_jeweller",
        assortment_keys=("capital_adornments",),
        authored_kwargs=(
            ("shop_key", "altoria_jeweller"),
            ("dialogue_key", "altoria_jeweller"),
        ),
    ),
    PlaceDefinition(
        key="altoria_alchemist",
        settlement_key="capital_altoria",
        kind=PlaceKind.ALCHEMIST,
        room_name_zh="聖潔王都鍊金坊",
        room_desc_zh=(
            "聖潔王都的鍊金坊，一排排瓶罐塞好、貼好標籤，望著東市那條貨運道路。"
        ),
        exterior_xy=(5, 3),  # 東市
        doorway_key_zh="鍊金坊",
        doorway_aliases=("alchemist", "alchemy shop"),
        host_name="希碧拉·灰沼",
        host_title="聖潔王都鍊金坊主",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        profession="merchant",
        service_id="altoria_alchemist",
        assortment_keys=("capital_remedies",),
        authored_kwargs=(
            ("shop_key", "altoria_alchemist"),
            ("dialogue_key", "altoria_alchemist"),
        ),
    ),
    # 聖潔王都商會公所 — the merchants' guild hall, off 東市 (5,3), sharing
    # that exterior with the alchemist under a different doorway name
    # (鍊金坊 vs 商會公所). The document's 商會與貿易行 is 「未來的」護衛委託
    # 發放處 and 「guild request」 already reports escort work closed: the
    # guild master talks caravans, routes and tariffs as world-building and
    # offers nothing — a commission surface without the escort quest type
    # behind it would post work that cannot be completed, so this row ships
    # an attendant's dialogue table and no work board (design refusal two).
    PlaceDefinition(
        key="altoria_merchant_hall",
        settlement_key="capital_altoria",
        kind=PlaceKind.MERCHANT_HALL,
        room_name_zh="聖潔王都商會公所",
        room_desc_zh=(
            "聖潔王都的商會公所是一間縱長的辦公室，俯著東市那條貨運道上的"
            "車馬：窗下一張稅率長桌，牆上釘著路線圖，這一季各支商隊的名字用"
            "粉筆記在地圖旁邊；長凳上坐等的是各號的代辦，櫃檯那頭書記把一筆筆"
            "生意用白紙黑字敲定。東市的買賣是在這間屋子裡調度的——誰走哪條路、"
            "誰替誰載玻璃與穀物、季末誰該付公會多少。牆上沒有公告板，門邊也沒有"
            "名單：這座公所日後要派什麼活，眼下都還是隔著書桌、面對面跟人談定的。"
        ),
        exterior_xy=(5, 3),  # 東市
        doorway_key_zh="商會公所",
        doorway_aliases=("merchant hall", "guild of merchants", "trading hall"),
        host_name="尤斯汀·柯德溫",
        host_title="聖潔王都商會會長",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        profession="attendant",
        service_id="altoria_merchant_master",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_merchant_hall"),),
    ),
    # 聖潔王都市集棚 — the covered market stalls, off 市場街 (2,3), sharing
    # that exterior with the general store and the jeweller under a third
    # doorway name (雜貨店 vs 首飾坊 vs 市集棚). Host-less on the document's
    # authority, not by omission: line 374 says a market street's function
    # hangs on individual stallholders, not on a fixed street-chief NPC, so
    # this emptiness is a design statement, not the palace's unwritten
    # story. When stallholders arrive they will be transient scene NPCs on
    # the quest path — the same rooms-only shape hostless-places reserves,
    # with no permanent roster row expected behind it.
    PlaceDefinition(
        key="altoria_market_stalls",
        settlement_key="capital_altoria",
        kind=PlaceKind.MARKET,
        room_name_zh="聖潔王都市集棚",
        room_desc_zh=(
            "聖潔王都的市集棚是蓋在別人攤位上頭的一片屋頂：長長一座棚子，"
            "支架撐著帆布與攔板，日光從縫隙漏下來，在空蕩的攤位排之間拖出淡淡"
            "的光條。每個攤位都掃過了、也都不屬於誰——賣果子的天亮推車進來、"
            "黃昏推車出去，賣唱的佔西門那片寬地，這塊地本身不養任何固定的店主。"
            "一條街的生意靠的是只站今天一天的人，而棚子蓋來就是為了等那樣的人，"
            "什麼都不問，什麼都不留。"
        ),
        exterior_xy=(2, 3),  # 市場街
        doorway_key_zh="市集棚",
        doorway_aliases=("market stalls", "stalls", "covered market"),
    ),
)
